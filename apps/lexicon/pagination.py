import base64
import json
from typing import Any

CURSOR_VERSION = 1
LIST_PAGE_SIZE = 10


def encode_cursor(payload: dict[str, Any]) -> str:
    data = json.dumps({"v": CURSOR_VERSION, **payload}, separators=(",", ":"), ensure_ascii=False)
    raw = data.encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token: str) -> dict[str, Any] | None:
    if not token or not isinstance(token, str):
        return None
    pad = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(token + pad)
        obj = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict) or obj.get("v") != CURSOR_VERSION:
        return None
    return obj
