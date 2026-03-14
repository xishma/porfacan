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

    def __str__(self) -> str:
        return self.email
