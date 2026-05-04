"""infrastructure/identity/uuid_id_generator.py — UUID-based IIdGenerator."""
from __future__ import annotations

import uuid

from application.interfaces.i_id_generator import IIdGenerator


class UuidIdGenerator(IIdGenerator):
    """Generates RFC 4122 UUID4 strings as entity identifiers."""

    def new_id(self) -> str:
        return str(uuid.uuid4())
