"""application/interfaces/i_current_user_service.py — Current-user context abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.enums.user_role import UserRole
from domain.exceptions.domain_exceptions import UnauthorizedOperationError


class ICurrentUserService(ABC):
    """Provides the identity and role of the currently-authenticated user.

    Implementations are injected into services that need role-based access
    control, removing the need to pass actor information through every method.
    """

    @property
    @abstractmethod
    def username(self) -> Optional[str]:
        """The username of the currently executing principal, or None if anonymous."""

    @property
    @abstractmethod
    def role(self) -> UserRole:
        """The role assigned to the current user."""

    @property
    def is_investigator(self) -> bool:
        """True when the current user holds at least the Investigator role."""
        return self.role >= UserRole.INVESTIGATOR

    def ensure_investigator_access(self, operation: str) -> None:
        """Raise :class:`UnauthorizedOperationError` if the user is not an Investigator."""
        if not self.is_investigator:
            raise UnauthorizedOperationError(
                username=self.username or "anonymous",
                operation=operation,
                required_role="Investigator",
            )
