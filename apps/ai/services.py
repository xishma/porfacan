from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.lexicon.models import EntryCategory, Epoch
from apps.lexicon.normalization import normalize_persian

JSON_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
JSON_OBJECT_RE = re.compile(r"(\{.*\})", re.DOTALL)


@dataclass(frozen=True)
class EntryDraftResult:
    prompt: str
    raw_response: str
    payload: dict[str, Any]


def build_entry_prompt(headword: str) -> str:
    allowed_epochs, allowed_categories = _allowed_taxonomy_lists()
    epochs_text = "\n".join(allowed_epochs) if allowed_epochs else "-"
    categories_text = "\n".join(allowed_categories) if allowed_categories else "-"
    return (
        _prompt_template_text()
        .replace("__HEADWORD__", headword)
        .replace("__ALLOWED_EPOCHS__", epochs_text)
        .replace("__ALLOWED_CATEGORIES__", categories_text)
    )


def generate_entry_draft(headword: str) -> EntryDraftResult:
    prompt = build_entry_prompt(headword=headword)
    raw_response = _call_grok(prompt)
    payload = _parse_entry_payload(raw_response)
    payload = _normalize_payload(payload)
    payload = _resolve_form_values(payload)
    return EntryDraftResult(prompt=prompt, raw_response=raw_response, payload=payload)


def _call_grok(prompt: str) -> str:
    api_key = getattr(settings, "GROK_API_KEY", "").strip()
    if not api_key:
        raise ImproperlyConfigured("GROK_API_KEY is not configured.")

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=getattr(settings, "GROK_API_BASE_URL", "https://api.x.ai/v1"),
        )
        response = client.chat.completions.create(
            model=getattr(settings, "GROK_MODEL", "grok-3-mini"),
            temperature=float(getattr(settings, "GROK_TEMPERATURE", 0.2)),
            timeout=int(getattr(settings, "GROK_TIMEOUT_SECONDS", 180)),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict Persian dictionary assistant. "
                        "Return valid JSON only and do not include markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        choices = response.choices or []
        if not choices:
            raise ValueError("Grok returned no choices.")
        content = choices[0].message.content or ""
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Grok returned empty content.")
        return content.strip()
    except Exception:
        return _call_grok_via_http(
            api_key=api_key,
            prompt=prompt,
            base_url=getattr(settings, "GROK_API_BASE_URL", "https://api.x.ai/v1"),
            model=getattr(settings, "GROK_MODEL", "grok-3-mini"),
            temperature=float(getattr(settings, "GROK_TEMPERATURE", 0.2)),
            timeout_seconds=int(getattr(settings, "GROK_TIMEOUT_SECONDS", 180)),
        )


def _call_grok_via_http(
    *,
    api_key: str,
    prompt: str,
    base_url: str,
    model: str,
    temperature: float,
    timeout_seconds: int,
) -> str:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict Persian dictionary assistant. "
                    "Return valid JSON only and do not include markdown fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Grok HTTP error {exc.code}: {detail}") from exc
    except URLError as exc:
        raise ValueError(f"Grok network error: {exc.reason}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Grok returned non-JSON response.") from exc

    choices = parsed.get("choices") or []
    if not choices:
        raise ValueError("Grok returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Grok returned empty content.")
    return content.strip()


def _parse_entry_payload(raw_response: str) -> dict[str, Any]:
    text = raw_response.strip()
    fence_match = JSON_CODE_FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        object_match = JSON_OBJECT_RE.search(text)
        if object_match:
            text = object_match.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Could not parse JSON from Grok response.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Grok payload must be a JSON object.")
    return parsed


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    definition = str(payload.get("definition", "") or "").strip()
    history_context = str(payload.get("history_context", "") or "").strip()
    usage_example = str(payload.get("usage_example", "") or "").strip()
    category = normalize_persian(str(payload.get("category", "") or "").strip())

    epochs_raw = payload.get("epochs") or []
    if not isinstance(epochs_raw, list):
        epochs_raw = []
    epochs_clean: list[str] = []
    seen: set[str] = set()
    for item in epochs_raw:
        value = normalize_persian(str(item or "").strip())
        if not value or value in seen:
            continue
        seen.add(value)
        epochs_clean.append(value)

    allowed_epochs_raw, allowed_categories_raw = _allowed_taxonomy_lists()
    allowed_epochs = [normalize_persian(x) for x in allowed_epochs_raw]
    epochs = [epoch for epoch in epochs_clean if epoch in allowed_epochs]
    if not epochs and allowed_epochs:
        epochs = [allowed_epochs[0]]

    allowed_categories = [normalize_persian(x) for x in allowed_categories_raw]
    if allowed_categories and category not in allowed_categories:
        category = allowed_categories[0]

    return {
        "epochs": epochs,
        "category": category,
        "definition": definition,
        "history_context": history_context,
        "usage_example": usage_example,
    }


def _resolve_form_values(payload: dict[str, Any]) -> dict[str, Any]:
    category_id = None
    epoch_ids: list[int] = []
    category_target = normalize_persian(payload["category"])

    categories = EntryCategory.objects.only("id", "name")
    for category in categories:
        if normalize_persian(category.name) == category_target:
            category_id = category.id
            break

    epoch_targets = {normalize_persian(name) for name in payload["epochs"]}
    if epoch_targets:
        epochs = Epoch.objects.only("id", "name")
        epoch_ids = [epoch.id for epoch in epochs if normalize_persian(epoch.name) in epoch_targets]

    return {
        **payload,
        "category_id": category_id,
        "epoch_ids": epoch_ids,
    }


@lru_cache(maxsize=1)
def _prompt_template_text() -> str:
    path = Path(__file__).resolve().parent / "prompts" / "entry_draft_prompt.txt"
    return path.read_text(encoding="utf-8")


def _allowed_taxonomy_lists() -> tuple[list[str], list[str]]:
    epoch_names = [
        name
        for name in Epoch.objects.order_by("start_date", "id").values_list("name", flat=True)
        if str(name).strip()
    ]
    category_names = [
        name
        for name in EntryCategory.objects.order_by("name", "id").values_list("name", flat=True)
        if str(name).strip()
    ]
    return epoch_names, category_names
