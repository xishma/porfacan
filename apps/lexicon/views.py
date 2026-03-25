from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.utils.translation import gettext as _

from apps.users.permissions import ContributorRequiredMixin, EditorRequiredMixin

from .forms import DefinitionAttachmentFormSet, DefinitionForm, EntryForm
from .models import Definition, DefinitionVote, Entry, Epoch


class EntryListView(ListView):
    model = Entry
    template_name = "lexicon/entry_list.html"
    context_object_name = "entries"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Entry.objects.filter(is_verified=True)
            .prefetch_related("epochs", "definitions")
            .with_hot_rank()
        )
        query = self.request.GET.get("q", "")
        selected_epoch = self.request.GET.get("epoch", "").strip()
        if query:
            queryset = queryset.search(query)
        if selected_epoch:
            epochs = Epoch.objects.filter(name__iexact=selected_epoch)
            if not epochs.exists():
                messages.error(self.request, _("Invalid epoch."))
                return queryset.none()

            queryset = queryset.filter(epochs__in=epochs)
        return queryset.order_by("-hot_rank", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["epochs"] = Epoch.objects.only("id", "name").order_by("start_date")
        context["selected_epoch"] = self.request.GET.get("epoch", "").strip()
        return context


class EntrySuggestionView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "")
        suggestions = list(Entry.objects.filter(is_verified=True).suggestions(query=query, limit=8))
        return JsonResponse({"results": suggestions})


class EntryDetailView(DetailView):
    model = Entry
    template_name = "lexicon/entry_detail.html"
    context_object_name = "entry"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Entry.objects.filter(is_verified=True).prefetch_related(
            "epochs",
            "definitions__author",
            "definitions__attachments",
            "definitions__votes",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_add_definition"] = False
        context["can_contribute"] = False
        context["can_vote"] = False
        context["can_view_entry_description"] = False
        if self.request.user.is_authenticated:
            context["can_contribute"] = (
                self.request.user.has_minimum_role(1) and self.request.user.is_email_verified
            )
            context["can_vote"] = self.request.user.is_email_verified
            context["can_view_entry_description"] = (
                self.request.user.is_superuser or getattr(self.request.user, "role", None) == "admin"
            )
            context["can_add_definition"] = not Definition.objects.filter(
                entry=context["entry"],
                author=self.request.user,
            ).exists()
            definition_ids = [definition.id for definition in context["entry"].definitions.all()]
            vote_map = {
                vote.definition_id: vote.value
                for vote in DefinitionVote.objects.filter(
                    user=self.request.user,
                    definition_id__in=definition_ids,
                )
            }
            for definition in context["entry"].definitions.all():
                definition.current_user_vote = vote_map.get(definition.id, 0)
        else:
            for definition in context["entry"].definitions.all():
                definition.current_user_vote = 0
        return context


class EntryCreateView(ContributorRequiredMixin, CreateView):
    model = Entry
    form_class = EntryForm
    template_name = "lexicon/entry_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("lexicon:entry-detail", kwargs={"slug": self.object.slug})


class EntryUpdateView(EditorRequiredMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = "lexicon/entry_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("lexicon:entry-detail", kwargs={"slug": self.object.slug})


class DefinitionCreateView(ContributorRequiredMixin, CreateView):
    model = Definition
    form_class = DefinitionForm
    template_name = "lexicon/definition_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.entry = get_object_or_404(Entry, slug=kwargs["slug"])
        if request.user.is_authenticated and Definition.objects.filter(entry=self.entry, author=request.user).exists():
            messages.error(request, _("You have already submitted a definition for this entry."))
            return HttpResponseRedirect(reverse("lexicon:entry-detail", kwargs={"slug": self.entry.slug}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        attachment_formset = self.get_attachment_formset()
        if not attachment_formset.is_valid():
            return self.form_invalid(form, attachment_formset=attachment_formset)
        self.object = form.save(author=self.request.user, entry=self.entry, attachment_formset=attachment_formset)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, attachment_formset=None):
        if attachment_formset is None:
            attachment_formset = self.get_attachment_formset()
        return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))

    def get_attachment_formset(self):
        if self.request.method == "POST":
            return DefinitionAttachmentFormSet(
                self.request.POST,
                self.request.FILES,
                prefix="attachments",
            )
        return DefinitionAttachmentFormSet(prefix="attachments")

    def get_success_url(self):
        return reverse("lexicon:entry-detail", kwargs={"slug": self.entry.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entry"] = self.entry
        context.setdefault("attachment_formset", self.get_attachment_formset())
        return context


class DefinitionVoteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("users:login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": _("Authentication required.")}, status=401)
        if not request.user.is_email_verified:
            return JsonResponse(
                {"error": _("Please verify your email first in your profile page.")},
                status=403,
            )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        definition = get_object_or_404(Definition, pk=kwargs["pk"])
        try:
            vote_value = int(request.POST.get("value", 0))
        except (TypeError, ValueError):
            return JsonResponse({"error": _("Invalid vote value.")}, status=400)
        if vote_value not in (DefinitionVote.VoteValue.UPVOTE, DefinitionVote.VoteValue.DOWNVOTE):
            return JsonResponse({"error": _("Invalid vote value.")}, status=400)

        vote, created = DefinitionVote.objects.get_or_create(
            definition=definition,
            user=request.user,
            defaults={"value": vote_value},
        )
        current_user_vote = vote_value
        if not created:
            if vote.value == vote_value:
                vote.delete()
                current_user_vote = 0
            else:
                vote.value = vote_value
                vote.save(update_fields=["value", "updated_at"])
                current_user_vote = vote_value

        definition.refresh_vote_metrics()
        definition.refresh_from_db(fields=["upvotes", "downvotes", "reputation_score", "hot_score_value"])
        return JsonResponse(
            {
                "upvotes": definition.upvotes,
                "downvotes": definition.downvotes,
                "reputation_score": definition.reputation_score,
                "hot_score": definition.hot_score,
                "user_vote": current_user_vote,
            }
        )
