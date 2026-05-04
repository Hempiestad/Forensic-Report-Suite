"""application/interfaces/i_encryption_service.py - Encryption abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod


class IEncryptionService(ABC):

    @abstractmethod
    def encrypt_text(self, plaintext: str) -> bytes:
        """Encrypt UTF-8 text into binary cipher payload."""

    @abstractmethod
    def decrypt_text(self, ciphertext: bytes) -> str:
        """Decrypt binary payload back to UTF-8 text."""

    @abstractmethod
    def encrypt_bytes(self, raw_data: bytes) -> bytes:
        """Encrypt raw bytes payload."""

    @abstractmethod
    def decrypt_bytes(self, ciphertext: bytes) -> bytes:
        """Decrypt raw bytes payload."""

    @abstractmethod
    def compute_hash(self, data: "str | bytes") -> str:
        """Compute a SHA-256 hex-digest of *data*.

        Accepts either a :class:`str` (encoded as UTF-8 before hashing)
        or raw :class:`bytes`.  Returns a lowercase hex string.
        """

    @abstractmethod
    def verify_hash(self, data: "str | bytes", expected_hash: str) -> bool:
        """Return True if the SHA-256 hash of *data* matches *expected_hash*.

        Comparison is performed in constant time to prevent timing attacks.
        """
