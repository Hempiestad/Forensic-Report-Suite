import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from forensic_server_loader import ensure_forensic_server_path

ensure_forensic_server_path()

from forensic_server.app import app, create_app, run


if __name__ == '__main__':
    run()
