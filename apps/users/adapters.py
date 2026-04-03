from django.conf import settings
from django.urls import reverse

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.models import EmailAddress


class UserAccountAdapter(DefaultAccountAdapter):
    """Customize account behavior for app-level defaults."""

    def get_email_confirmation_url(self, request, emailconfirmation):
        canonical = (getattr(settings, "SITE_CANONICAL_URL", "") or "").strip().rstrip("/")
        if canonical:
            path = reverse("account_confirm_email", args=[emailconfirmation.key])
            return f"{canonical}{path}"
        return super().get_email_confirmation_url(request, emailconfirmation)


class UserSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Set default role for first-time social signups."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)

        EmailAddress.objects.filter(user=user, primary=True).exclude(email__iexact=user.email).update(primary=False)
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True, "verified": True},
        )

        if sociallogin.is_existing:
            return user

        if user.role == user.Roles.VISITOR:
            user.role = user.Roles.CONTRIBUTOR
            user.save(update_fields=["role"])

        return user
