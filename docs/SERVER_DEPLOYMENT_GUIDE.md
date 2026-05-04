# Server Deployment Guide — FuDog Labs Forensic Report Suite

## Scope

This guide focuses on deploying the FuDog Labs Forensic Report Suite backend server in development and production environments.

## Deployment Modes

- **Local development**: single-node, local SQLite, optional HTTP.
- **Team staging**: single-node with TLS, production-like settings.
- **Production**: hardened TLS endpoint, monitored logs, backup strategy, optional external DB/Redis.

## Prepare Host

Minimum recommendations:

- Python 3.8+
- 4 CPU cores, 8 GB RAM (higher for concurrent users)
- Persistent storage for database and logs
- Access to TLS certificates

## Install Dependencies

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install -r requirements_server.txt
```

If you also run the desktop client on the same machine:

```bash
pip install -r requirements_client.txt
```

## Configure Environment

Create `.env` in project root:

```env
JWT_SECRET=<32+ character random secret>
DATABASE_URL=sqlite:///server.db
FLASK_ENV=production
FLASK_DEBUG=False
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
TLS_ENABLED=True
TLS_CERT_PATH=/secure/path/fullchain.pem
TLS_KEY_PATH=/secure/path/privkey.pem
RATE_LIMIT_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

Generate secret example:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Launch Server

```bash
python server.py
```

Expected behavior:

- Security checks pass (`JWT_SECRET`, TLS settings).
- Database tables are created if missing.
- Logs are written to `logs/server.log`.

## Smoke Tests

1. Confirm process is listening on configured host/port.
2. Authenticate against `POST /api/v1/auth/login`.
3. Access protected endpoint with token.
4. Validate legal template library endpoint:
   - `GET /api/v1/legal-template-library/templates`

## Production Hardening Checklist

- Run with non-admin service account.
- Restrict inbound ports to required clients.
- Force TLS for all remote access.
- Rotate secrets and TLS certificates on schedule.
- Enable central log collection.
- Protect backups with encryption and retention policy.
- Validate rate limiting and alert on anomalies.

## Data and Backup Strategy

SQLite baseline:

- Backup `server.db` regularly.
- Backup `.env` securely.
- Backup `logs/` for incident investigations.

PostgreSQL/MySQL option:

- Use scheduled dumps.
- Test restore workflow quarterly.
- Keep at least one off-host backup copy.

## Deployment Patterns

### Reverse Proxy Pattern

Recommended for production:

- Flask server bound to internal interface.
- Reverse proxy (Nginx/Apache) handles TLS termination and request buffering.
- Proxy passes request ID headers for traceability.

### Container Pattern

Use `docker-compose.yml` as baseline for repeatable deployments:

- Pin image versions.
- Mount persistent volumes for DB/logs.
- Inject `.env` through secure secret mechanism.

## Common Failure Modes

- `JWT_SECRET` missing/short:
  - Server exits at startup.
- TLS cert path invalid:
  - Server may start without TLS context; fix paths before production use.
- 401 on protected APIs:
  - Access token missing/expired/invalid.
- 403 on template sharing:
  - Role or supervision scope does not permit operation.

## Release Deployment Checklist

- Pull tagged release.
- Run integration tests:
  - `python -m pytest tests/integration/test_legal_template_library_local_db.py tests/integration/test_legal_template_library_api.py -q`
- Verify schema compatibility and migration notes.
- Deploy to staging and run smoke tests.
- Deploy production with rollback plan.
- Capture deployment record and config hash.

## Related Documentation

- [README](README.md) — Project overview and quick start
- [Server Component Guide](SERVER_COMPONENT_GUIDE.md) — Architecture, blueprints, and runtime controls
- [Server User Guide](SERVER_USER_GUIDE.md) — API reference and security features
- [Installation Guide](INSTALLATION_GUIDE.md) — Initial installation and configuration
