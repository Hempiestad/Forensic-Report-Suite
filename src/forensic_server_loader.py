from pathlib import Path
import sys


def ensure_forensic_server_path() -> None:
    # This file lives in src/; go up one level to reach the project root
    server_root = Path(__file__).resolve().parent.parent / 'Forensic Server'
    server_root_str = str(server_root)
    if server_root_str not in sys.path:
        sys.path.insert(0, server_root_str)
