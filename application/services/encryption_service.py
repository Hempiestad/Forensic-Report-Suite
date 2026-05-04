"""application/services/encryption_service.py — FernetEncryptionService (Phase 6)."""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from application.interfaces.i_encryption_service import IEncryptionService
from domain.exceptions.domain_exceptions import DomainValidationError
import hashlib
import hmac



class FernetEncryptionService(IEncryptionService):
    """AES-128-CBC (Fernet) symmetric encryption service."""

    def __init__(self, key: bytes | str | None = None) -> None:
        """Initialise with an existing Fernet key or generate a new one.

        Args:
            key: URL-safe base64-encoded 32-byte Fernet key (bytes or str).
                 If *None*, a new key is generated automatically.
        """
        if key is None:
            key = Fernet.generate_key()
        if isinstance(key, str):
            key = key.encode()
        self._fernet = Fernet(key)

    # ------------------------------------------------------------------ #
    # Text                                                                 #
    # ------------------------------------------------------------------ #

    def encrypt_text(self, plaintext: str) -> str:
        if not isinstance(plaintext, str):
            raise DomainValidationError("plaintext", "Input must be a string.")
        token: bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt_text(self, ciphertext: str) -> str:
        if not isinstance(ciphertext, str):
            raise DomainValidationError("ciphertext", "Input must be a string.")
        try:
            plaintext: bytes = self._fernet.decrypt(ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            raise DomainValidationError("ciphertext", "Decryption failed — invalid or corrupt token.") from exc
        return plaintext.decode("utf-8")

    # ------------------------------------------------------------------ #
    # Bytes                                                                #
    # ------------------------------------------------------------------ #

    def encrypt_bytes(self, data: bytes) -> bytes:
        if not isinstance(data, (bytes, bytearray)):
            raise DomainValidationError("data", "Input must be bytes.")
        return self._fernet.encrypt(bytes(data))

    def decrypt_bytes(self, data: bytes) -> bytes:
        if not isinstance(data, (bytes, bytearray)):
            raise DomainValidationError("data", "Input must be bytes.")
        try:
            return self._fernet.decrypt(bytes(data))
        except InvalidToken as exc:
            raise DomainValidationError("data", "Decryption failed — invalid or corrupt token.") from exc

    # ------------------------------------------------------------------ #
    # Hashing                                                             #
    # ------------------------------------------------------------------ #

    def compute_hash(self, data: "str | bytes") -> str:
        """Return the SHA-256 hex-digest of *data*."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def verify_hash(self, data: "str | bytes", expected_hash: str) -> bool:
        """Return True if SHA-256(*data*) == *expected_hash* (constant-time)."""
        actual = self.compute_hash(data)
        return hmac.compare_digest(actual, expected_hash.lower())
