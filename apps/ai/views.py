import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views import View

from apps.lexicon.normalization import normalize_persian
from apps.users.permissions import ContributorRequiredMixin

from .models import EntryAIDraftJob
from .permissions import user_in_ai_group
from .services import build_entry_prompt
from .tasks import generate_entry_ai_draft


class EntryAIDraftCreateView(ContributorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not user_in_ai_group(request.user):
            return JsonResponse({"error": _("You do not have AI access.")}, status=403)
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": _("Invalid JSON payload.")}, status=400)

        headword = normalize_persian(str(data.get("headword", "")).strip())
        if not headword:
            return JsonResponse({"error": _("Headword is required.")}, status=400)

        job = EntryAIDraftJob.objects.create(
            user=request.user,
            headword=headword,
            prompt=build_entry_prompt(headword=headword),
        )
        generate_entry_ai_draft.delay(job.id)
        return JsonResponse(
            {
                "job_id": job.id,
                "status": job.status,
            },
            status=202,
        )


class EntryAIDraftStatusView(ContributorRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if not user_in_ai_group(request.user):
            return JsonResponse({"error": _("You do not have AI access.")}, status=403)
        job = get_object_or_404(EntryAIDraftJob, pk=kwargs["job_id"], user=request.user)
        payload = {
            "job_id": job.id,
            "status": job.status,
            "error": job.error_message if job.status == EntryAIDraftJob.Status.FAILED else "",
        }
        if job.status == EntryAIDraftJob.Status.SUCCEEDED:
            payload["result"] = job.result_payload or {}
        return JsonResponse(payload)
