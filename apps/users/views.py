from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, UpdateView
from allauth.account.models import EmailAddress

from .forms import TailwindAuthenticationForm, UserProfileForm, UserRegistrationForm
from .tasks import send_verification_email_task

User = get_user_model()


def _oauth_provider_context() -> dict:
    return {
        "google_oauth_enabled": bool(
            settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET
        ),
        "x_oauth_enabled": bool(settings.X_OAUTH_CLIENT_ID and settings.X_OAUTH_CLIENT_SECRET),
    }


def _sync_primary_email_address(user, verified: bool) -> EmailAddress:
    EmailAddress.objects.filter(user=user, primary=True).exclude(email__iexact=user.email).update(primary=False)
    email_address, _ = EmailAddress.objects.update_or_create(
        user=user,
        email=user.email,
        defaults={"primary": True, "verified": verified},
    )
    return email_address


class UserLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = TailwindAuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_oauth_provider_context())
        return context


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("lexicon:entry-list")


class UserRegisterView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = "users/register.html"
    success_url = reverse_lazy("users:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_oauth_provider_context())
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.role = User.Roles.CONTRIBUTOR
        self.object.save()
        email_address = _sync_primary_email_address(self.object, verified=False)
        send_verification_email_task.delay(email_address.pk, signup=True)
        messages.success(
            self.request,
            _("Your account has been created. Please verify your email before contributing."),
        )
        return HttpResponseRedirect(self.get_success_url())


class UserProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = "users/profile.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["can_change_email"] = not self.request.user.has_social_login
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_change_email"] = not self.request.user.has_social_login
        context["is_email_verified"] = self.request.user.is_email_verified
        return context

    def form_valid(self, form):
        current_email = User.objects.only("email").get(pk=self.request.user.pk).email
        response = super().form_valid(form)
        if current_email.lower() != self.object.email.lower():
            email_address = _sync_primary_email_address(self.object, verified=False)
            send_verification_email_task.delay(email_address.pk, signup=False)
            messages.warning(
                self.request,
                _("Your email was updated. Please verify the new address before contributing."),
            )
        else:
            messages.success(self.request, _("Profile updated successfully."))
        return response


class ResendVerificationEmailView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if request.user.is_email_verified:
            messages.info(request, _("Your email is already verified."))
            return redirect("users:profile")

        email_address = _sync_primary_email_address(request.user, verified=False)
        send_verification_email_task.delay(email_address.pk, signup=False)
        messages.success(request, _("Verification email sent. Check your inbox."))
        return redirect("users:profile")
