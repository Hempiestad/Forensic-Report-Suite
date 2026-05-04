# security.py - now minimal wrapper
from secure_key_manager import encrypt_data, decrypt_data
from hashlib import sha256
from collections import OrderedDict
import os

# Size-limited LRU cache for PDF hashes (max 256 entries) to avoid unbounded memory growth
_PDF_HASH_CACHE_MAX = 256
_pdf_hash_cache: OrderedDict[str, str] = OrderedDict()


def _cache_put(path: str, digest: str) -> None:
    """Insert a hash result, evicting the oldest entry if at capacity."""
    if path in _pdf_hash_cache:
        _pdf_hash_cache.move_to_end(path)
    else:
        if len(_pdf_hash_cache) >= _PDF_HASH_CACHE_MAX:
            _pdf_hash_cache.popitem(last=False)
        _pdf_hash_cache[path] = digest

def compute_sha256(file_path: str, progress_callback=None) -> str:
    """
    Compute SHA-256 hash of a file, streaming chunks to avoid memory issues.
    Supports optional progress callback for large files.

    Args:
        file_path: Path to the file to hash
        progress_callback: Optional callback function that takes (bytes_processed, total_bytes)

    Returns:
        Hexadecimal string of the SHA-256 hash
    """
    # Check cache first
    if file_path in _pdf_hash_cache:
        return _pdf_hash_cache[file_path]

    h = sha256()
    total_bytes = os.path.getsize(file_path)
    bytes_processed = 0

    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
            bytes_processed += len(block)
            if progress_callback:
                progress_callback(bytes_processed, total_bytes)

    hash_result = h.hexdigest()

    # Cache the result for future use
    _cache_put(file_path, hash_result)

    return hash_result

def clear_pdf_hash_cache():
    """Clear the PDF hash cache"""
    global _pdf_hash_cache
    _pdf_hash_cache.clear()
