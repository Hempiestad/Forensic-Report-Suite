# FuDog Labs Forensic Report Suite

FuDog Labs Forensic Report Suite is a desktop-first digital forensics workflow platform with an optional secure Flask server for multi-user collaboration.

It is designed for investigators, examiners, supervisors, and admins who need structured case tracking, report authoring, legal process management, and auditable workflow history.

## Release Highlights

- Desktop case management with Notes and Reports authoring.
- Role-based access controls for investigator, examiner, supervisor, and admin workflows.
- Optional server mode with JWT auth, auditing, rate limiting, and TLS support.
- Legal template library with hierarchical organization:
  - Vendor root categories
  - Template-type folders
  - Multiple templates per folder
- Controlled template sharing:
  - Full library share
  - Scoped share (vendor or vendor + type folder)
- Template import/export for portability between investigators.

## Project Layout

- `main.py`: desktop application entrypoint.
- `database.py`: local SQLite and server-proxy data access layer.
- `server.py`: server bootstrap wrapper for the Flask backend.
- `Forensic Server/forensic_server`: server package with blueprints and models.
- `tests/integration`: integration coverage for API and local database behavior.

## Quick Start

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

Client mode:

```powershell
pip install -r requirements_client.txt
```

Client + server mode:

```powershell
pip install -r requirements_client.txt
pip install -r requirements_server.txt
```

### 3. Run desktop app

```powershell
python main.py
```

### 4. Run server (optional)

```powershell
python server.py
```

## Quality and Testing

Run targeted integration tests:

```powershell
python -m pytest tests/integration/test_legal_template_library_local_db.py tests/integration/test_legal_template_library_api.py -q
```

## Security Notes

- Set `JWT_SECRET` to a strong value of at least 32 characters before running server mode.
- Use TLS (`TLS_ENABLED=True`) for non-local deployments.
- Keep `.env`, databases, and case artifacts out of public repositories.



## License

Use under your organization policy and legal/compliance requirements.
