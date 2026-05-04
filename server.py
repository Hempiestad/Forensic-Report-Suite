from forensic_server_loader import ensure_forensic_server_path

ensure_forensic_server_path()

from forensic_server.app import app, create_app, run


if __name__ == '__main__':
    run()
