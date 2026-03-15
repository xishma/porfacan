from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class UserSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Set default role for first-time social signups."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        if sociallogin.is_existing:
            return user

        if user.role == user.Roles.VISITOR:
            user.role = user.Roles.CONTRIBUTOR
            user.save(update_fields=["role"])

        return user
