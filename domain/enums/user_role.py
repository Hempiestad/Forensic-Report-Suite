"""domain/enums/user_role.py — UserRole enum for role-based access control."""
from __future__ import annotations

from enum import IntEnum


class UserRole(IntEnum):
    """
    Role levels for users of the forensic system.

    Integer values mirror the C# definition (Examiner = 0, Investigator = 1)
    so that comparisons like ``role >= UserRole.INVESTIGATOR`` work naturally.
    """

    EXAMINER = 0
    INVESTIGATOR = 1

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").title()

    def can_perform_investigator_actions(self) -> bool:
        """Return True if the role is allowed to perform Investigator-only operations."""
        return self >= UserRole.INVESTIGATOR
