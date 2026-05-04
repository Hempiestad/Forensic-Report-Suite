from forensic_server_loader import ensure_forensic_server_path

ensure_forensic_server_path()

from forensic_server.server_view_bp import *  # noqa: F401,F403
