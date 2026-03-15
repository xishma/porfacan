from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    class Roles(models.TextChoices):
        VISITOR = "visitor", _("Visitor")
        CONTRIBUTOR = "contributor", _("Contributor")
        EDITOR = "editor", _("Editor")
        MODERATOR = "moderator", _("Moderator")
        ADMIN = "admin", _("Admin")

    username = None
    email = models.EmailField(
        unique=True,
        verbose_name=_("Email"),
        db_index=True,
    )
    reputation_iq = models.IntegerField(
        default=0,
        verbose_name=_("Reputation IQ"),
        db_index=True,
    )
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.VISITOR,
        verbose_name=_("Role"),
        db_index=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    _ROLE_LEVELS = {
        Roles.VISITOR: 0,
        Roles.CONTRIBUTOR: 1,
        Roles.EDITOR: 2,
        Roles.MODERATOR: 3,
        Roles.ADMIN: 4,
    }

    @property
    def role_level(self) -> int:
        if self.is_superuser:
            return self._ROLE_LEVELS[self.Roles.ADMIN]
        return self._ROLE_LEVELS.get(self.role, 0)

    def has_minimum_role(self, minimum_level: int) -> bool:
        return self.is_authenticated and self.role_level >= minimum_level

    @property
    def has_social_login(self) -> bool:
        from allauth.socialaccount.models import SocialAccount

        if not self.pk:
            return False
        return SocialAccount.objects.filter(user=self).exists()

    @property
    def is_email_verified(self) -> bool:
        from allauth.account.models import EmailAddress

        if not self.pk:
            return False
        return EmailAddress.objects.filter(
            user=self,
            email__iexact=self.email,
            verified=True,
        ).exists()

    def __str__(self) -> str:
        return self.email

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
