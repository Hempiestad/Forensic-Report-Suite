"""Key vault abstractions for audit trail encryption.

Provides a simple IKeyVault protocol and concrete implementations:
- InMemoryKeyVault   — pass raw bytes; primarily for testing.
- EnvironmentKeyVault — reads a base64url-encoded 32-byte key from an
                        environment variable (default: AUDIT_ENCRYPTION_KEY).

Usage example (production):
    vault = EnvironmentKeyVault()          # reads AUDIT_ENCRYPTION_KEY
    mgr   = AuditEncryptionManager(vault)

Usage example (tests):
    key   = AuditEncryptionManager.generate_key()
    vault = InMemoryKeyVault({"audit-v1": key})
    mgr   = AuditEncryptionManager(vault)
"""
from __future__ import annotations

import base64
import os
from typing import Dict, Protocol, runtime_checkable


@runtime_checkable
class IKeyVault(Protocol):
    """Minimal interface for retrieving raw symmetric encryption keys."""

    def get_key(self, key_id: str) -> bytes:
        """Return the raw key bytes for *key_id*.

        Raises:
            KeyError: if the key_id is not found.
            ValueError: if the stored value is malformed (e.g. wrong length).
        """
        ...  # pragma: no cover


class InMemoryKeyVault:
    """Simple in-memory vault backed by a dict.  Suitable for tests only."""

    def __init__(self, keys: Dict[str, bytes]) -> None:
        self._keys = dict(keys)

    def get_key(self, key_id: str) -> bytes:
        try:
            return self._keys[key_id]
        except KeyError:
            raise KeyError(f"Key '{key_id}' not found in InMemoryKeyVault.")


class EnvironmentKeyVault:
    """Read keys from environment variables.

    The key is expected to be **base64url-encoded** (no padding required) and
    must decode to exactly 32 bytes (256 bits) for AES-256.

    By default the vault looks up key_id ``"audit-v1"`` using the env var
    ``AUDIT_ENCRYPTION_KEY``.  Additional key IDs can be registered via
    ``register(key_id, env_var)`` to support key rotation.

    Args:
        default_env_var: Name of the environment variable for the default key.
        default_key_id:  The key ID served by *default_env_var*.
    """

    _AES256_KEY_BYTES = 32

    def __init__(
        self,
        default_env_var: str = "AUDIT_ENCRYPTION_KEY",
        default_key_id: str = "audit-v1",
    ) -> None:
        # key_id → env var name
        self._mapping: Dict[str, str] = {default_key_id: default_env_var}

    def register(self, key_id: str, env_var: str) -> None:
        """Map an additional *key_id* to an environment variable."""
        self._mapping[key_id] = env_var

    def get_key(self, key_id: str) -> bytes:
        env_var = self._mapping.get(key_id)
        if env_var is None:
            raise KeyError(
                f"Key '{key_id}' is not mapped to any environment variable in EnvironmentKeyVault."
            )
        raw = os.environ.get(env_var)
        if not raw:
            raise KeyError(
                f"Environment variable '{env_var}' is not set or empty. "
                f"Cannot retrieve key '{key_id}'."
            )
        try:
            key_bytes = base64.urlsafe_b64decode(raw + "==")  # pad to avoid truncation errors
        except Exception as exc:
            raise ValueError(
                f"Environment variable '{env_var}' is not valid base64url."
            ) from exc

        if len(key_bytes) != self._AES256_KEY_BYTES:
            raise ValueError(
                f"Key '{key_id}' decoded to {len(key_bytes)} bytes; expected {self._AES256_KEY_BYTES} (AES-256)."
            )
        return key_bytes
