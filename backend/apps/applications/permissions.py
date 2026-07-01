"""
Application Management System — Permissions

Custom DRF permission classes that enforce owner-only access to
application data. All application records are private to the user
who created them, with admin staff having full access for support.

Security Model:
    1. Queryset filtering (get_queryset) — primary defense, filters at DB level
    2. Object-level permissions (this module) — secondary defense, per-object check
    3. Both layers must pass for access to be granted
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsApplicationOwner(BasePermission):
    """
    Object-level permission granting access only to the application owner.

    For top-level JobApplication objects:
        Checks request.user == obj.user

    For nested objects (notes, timeline, interviews, offers):
        Traverses to the parent application and checks ownership there.

    Staff users (is_staff=True) bypass this check entirely for
    administrative support purposes.
    """

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        # Admin/staff bypass — full access for support
        if request.user and request.user.is_staff:
            return True

        # Direct application ownership (JobApplication model)
        if hasattr(obj, "user_id"):
            return obj.user_id == request.user.id

        # Nested resource — traverse to parent application
        if hasattr(obj, "application"):
            return obj.application.user_id == request.user.id

        return False
