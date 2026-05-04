# PostgreSQL DSN Configuration Guide

**Version:** 1.0  
**Date:** April 23, 2026  
**Purpose:** Configure PostgreSQL for Forensic Report Writer in different environments

---

## Quick Start

### Local Development
```bash
# 1. Create PostgreSQL database
createdb forensic_dev
createuser forensic_user --password
# Enter password when prompted

# 2. Set environment variable
export FORENSIC_PG_DSN="postgresql://forensic_user:password@localhost:5432/forensic_dev"

# 3. Run tests (postgres tests will now execute instead of skip)
pytest tests/integration/ -v
```

---

## Environment-Specific Configuration

### Development Environment

**DSN Pattern:**
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Example:**
```bash
export FORENSIC_PG_DSN="postgresql://forensic_user:mypassword@localhost:5432/forensic_dev"
```

**Settings:**
- Connection timeout: 30 seconds
- Idle timeout: 5 minutes
- Pool size: 5-10 connections
- SSL mode: prefer (auto-upgrade if available)

---

### Testing Environment (CI/CD)

**GitHub Actions Example:**
```yaml
name: Integration Tests with PostgreSQL

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: forensic_test
          POSTGRES_USER: ci_user
          POSTGRES_PASSWORD: ci_pass_temporary
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run integration tests with PostgreSQL
        env:
          FORENSIC_PG_DSN: "postgresql://ci_user:ci_pass_temporary@localhost:5432/forensic_test"
        run: |
          pytest tests/integration/test_postgres_*.py -v
```

**GitLab CI Example:**
```yaml
test:postgres:
  image: python:3.9
  
  services:
    - postgres:15-alpine
  
  variables:
    POSTGRES_DB: forensic_test
    POSTGRES_USER: ci_user
    POSTGRES_PASSWORD: ci_pass_temporary
    FORENSIC_PG_DSN: "postgresql://ci_user:ci_pass_temporary@postgres:5432/forensic_test"
  
  script:
    - pip install -r requirements.txt
    - pytest tests/integration/test_postgres_*.py -v
```

---

### Production Environment

**Cloud Provider Options:**

#### AWS RDS
```bash
# Use AWS Secrets Manager or Parameter Store
export FORENSIC_PG_DSN="postgresql://admin:$(aws secretsmanager get-secret-value --secret-id forensic/pg-password --query SecretString --output text)@forensic-db.xxxxx.us-east-1.rds.amazonaws.com:5432/forensic_prod"

# Or directly with IAM auth (recommended)
export FORENSIC_PG_DSN="postgresql://admin@forensic-db.xxxxx.us-east-1.rds.amazonaws.com:5432/forensic_prod?sslmode=require"
```

#### Azure Database for PostgreSQL
```bash
export FORENSIC_PG_DSN="postgresql://forensic_admin@forensic-server:password@forensic-server.postgres.database.azure.com:5432/forensic_prod?sslmode=require"
```

#### Google Cloud SQL
```bash
export FORENSIC_PG_DSN="postgresql://cloudsql_user:password@:/cloudsql/project:region:instance/forensic_prod"
```

#### Self-Hosted PostgreSQL
```bash
export FORENSIC_PG_DSN="postgresql://admin:password@db.example.com:5432/forensic_prod"
```

**Production Settings:**
- Connection timeout: 60 seconds
- Idle timeout: 30 minutes
- Pool size: 50-200 connections (via pgbouncer)
- SSL mode: require
- Application name: forensic_report_writer

**Connection String with Full Parameters:**
```bash
export FORENSIC_PG_DSN="postgresql://user:password@host:5432/forensic_prod?sslmode=require&connect_timeout=60&application_name=forensic_writer&options=-c%20statement_timeout=300000"
```

---

## Connection String Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `sslmode` | disable, allow, prefer, require | SSL connection mode (require for production) |
| `connect_timeout` | seconds | Connection timeout |
| `application_name` | string | App identifier in PostgreSQL logs |
| `statement_timeout` | milliseconds | Query timeout (e.g., 300000 = 5 minutes) |
| `pool_size` | 1-100 | Connection pool size |
| `max_overflow` | 1-50 | Max overflow beyond pool size |

---

## Troubleshooting

### Connection Refused
```bash
# Check PostgreSQL is running
psql -h localhost -U forensic_user -d forensic_dev -c "SELECT 1;"
```

### Authentication Failed
```bash
# Verify credentials
# In psql:
\du  -- list users
\l   -- list databases
```

### Slow Connections
```bash
# Check connection string for SSL issues
# Reduce connection_timeout if network is unstable
export FORENSIC_PG_DSN="postgresql://user:pass@host:5432/db?sslmode=prefer&connect_timeout=10"
```

### Port Already in Use
```bash
# On macOS/Linux
lsof -i :5432
kill -9 <PID>
```

---

## Testing the Connection

### Using Python
```python
import os
import psycopg

dsn = os.getenv("FORENSIC_PG_DSN")
try:
    conn = psycopg.connect(dsn)
    print(f"✅ Connected to PostgreSQL")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### Using psql CLI
```bash
psql $FORENSIC_PG_DSN -c "SELECT version();"
```

### Run Integration Tests
```bash
# All postgres tests
pytest tests/integration/test_postgres_*.py -v

# Specific test
pytest tests/integration/test_postgres_service_continuity.py::test_postgres_report_audit_chain -v
```

---

## Best Practices

1. **Never commit credentials** — Use environment variables or secrets manager
2. **Use SSL in production** — Always set `sslmode=require`
3. **Connection pooling** — Use pgbouncer or application-level pooling
4. **Monitoring** — Track connection count, query latency, replication lag
5. **Backups** — Configure automated backups (see PHASE3_2_ENTERPRISE_FEATURES.md)
6. **Testing** — Run CI tests with PostgreSQL enabled to catch provider-specific bugs

---

## DSN Validation Checklist

- [ ] DSN environment variable is set: `echo $FORENSIC_PG_DSN`
- [ ] PostgreSQL server is running and reachable via `psql`
- [ ] Database exists: `psql -l | grep forensic`
- [ ] User has permissions: `psql -U forensic_user -d forensic_dev -c "SELECT 1;"`
- [ ] Connection works: `python -c "import psycopg; psycopg.connect('$FORENSIC_PG_DSN')"`
- [ ] Pytest discovers tests: `pytest tests/integration/test_postgres_*.py --collect-only`
- [ ] Tests execute: `pytest tests/integration/test_postgres_*.py -v`

