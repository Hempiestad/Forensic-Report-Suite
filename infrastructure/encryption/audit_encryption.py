"""AES-256-GCM encryption manager for audit trail details.

Encrypts the ``details`` field of AuditEntry objects before persistence and
decrypts on load, making stored audit payloads confidential while keeping the
SHA-256 hash chain intact (hashes are always computed on plaintext).

Encrypted storage format (stored as a JSON dict in the details column):
    {
        "__enc": true,
        "v": 1,
        "kid": "<key_id>",
        "nonce": "<base64url-encoded 12-byte nonce>",
        "ct": "<base64url-encoded ciphertext+GCM tag>"
    }

The GCM tag (16 bytes) is appended to the ciphertext by ``cryptography``'s
AESGCM implementation, so ``ct`` contains both.

Backward compatibility:
    If a stored ``details`` dict does NOT contain ``"__enc": true``, it is
    returned as-is (plaintext).  This means existing unencrypted audit rows
    continue to load correctly after encryption is enabled.

Usage:
    from infrastructure.encryption.key_vault import InMemoryKeyVault
    from infrastructure.encryption.audit_encryption import AuditEncryptionManager

    key   = AuditEncryptionManager.generate_key()
    vault = InMemoryKeyVault({"audit-v1": key})
    mgr   = AuditEncryptionManager(vault)

    encrypted = mgr.encrypt_details({"action": "report saved", "by": "alice"})
    plaintext = mgr.decrypt_details(encrypted)
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict

from infrastructure.encryption.key_vault import IKeyVault

# Sentinel key present in every encrypted payload dict
_ENC_SENTINEL = "__enc"
_FORMAT_VERSION = 1


class AuditEncryptionManager:
    """Encrypt and decrypt AuditEntry ``details`` dicts using AES-256-GCM.

    Args:
        vault:  Key vault that provides raw 32-byte AES keys by ID.
        key_id: Identifier of the key to use for new encryptions.
                Decryption always uses the ``kid`` stored inside the payload,
                so key rotation is supported transparently.
    """

    def __init__(self, vault: IKeyVault, key_id: str = "audit-v1") -> None:
        self._vault = vault
        self._key_id = key_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encrypt_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize *details* to JSON and encrypt with AES-256-GCM.

        Returns a sentinel dict that can be serialised as JSON and stored in
        the ``details`` column (TEXT for SQLite, JSONB for PostgreSQL).
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = self._vault.get_key(self._key_id)
        nonce = os.urandom(12)  # 96-bit nonce — GCM standard
        aesgcm = AESGCM(key)

        plaintext_bytes = json.dumps(details, sort_keys=True, default=str).encode("utf-8")
        ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext_bytes, None)

        return {
            _ENC_SENTINEL: True,
            "v": _FORMAT_VERSION,
            "kid": self._key_id,
            "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
            "ct": base64.urlsafe_b64encode(ciphertext_with_tag).decode("ascii"),
        }

    def decrypt_details(self, encrypted: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt a payload returned by :meth:`encrypt_details`.

        If *encrypted* is not a recognised encrypted payload (no ``__enc``
        sentinel), it is returned unchanged — this handles legacy plaintext
        rows transparently.

        Raises:
            ValueError: if decryption fails (wrong key, tampered ciphertext).
        """
        if not self.is_encrypted(encrypted):
            return encrypted  # backward-compat: plaintext row

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key_id: str = encrypted.get("kid", self._key_id)
        key = self._vault.get_key(key_id)

        try:
            nonce = base64.urlsafe_b64decode(encrypted["nonce"] + "==")
            ct = base64.urlsafe_b64decode(encrypted["ct"] + "==")
            aesgcm = AESGCM(key)
            plaintext_bytes = aesgcm.decrypt(nonce, ct, None)
            return json.loads(plaintext_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError(
                f"AES-256-GCM decryption failed for audit entry (kid={key_id}). "
                "The ciphertext may be tampered or the wrong key was used."
            ) from exc

    @staticmethod
    def is_encrypted(data: Dict[str, Any]) -> bool:
        """Return True if *data* is an encrypted audit details payload."""
        return isinstance(data, dict) and data.get(_ENC_SENTINEL) is True

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def generate_key() -> bytes:
        """Generate a cryptographically random 32-byte (256-bit) AES key.

        The returned bytes can be stored as ``base64.urlsafe_b64encode(key).decode()``
        in the ``AUDIT_ENCRYPTION_KEY`` environment variable.
        """
        return os.urandom(32)

    @staticmethod
    def key_to_env_string(key: bytes) -> str:
        """Encode *key* as a base64url string suitable for environment variables."""
        return base64.urlsafe_b64encode(key).decode("ascii")
