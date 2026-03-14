from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class Roles(models.TextChoices):
        VISITOR = "visitor", "Visitor"
        CONTRIBUTOR = "contributor", "Contributor"
        EDITOR = "editor", "Editor"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Admin"

    username = None
    email = models.EmailField(unique=True)
    reputation_iq = models.IntegerField(default=0)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.VISITOR)

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

    def __str__(self) -> str:
        return self.email
