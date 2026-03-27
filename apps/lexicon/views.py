from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.contrib.postgres.search import TrigramSimilarity
from django.http import Http404
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView
from django.utils.translation import gettext as _

from apps.users.permissions import ContributorRequiredMixin, EditorRequiredMixin

from .cache import build_versioned_cache_key
from .definition_page import definition_first_page_prefetch_queryset, fetch_definition_page, initial_definition_infinite_scroll_state
from .entry_list_page import fetch_entry_list_page
from .forms import DefinitionAttachmentFormSet, DefinitionForm, EntryForm, EntryInitialDefinitionForm
from .models import Definition, DefinitionVote, Entry, EntryQuerySet, Epoch, Page, SimilarEntryLink
from .normalization import normalize_persian


def _entry_admin_visibility(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_superuser or getattr(user, "role", None) == "admin")


def entry_visible_queryset(request):
    queryset = Entry.objects
    if _entry_admin_visibility(request.user):
        pass
    elif getattr(request.user, "is_authenticated", False):
        queryset = queryset.filter(Q(is_verified=True) | Q(created_by=request.user))
    else:
        queryset = queryset.filter(is_verified=True)
    return queryset


def _attach_definition_votes(request, definitions: list):
    if not definitions:
        return
    if not getattr(request.user, "is_authenticated", False):
        for definition in definitions:
            definition.current_user_vote = 0
        return
    ids = [d.id for d in definitions]
    vote_map = {
        vote.definition_id: vote.value
        for vote in DefinitionVote.objects.filter(user=request.user, definition_id__in=ids)
    }
    for definition in definitions:
        definition.current_user_vote = vote_map.get(definition.id, 0)


def _entry_detail_lexicon_flags(request, entry):
    can_add_definition = False
    can_contribute = False
    can_vote = False
    can_view_entry_description = False
    if request.user.is_authenticated:
        can_contribute = request.user.has_minimum_role(1) and request.user.is_email_verified
        can_vote = request.user.is_email_verified
        can_view_entry_description = _entry_admin_visibility(request.user)
        can_add_definition = not Definition.objects.filter(entry=entry, author=request.user).exists()
    return {
        "can_add_definition": can_add_definition,
        "can_contribute": can_contribute,
        "can_vote": can_vote,
        "can_view_entry_description": can_view_entry_description,
    }


class EntryListView(TemplateView):
    template_name = "lexicon/entry_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "")
        selected_epoch = self.request.GET.get("epoch", "").strip()
        page = fetch_entry_list_page(query=query, selected_epoch=selected_epoch, after_token=None)
        if page.invalid_epoch:
            messages.error(self.request, _("Invalid epoch."))
        context["entries"] = page.entries
        context["entry_list_has_more"] = page.has_more
        context["entry_list_next_cursor"] = page.next_cursor or ""
        context["query"] = query
        context["epochs"] = Epoch.objects.only("id", "name").order_by("start_date")
        context["selected_epoch"] = selected_epoch
        return context


class EntryListMoreView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "")
        selected_epoch = request.GET.get("epoch", "").strip()
        after = (request.GET.get("after") or "").strip()
        page = fetch_entry_list_page(query=query, selected_epoch=selected_epoch, after_token=after or None)
        if page.reset or page.invalid_epoch:
            return JsonResponse({"html": "", "has_more": False, "next_cursor": "", "reset": True})
        html = ""
        if page.entries:
            html = "".join(
                render_to_string("lexicon/_entry_list_item.html", {"entry": entry}, request=request) for entry in page.entries
            )
        return JsonResponse(
            {
                "html": html,
                "has_more": page.has_more,
                "next_cursor": page.next_cursor or "",
                "reset": False,
            }
        )


class PageDetailView(DetailView):
    model = Page
    template_name = "lexicon/page_detail.html"
    context_object_name = "page"
    slug_field = "address"
    slug_url_kwarg = "address"

    def get_object(self, queryset=None):
        queryset = queryset if queryset is not None else self.get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return super().get_object(queryset=queryset)

        address = self.kwargs.get(self.slug_url_kwarg)
        cache_key = build_versioned_cache_key(
            "page_detail",
            {"address": address},
            version_scope="pages",
        )
        cached_page = cache.get(cache_key)
        if cached_page is not None:
            return cached_page

        page = queryset.only("id", "address", "title", "content", "is_published", "created_at", "updated_at").filter(
            address=address
        ).first()
        if page is None:
            raise Http404
        cache.set(cache_key, page, timeout=settings.LEXICON_CACHE_TIMEOUT_PAGES)
        return page

    def get_queryset(self):
        queryset = Page.objects
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset
        return queryset.filter(is_published=True)


class EntrySuggestionView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "")
        normalized_query = normalize_persian(query).strip()
        if not normalized_query:
            return JsonResponse({"results": []})

        cache_key = build_versioned_cache_key(
            "entry_suggestions",
            {"query": normalized_query, "limit": 8},
            version_scope="entry_suggestions",
        )
        suggestions = cache.get(cache_key)
        if suggestions is None:
            limit = 8
            prefix_matches = list(
                Entry.objects.filter(is_verified=True, headword__startswith=normalized_query)
                .order_by("-created_at")
                .values("headword", "slug")[:limit]
            )
            suggestions = prefix_matches
            remaining = limit - len(prefix_matches)
            if remaining > 0 and len(normalized_query) >= 3:
                used_slugs = [item["slug"] for item in prefix_matches]
                fuzzy_matches = list(
                    Entry.objects.filter(is_verified=True)
                    .exclude(slug__in=used_slugs)
                    .filter(headword__trigram_similar=normalized_query)
                    .annotate(trigram_similarity=TrigramSimilarity("headword", normalized_query))
                    .filter(trigram_similarity__gte=EntryQuerySet.SUGGESTION_TRIGRAM_THRESHOLD)
                    .order_by("-trigram_similarity", "-created_at")
                    .values("headword", "slug")[:remaining]
                )
                suggestions = prefix_matches + fuzzy_matches
            cache.set(cache_key, suggestions, timeout=settings.LEXICON_CACHE_TIMEOUT_SUGGESTIONS)
        return JsonResponse({"results": suggestions})


class EntryDetailView(DetailView):
    model = Entry
    template_name = "lexicon/entry_detail.html"
    context_object_name = "entry"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        queryset = entry_visible_queryset(self.request)
        similar_qs = (
            SimilarEntryLink.objects.filter(similar_entry__is_verified=True)
            .select_related("similar_entry")
            .order_by("sort_order", "id")
        )
        defs_qs = definition_first_page_prefetch_queryset()
        return queryset.prefetch_related(
            "epochs",
            Prefetch("similar_links", queryset=similar_qs),
            Prefetch("definitions", queryset=defs_qs, to_attr="definitions_visible"),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entry = context["entry"]
        seen_ids: set[int] = set()
        seen_headwords: set[str] = set()
        similar_links = []
        for link in entry.similar_links.all():
            target = link.similar_entry
            if not target.is_verified:
                continue
            if target.pk in seen_ids:
                continue
            headword_key = normalize_persian(target.headword or "")
            if headword_key in seen_headwords:
                continue
            seen_ids.add(target.pk)
            seen_headwords.add(headword_key)
            similar_links.append(link)
        context["similar_entry_links"] = similar_links
        flags = _entry_detail_lexicon_flags(self.request, entry)
        context.update(flags)
        definitions_visible = list(entry.definitions_visible)
        _attach_definition_votes(self.request, definitions_visible)
        context["definitions_visible"] = definitions_visible
        context["definition_total_count"] = Definition.objects.filter(entry=entry).count()
        has_more, next_cursor = initial_definition_infinite_scroll_state(definitions_visible, context["definition_total_count"])
        context["definition_list_has_more"] = has_more
        context["definition_list_next_cursor"] = next_cursor
        if not entry.is_verified and (
            _entry_admin_visibility(self.request.user)
            or entry.created_by_id == getattr(self.request.user, "id", None)
        ):
            messages.warning(
                self.request,
                _("This entry is not verified yet. It is visible only to admins and the entry creator until verification."),
            )
        return context


class EntryDefinitionsMoreView(View):
    def get(self, request, *args, **kwargs):
        slug = kwargs["slug"]
        entry = get_object_or_404(entry_visible_queryset(request), slug=slug)
        after = (request.GET.get("after") or "").strip()
        page = fetch_definition_page(entry_id=entry.pk, after_token=after or None)
        if page.reset:
            return JsonResponse({"html": "", "has_more": False, "next_cursor": "", "reset": True})
        _attach_definition_votes(request, page.definitions)
        flags = _entry_detail_lexicon_flags(request, entry)
        html = ""
        if page.definitions:
            html = "".join(
                render_to_string(
                    "lexicon/_definition_card.html",
                    {"definition": definition, "entry": entry, **flags},
                    request=request,
                )
                for definition in page.definitions
            )
        return JsonResponse(
            {
                "html": html,
                "has_more": page.has_more,
                "next_cursor": page.next_cursor or "",
                "reset": False,
            }
        )


class EntryCreateView(ContributorRequiredMixin, CreateView):
    model = Entry
    form_class = EntryForm
    template_name = "lexicon/entry_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_definition_form(self):
        if self.request.method == "POST":
            return EntryInitialDefinitionForm(self.request.POST, prefix="definition")
        return EntryInitialDefinitionForm(prefix="definition")

    def get_attachment_formset(self):
        if self.request.method == "POST":
            return DefinitionAttachmentFormSet(
                self.request.POST,
                self.request.FILES,
                prefix="attachments",
            )
        return DefinitionAttachmentFormSet(prefix="attachments")

    def _has_initial_attachment_input(self) -> bool:
        total_forms = int(self.request.POST.get("attachments-TOTAL_FORMS", 0) or 0)
        for index in range(total_forms):
            link_key = f"attachments-{index}-link"
            image_key = f"attachments-{index}-image"
            link_value = (self.request.POST.get(link_key) or "").strip()
            if link_value or self.request.FILES.get(image_key):
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("definition_form", self.get_definition_form())
        context.setdefault("attachment_formset", self.get_attachment_formset())
        context["is_create"] = True
        return context

    def form_valid(self, form):
        definition_form = self.get_definition_form()
        attachment_formset = self.get_attachment_formset()
        if not definition_form.is_valid():
            return self.form_invalid(form, definition_form=definition_form, attachment_formset=attachment_formset)

        definition_content = definition_form.cleaned_data.get("content", "").strip()
        has_initial_attachment_input = self._has_initial_attachment_input()
        if has_initial_attachment_input and not definition_content:
            definition_form.add_error("content", _("Definition text is required when adding examples."))
            attachment_formset.is_valid()
            return self.form_invalid(form, definition_form=definition_form, attachment_formset=attachment_formset)
        if definition_content and not attachment_formset.is_valid():
            return self.form_invalid(form, definition_form=definition_form, attachment_formset=attachment_formset)

        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
        self.object.save()
        form.save_m2m()
        if definition_content:
            definition_form.save(author=self.request.user, entry=self.object, attachment_formset=attachment_formset)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, definition_form=None, attachment_formset=None):
        if definition_form is None:
            definition_form = self.get_definition_form()
        if attachment_formset is None:
            attachment_formset = self.get_attachment_formset()
        return self.render_to_response(
            self.get_context_data(
                form=form,
                definition_form=definition_form,
                attachment_formset=attachment_formset,
            )
        )

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_create"] = False
        return context

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
