from django.urls import path

from .views import EntryListView

app_name = "lexicon"

urlpatterns = [
    path("", EntryListView.as_view(), name="entry-list"),
]
