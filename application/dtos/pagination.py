"""application/dtos/pagination.py - Common pagination DTOs."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Generic, List, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PaginationParams:
    page: int = 1
    page_size: int = 50

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if self.page_size < 1:
            raise ValueError("page_size must be >= 1")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass
class PagedResult(Generic[T]):
    items: List[T] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 50

    @property
    def total_pages(self) -> int:
        if self.total_count == 0:
            return 0
        return ceil(self.total_count / self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1
