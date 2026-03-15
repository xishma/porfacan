from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.models import EmailAddress


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
