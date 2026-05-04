"""Storage backend abstractions for backup artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import List, Protocol, runtime_checkable


@runtime_checkable
class IStorageBackend(Protocol):
    """Minimal storage backend contract used by backup/restore services."""

    def write_bytes(self, key: str, content: bytes) -> None:
        ...  # pragma: no cover

    def read_bytes(self, key: str) -> bytes:
        ...  # pragma: no cover

    def exists(self, key: str) -> bool:
        ...  # pragma: no cover

    def list_keys(self, prefix: str = "") -> List[str]:
        ...  # pragma: no cover


class LocalFilesystemStorage:
    """Local filesystem storage backend.

    Keys are relative paths under ``root_dir``.  Parent directories are created
    automatically when writing.
    """

    def __init__(self, root_dir: str) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, key: str, content: bytes) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def read_bytes(self, key: str) -> bytes:
        path = self._resolve(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def list_keys(self, prefix: str = "") -> List[str]:
        prefix_path = self._resolve(prefix) if prefix else self._root
        if not prefix_path.exists():
            return []

        paths = [
            p.relative_to(self._root).as_posix()
            for p in prefix_path.rglob("*")
            if p.is_file()
        ]
        return sorted(paths)

    def _resolve(self, key: str) -> Path:
        # Prevent path traversal by resolving against root and validating prefix.
        candidate = (self._root / key).resolve()
        root_resolved = self._root.resolve()
        if not str(candidate).startswith(str(root_resolved)):
            raise ValueError(f"Invalid key path outside storage root: {key}")
        return candidate
