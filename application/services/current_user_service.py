"""application/services/current_user_service.py — ICurrentUserService implementations."""
from __future__ import annotations

from typing import Optional

from application.interfaces.i_current_user_service import ICurrentUserService
from domain.enums.user_role import UserRole


class SystemUserService(ICurrentUserService):
    """A no-op implementation that acts as the 'system' user with Investigator role.

    Use this as the default when no real authentication context is available —
    it grants full access while remaining explicit about the absence of a real
    user (the username is 'system' rather than None).
    """

    @property
    def username(self) -> Optional[str]:
        return "system"

    @property
    def role(self) -> UserRole:
        return UserRole.INVESTIGATOR


class StaticCurrentUserService(ICurrentUserService):
    """A simple implementation that wraps fixed username/role values.

    Useful for unit tests and CLI tools where the caller knows the actor
    up-front and wants to pass it once at construction time.
    """

    def __init__(self, username: str, role: UserRole) -> None:
        self._username = username
        self._role = role

    @property
    def username(self) -> Optional[str]:
        return self._username

    @property
    def role(self) -> UserRole:
        return self._role
