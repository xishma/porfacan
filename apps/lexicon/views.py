from django.views.generic import ListView

from .models import Entry


class EntryListView(ListView):
    model = Entry
    template_name = "lexicon/entry_list.html"
    context_object_name = "entries"
    paginate_by = 20
    queryset = Entry.objects.select_related("epoch").all()
