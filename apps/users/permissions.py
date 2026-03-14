from __future__ import annotations

from typing import Callable

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


def _has_minimum_role(user, minimum_level: int) -> bool:
    return bool(getattr(user, "has_minimum_role", lambda _: False)(minimum_level))


def minimum_role_required(minimum_level: int):
    def decorator(view_func: Callable):
        return login_required(
            user_passes_test(
                lambda user: _has_minimum_role(user, minimum_level),
                login_url="users:login",
            )(view_func)
        )

    return decorator


def contributor_required(view_func: Callable):
    return minimum_role_required(1)(view_func)


def editor_required(view_func: Callable):
    return minimum_role_required(2)(view_func)


class MinimumRoleRequiredMixin(LoginRequiredMixin):
    minimum_role_level = 0
    login_url = "users:login"

    def dispatch(self, request, *args, **kwargs):
        if not _has_minimum_role(request.user, self.minimum_role_level):
            raise PermissionDenied("Insufficient role level for this action.")
        return super().dispatch(request, *args, **kwargs)


class ContributorRequiredMixin(MinimumRoleRequiredMixin):
    minimum_role_level = 1


class EditorRequiredMixin(MinimumRoleRequiredMixin):
    minimum_role_level = 2
