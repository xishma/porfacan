from django.urls import path

from .views import (
    DefinitionCreateView,
    DefinitionVoteView,
    EntryCreateView,
    EntryDefinitionsMoreView,
    EntryDetailView,
    EntryListMoreView,
    EntryListView,
    EntrySuggestionView,
    EntryUpdateView,
    PageDetailView,
)

app_name = "lexicon"

urlpatterns = [
    path("", EntryListView.as_view(), name="entry-list"),
    path("entries/feed/", EntryListMoreView.as_view(), name="entry-list-more"),
    path("pages/<str:address>/", PageDetailView.as_view(), name="page-detail"),
    path("entries/suggest/", EntrySuggestionView.as_view(), name="entry-suggest"),
    path("entries/new/", EntryCreateView.as_view(), name="entry-create"),
    path("entries/<str:slug>/definitions/feed/", EntryDefinitionsMoreView.as_view(), name="entry-definitions-more"),
    path("entries/<str:slug>/definitions/new/", DefinitionCreateView.as_view(), name="definition-create"),
    path("entries/<str:slug>/", EntryDetailView.as_view(), name="entry-detail"),
    path("entries/<str:slug>/edit/", EntryUpdateView.as_view(), name="entry-update"),
    path("definitions/<int:pk>/vote/", DefinitionVoteView.as_view(), name="definition-vote"),
]
