# FuDog Labs Forensic Report Suite

FuDog Labs Forensic Report Suite is a desktop-first digital forensics workflow platform with an optional secure Flask server for multi-user collaboration.

It is designed for investigators, examiners, supervisors, and admins who need structured case tracking, report authoring, legal process management, and auditable workflow history.

This project is still an Alpha version and is still a work in progress, especially the server componets are actively being worked on. Please provide feedback and report bugs.

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

## Features and Functions

### Who This Is For

- Investigators who need structured case tracking, legal-process visibility, and timeline control.
- Examiners who need evidence status management and efficient report drafting workflows.
- Supervisors who need approval controls, audit visibility, and operational oversight.
- Admins and technical leads who need secure deployment options and role-based governance.

### Feature Matrix

| Capability Area | Core Functions | Primary Roles |
|---|---|---|
| Case Management | Create/track/close cases, dashboard filtering, archive/restore | Investigator, Supervisor |
| Evidence Tracking | Evidence metadata, imaging status, investigative lead tracking | Investigator, Examiner |
| Legal Workflow | Multi-stage approvals, SLA tracking, provider handoff tracking | Investigator, Supervisor |
| Notes and Reports | Rich-text authoring, template-assisted drafting, exports | Examiner, Investigator |
| Collaboration and Security | JWT auth, RBAC, audit logging, TLS-ready server mode | Admin, Supervisor |
| Deployment Modes | Desktop-first local mode, optional centralized Flask server | Admin, Technical Lead |

### Case and Workflow Management

- Case lifecycle tracking from draft through review and close-out.
- Role-aware workflows for investigator, examiner, supervisor, and admin users.
- Dashboard views with filters and status-focused operational visibility.
- Archived case handling to declutter active work while preserving recoverability.

### Evidence and Investigation Tracking

- Structured evidence item records with forensic metadata fields.
- Imaging and processing status tracking for evidence progression.
- Legal process tracking for subpoenas, warrants, and related actions.
- Lead and milestone tracking to support investigative timeline management.

### Legal Process and Approval Workflow

- Multi-stage legal approval flow (investigator, attorney, judicial, provider).
- SLA-aware process monitoring from provider submission to response completion.
- Calendar-aligned workflow events and notification hooks.
- Legal template library with hierarchical organization and share controls.

### Report and Notes Authoring

- Rich-text reporting workspace for forensic report creation.
- Dedicated notes workspace for case-centric operational notes.
- Template-assisted drafting to standardize legal and investigative output.
- Export capabilities for common distribution formats.

### Collaboration, Security, and Auditability

- Optional server mode for centralized multi-user collaboration.
- JWT-based authentication and role-based access enforcement.
- Auditable action logging for sensitive workflow operations.
- Security-oriented deployment controls including TLS-ready configuration.

### Platform and Deployment Flexibility

- Desktop-first local operation with SQLite-backed data handling.
- Optional Flask server for API-driven and centralized workflows.
- Environment-driven configuration for deployment portability.
- Development and integration test coverage for core workflows.

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

## Documentation Index

- [Installation Guide](docs/INSTALLATION_GUIDE.md)
- [Main User Guide](docs/MAIN_USER_GUIDE.md)
- [Notes User Guide](docs/NOTES_USER_GUIDE.md)
- [Reports User Guide](docs/REPORTS_USER_GUIDE.md)
- [Server User Guide](docs/SERVER_USER_GUIDE.md)
- [Server Component Guide](docs/SERVER_COMPONENT_GUIDE.md)
- [Server Deployment Guide](docs/SERVER_DEPLOYMENT_GUIDE.md)
- [Legal Workflow Guide](docs/LEGAL_WORKFLOW_GUIDE.md)
- [Legal Workflow UI Guide](docs/LEGAL_WORKFLOW_UI_GUIDE.md)

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

GPL-3.0 License. Use under your organization's policy and legal/compliance requirements.
