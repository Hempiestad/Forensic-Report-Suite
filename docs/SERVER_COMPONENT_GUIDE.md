# Server Component Guide — FuDog Labs Forensic Report Suite

## Purpose

This guide documents the backend component of the FuDog Labs Forensic Report Suite, including architecture, runtime controls, and key API modules.

## Server Entry Path

The server starts from `server.py`, which loads the backend package under `Forensic Server/forensic_server` and runs `forensic_server.app.run()`.

Main flow:

1. `server.py` calls `forensic_server_loader.ensure_forensic_server_path()`.
2. `forensic_server.app.create_app()` builds the Flask application.
3. `forensic_server.app.run()` starts the HTTPS/HTTP listener.

## Component Map

### Core App Layer

- `Forensic Server/forensic_server/app.py`
  - Flask app creation.
  - Security middleware (JWT, CSRF, Talisman, limiter, CORS).
  - Blueprint registration.
  - Observability hooks and `/metrics` endpoint.

### API Blueprints

- `auth_bp.py`: authentication, token lifecycle.
- `cases_bp.py`: case CRUD and workflow operations.
- `dashboard_bp.py`: dashboard stats and filtering data.
- `reports_bp.py`: report-related server endpoints.
- `peer_review_bp.py`: peer review data flows.
- `discovery_bp.py`: discovery routes.
- `server_view_bp.py`: server-focused views/endpoints.
- `legal_template_library_bp.py`: legal template CRUD, scoped sharing, import/export.

### Data Layer

- `models.py`: SQLAlchemy models and table mappings.
- `schemas.py`: serialization/validation schema structures.

### Infrastructure Layer

- `infrastructure/api/decorators.py`: shared API decorators (including rate-limit helpers).
- `infrastructure/middleware.py`: request/response middleware registration.
- `infrastructure/observability.py`: structured logging, request IDs, metrics helpers.

## Runtime Security Controls

The app enables and validates these controls at startup:

- Required `JWT_SECRET` (minimum 32 chars).
- JWT access and refresh token expiry.
- CSRF protection (API blueprints explicitly exempted where bearer auth is used).
- Rate limiting defaults (`200/day`, `50/hour`).
- TLS settings via environment variables.
- Security headers and CSP with Flask-Talisman.
- Session cookie hardening (`Secure`, `HttpOnly`, `SameSite=Lax`).

## Environment Variables

Minimum recommended settings:

```env
JWT_SECRET=<32+ character secret>
DATABASE_URL=sqlite:///server.db
FLASK_ENV=production
FLASK_DEBUG=False
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
TLS_ENABLED=True
TLS_CERT_PATH=/path/to/cert.pem
TLS_KEY_PATH=/path/to/key.pem
RATE_LIMIT_ENABLED=true
```

Optional settings:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CORS_ORIGINS=http://localhost:5000,https://localhost:5000
METRICS_TOKEN=<token for /metrics>
```

## Legal Template Library Component

The legal template library supports reusable legal-process templates and controlled sharing.

Key capabilities:

- Vendor and template-type hierarchy.
- Template CRUD with owner/admin controls.
- Full library sharing.
- Scoped folder sharing (`vendor_name` and optional `template_type`).
- Import/export for portability.

Primary endpoint base:

- `/api/v1/legal-template-library`

## Database and Schema Behavior

- SQLAlchemy models are initialized in app startup.
- `db.create_all()` runs to ensure required tables exist.
- Local desktop schema evolution remains in `database.py` migrations for SQLite mode.

## Operational Checks

After startup, verify:

1. Auth endpoint responds:
   - `POST /api/v1/auth/login`
2. Case list endpoint reachable with token:
   - `GET /api/v1/cases`
3. Legal template endpoint reachable with token:
   - `GET /api/v1/legal-template-library/templates`
4. Metrics endpoint behavior:
   - `GET /metrics` (with token if configured)
5. Logs are being written:
   - `logs/server.log`

## Troubleshooting Quick Checks

- Startup failure with security error:
  - Validate `JWT_SECRET` length and presence.
- TLS not enabled in production:
  - Confirm `TLS_ENABLED=True` and cert/key paths exist.
- Unexpected 401/403:
  - Validate JWT claims, user role, and supervision assignments.
- Missing template visibility:
  - Check ownership, share scope, and `is_active` records.

## Related Documentation

- [README](README.md) — Project overview and quick start
- [Server User Guide](SERVER_USER_GUIDE.md) — API reference, roles, security features
- [Server Deployment Guide](SERVER_DEPLOYMENT_GUIDE.md) — Production deployment and checklists
- [Installation Guide](INSTALLATION_GUIDE.md) — Installation and initial configuration
- [Main Application User Guide](MAIN_USER_GUIDE.md) — Desktop client feature reference
