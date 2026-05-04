"""application/interfaces/i_template_repository.py - Typed template repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional

from application.interfaces.i_repository import IRepository
from domain.entities.template import Template


class ITemplateRepository(IRepository[Template]):

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Template]:
        """Return template by unique name."""

    @abstractmethod
    def get_published(self) -> List[Template]:
        """Return published templates."""

    @abstractmethod
    def get_by_category(self, category: str) -> List[Template]:
        """Return templates by category."""

    @abstractmethod
    def search(self, query: str) -> List[Template]:
        """Search by name/description/content/tags."""
