from __future__ import annotations

from typing import Callable

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _


def _has_minimum_role(user, minimum_level: int) -> bool:
    has_role = bool(getattr(user, "has_minimum_role", lambda _: False)(minimum_level))
    if not has_role:
        return False
    if minimum_level >= 1:
        return bool(getattr(user, "is_email_verified", False))
    return True


def minimum_role_required(minimum_level: int):
    def decorator(view_func: Callable):
        @login_required(login_url="users:login")
        def _wrapped(request, *args, **kwargs):
            if not _has_minimum_role(request.user, minimum_level):
                if minimum_level >= 1 and not request.user.is_email_verified:
                    raise PermissionDenied(_("Please verify your email before contributing."))
                raise PermissionDenied(_("Insufficient role level for this action."))
            return view_func(request, *args, **kwargs)

        return _wrapped

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
            if request.user.is_authenticated and self.minimum_role_level >= 1 and not request.user.is_email_verified:
                raise PermissionDenied(_("Please verify your email before contributing."))
            raise PermissionDenied(_("Insufficient role level for this action."))
        return super().dispatch(request, *args, **kwargs)


class ContributorRequiredMixin(MinimumRoleRequiredMixin):
    minimum_role_level = 1


class EditorRequiredMixin(MinimumRoleRequiredMixin):
    minimum_role_level = 2
