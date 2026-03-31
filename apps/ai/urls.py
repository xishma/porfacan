from django.urls import path

from .views import EntryAIDraftCreateView, EntryAIDraftStatusView

app_name = "ai"

urlpatterns = [
    path("entry-drafts/", EntryAIDraftCreateView.as_view(), name="entry-draft-create"),
    path("entry-drafts/<int:job_id>/", EntryAIDraftStatusView.as_view(), name="entry-draft-status"),
]
