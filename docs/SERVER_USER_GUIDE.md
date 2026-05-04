# Server User Guide — FuDog Labs Forensic Report Suite

## Overview

The Server component is the central backend service for the FuDog Labs Forensic Report Suite. It provides a RESTful API for case management, user authentication, and secure data storage. The server is built with Flask and implements enterprise-grade security features including JWT authentication, role-based access control, TLS encryption, and comprehensive audit logging.

## Architecture

The server consists of:
- **Flask Application**: Main web framework
- **Blueprints**: Modular API endpoints (auth, cases, dashboard)
- **Database Layer**: SQLAlchemy ORM with connection pooling
- **Security Layer**: JWT tokens, CSRF protection, rate limiting
- **Caching Layer**: Redis-backed caching for performance
- **Logging System**: Rotating file logs with structured formatting

## Prerequisites

### System Requirements
- Python 3.8+
- SQLite (default) or PostgreSQL/MySQL
- Redis (optional, for caching)
- TLS certificates (for production HTTPS)

### Required Python Packages
```
Flask==2.3.3
Flask-JWT-Extended==4.5.2
Flask-SQLAlchemy==3.0.5
Flask-CORS==4.0.0
Flask-Limiter==3.5.0
Flask-Caching==2.1.0
Flask-Talisman==1.0.0
Flask-WTF==1.1.1
python-dotenv==1.0.0
ldap3==2.9.1
marshmallow==3.20.1
werkzeug==2.3.7
```

## Installation

1. **Clone or download the project files**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment variables** (see Configuration section)
4. **Initialize database** (automatic on first run)

## Configuration

### Environment Variables

Create a `.env` file in the server directory:

```bash
# Critical Security Settings
JWT_SECRET=your-32-character-or-longer-secret-key-here
DATABASE_URL=sqlite:///server.db

# Optional Database (PostgreSQL/MySQL)
# DATABASE_URL=postgresql://user:password@localhost/forensic_db
# DATABASE_URL=mysql://user:password@localhost/forensic_db

# Server Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SERVER_HOST=0.0.0.0
SERVER_PORT=5000

# TLS/HTTPS (Production)
TLS_ENABLED=True
TLS_CERT_PATH=/path/to/certificate.pem
TLS_KEY_PATH=/path/to/private.key

# Caching (Redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Active Directory (Optional)
AD_SERVER=dc.example.com
AD_DOMAIN=example.com
AD_BASE_DN=DC=example,DC=com
```

### Security Validation

The server validates critical security settings on startup:
- **JWT_SECRET**: Must be set and at least 32 characters
- **TLS**: Required in production mode
- **Database**: Connection tested on startup

## Running the Server

### Development Mode
```bash
export FLASK_DEBUG=True
export FLASK_ENV=development
python server.py
```

### Production Mode
```bash
export FLASK_ENV=production
export TLS_ENABLED=True
python server.py
```

### Docker Deployment
```bash
docker build -t forensic-server .
docker run -p 5000:5000 --env-file .env forensic-server
```

## API Endpoints

### Authentication Endpoints (`/api/v1/auth`)

#### POST `/api/v1/auth/login`
Authenticate user and return JWT tokens.

**Request Body:**
```json
{
  "username": "investigator1",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "user": {
    "username": "investigator1",
    "role": "investigator"
  }
}
```

#### POST `/api/v1/auth/refresh`
Refresh access token using refresh token.

#### POST `/api/v1/auth/logout`
Invalidate current session.

### Case Management Endpoints (`/api/v1/cases`)

#### GET `/api/v1/cases`
Retrieve all accessible cases (role-based filtering).

**Response:**
```json
[
  {
    "id": "CASE-2024-001",
    "assigned_to": "investigator1",
    "status": "draft",
    "trial_date": "2024-06-15",
    "sentencing_date": "2024-07-20",
    "evidence_details": [...],
    "legal_details": [...]
  }
]
```

#### POST `/api/v1/cases`
Create new case (Admin/Supervisor only).

**Request Body:**
```json
{
  "case_number": "CASE-2024-002",
  "assigned_to": "investigator2"
}
```

#### POST `/api/v1/cases/{case_number}/submit`
Submit case for review.

#### POST `/api/v1/cases/{case_number}/approve`
Approve submitted case (Admin/Supervisor only).

#### POST `/api/v1/cases/{case_number}/reject`
Reject case with comments (Admin/Supervisor only).

**Request Body:**
```json
{
  "comments": "Additional evidence required"
}
```

#### POST `/api/v1/cases/{case_number}/evidence`
Add evidence item to case.

**Request Body:**
```json
{
  "type": "digital",
  "details": "USB drive containing financial records",
  "imaging_status": "not_imaged"
}
```

#### POST `/api/v1/cases/{case_number}/legal`
Add legal process to case.

**Request Body:**
```json
{
  "type": "subpoena",
  "provider": "County Court",
  "status": "pending",
  "submission_date": "2024-01-15",
  "due_date": "2024-02-15"
}
```

#### PUT `/api/v1/cases/{case_number}/dates`
Update case trial/sentencing dates.

**Request Body:**
```json
{
  "trial_date": "2024-06-15",
  "sentencing_date": "2024-07-20"
}
```

### Dashboard Endpoints (`/api/v1/dashboard`)

#### GET `/api/v1/dashboard/stats`
Retrieve dashboard statistics and charts data.

**Response:**
```json
{
  "total_cases": 25,
  "cases_by_status": {
    "draft": 10,
    "submitted": 8,
    "approved": 7
  },
  "evidence_completion": {
    "completed": 15,
    "pending": 10
  }
}
```

### Legal Template Library Endpoints (`/api/v1/legal-template-library`)

#### GET `/api/v1/legal-template-library/templates`
List templates visible to the authenticated user (owned plus explicitly shared templates).

#### POST `/api/v1/legal-template-library/templates`
Create a new legal template.

```json
{
  "vendor_name": "Google",
  "template_type": "subpoena",
  "title": "Google Subpoena - Accounts",
  "template_content": "...",
  "tags": ["subscriber", "accounts"]
}
```

#### PUT `/api/v1/legal-template-library/templates/{id}`
Update a template (owner or admin).

#### POST `/api/v1/legal-template-library/libraries/share`
Share an owner's entire library with another user.

#### POST `/api/v1/legal-template-library/libraries/share-scoped`
Share limited scope by vendor or vendor + type folder.

```json
{
  "shared_with": "investigator_b",
  "vendor_name": "Google",
  "template_type": "subpoena"
}
```

If `template_type` is omitted, all templates under the vendor are shared.

#### GET `/api/v1/legal-template-library/export`
Export the owner's templates as portable JSON.

#### POST `/api/v1/legal-template-library/import`
Import templates from JSON using append or replace mode.

## User Roles and Permissions

### Role Hierarchy
- **Admin**: Full system access, user management
- **Supervisor**: Case creation, approval, evidence/legal management
- **Investigator**: Case assignment, evidence tracking, legal processes
- **Examiner**: Case viewing, report generation

### Permission Matrix

| Operation | Admin | Supervisor | Investigator | Examiner |
|-----------|-------|------------|--------------|----------|
| View Cases | ✓ | ✓ | Assigned | Assigned |
| Create Cases | ✓ | ✓ | ✗ | ✗ |
| Edit Cases | ✓ | ✓ | Assigned | ✗ |
| Approve Cases | ✓ | ✓ | ✗ | ✗ |
| Add Evidence | ✓ | ✓ | ✓ | ✗ |
| Add Legal | ✓ | ✓ | ✓ | ✗ |

## Security Features

### Authentication
- **JWT Tokens**: Stateless authentication with access/refresh tokens
- **Token Expiration**: Access tokens expire in 12 hours, refresh in 7 days
- **Active Directory**: Optional LDAP integration for enterprise auth

### Authorization
- **Role-Based Access Control**: API endpoints protected by user roles
- **CSRF Protection**: Cross-site request forgery prevention
- **Rate Limiting**: 200 requests/day, 50/hour per IP

### Data Protection
- **TLS Encryption**: HTTPS required in production
- **HSTS**: HTTP Strict Transport Security (1 year)
- **Content Security Policy**: XSS protection
- **Secure Headers**: Comprehensive security headers via Talisman

### Audit Logging
- **Request Logging**: All API requests logged with timestamps
- **Error Logging**: Application errors with stack traces
- **Security Events**: Authentication failures, unauthorized access
- **Log Rotation**: 10MB files, 10 backup files

### Template Sharing Guardrails
- Owners can update/delete only their templates (except admin override).
- Scoped sharing can be constrained by supervisor assignments.
- Share/import/export actions are audit logged.

## Database Schema

### Cases Table
```sql
CREATE TABLE cases (
    case_number VARCHAR(50) PRIMARY KEY,
    assigned_to VARCHAR(100),
    status VARCHAR(50) DEFAULT 'draft',
    trial_date VARCHAR(20),
    sentencing_date VARCHAR(20),
    review_comments TEXT,
    examiner_id VARCHAR(100),
    title VARCHAR(200),
    peer_reviewers TEXT
);
```

### Evidence Items Table
```sql
CREATE TABLE evidence_items (
    id INTEGER PRIMARY KEY,
    case_number VARCHAR(50) REFERENCES cases(case_number),
    item_type VARCHAR(50),
    details TEXT,
    imaging_status VARCHAR(50) DEFAULT 'not_imaged',
    imaged_date DATETIME,
    completed_date DATETIME
);
```

### Legal Processes Table
```sql
CREATE TABLE legal_processes (
    id INTEGER PRIMARY KEY,
    case_number VARCHAR(50) REFERENCES cases(case_number),
    process_type VARCHAR(50),
    provider VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    submission_date DATETIME,
    due_date DATETIME,
    expiration_date DATETIME,
    received_date DATETIME,
    analysis_start_date DATETIME,
    completed_date DATETIME
);
```

## Monitoring and Maintenance

### Health Checks
- **Database Connectivity**: Tested on startup
- **Cache Status**: Redis connection monitoring
- **Memory Usage**: Flask application monitoring

### Log Analysis
- **Access Logs**: API usage patterns
- **Error Logs**: Application issues and stack traces
- **Security Logs**: Authentication and authorization events

### Performance Optimization
- **Connection Pooling**: Database connections reused
- **Caching**: API responses cached for 45 seconds
- **Indexing**: Database indexes on frequently queried columns

## Troubleshooting

### Common Issues

**Server Won't Start**
- Check JWT_SECRET environment variable
- Verify database URL and connectivity
- Ensure required ports are available

**Authentication Fails**
- Verify JWT_SECRET matches between client/server
- Check token expiration times
- Validate user credentials and roles

**Database Connection Errors**
- Test database connectivity: `python -c "from models import db; db.create_all()"`
- Check connection string format
- Verify database server is running

**TLS/HTTPS Issues**
- Ensure certificate files exist and are readable
- Verify certificate validity and chain
- Check firewall settings for port 443

**Performance Problems**
- Monitor database query performance
- Check Redis cache hit rates
- Review rate limiting logs

### Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| 400 | Bad Request | Check request format and required fields |
| 401 | Unauthorized | Verify authentication token |
| 403 | Forbidden | Check user permissions and roles |
| 404 | Not Found | Verify endpoint URL and resource existence |
| 429 | Too Many Requests | Wait for rate limit reset |
| 500 | Internal Error | Check server logs for details |

### Log Locations
- **Application Logs**: `logs/server.log`
- **Error Logs**: Included in main log file
- **Startup Logs**: Console output during server launch

## Backup and Recovery

### Database Backup
```bash
# SQLite
cp server.db server.db.backup

# PostgreSQL
pg_dump forensic_db > backup.sql

# MySQL
mysqldump forensic_db > backup.sql
```

### Configuration Backup
```bash
cp .env .env.backup
cp config.json config.json.backup
```

### Log Archival
```bash
tar -czf logs_$(date +%Y%m%d).tar.gz logs/
```

## Integration with Client Applications

### API Client Setup
```python
import requests

BASE_URL = "https://your-server.com/api/v1"
headers = {"Authorization": f"Bearer {access_token}"}

# Example: Get cases
response = requests.get(f"{BASE_URL}/cases", headers=headers)
cases = response.json()
```

### WebSocket Support (Future)
- Real-time case updates
- Live dashboard refresh
- Notification system

## Development and Testing

### Running Tests
```bash
python -m pytest tests/
```

### API Documentation
- **Swagger/OpenAPI**: Available at `/api/docs` (if configured)
- **Postman Collection**: Import `api_collection.json`
- **Server Component Guide**: [SERVER_COMPONENT_GUIDE.md](SERVER_COMPONENT_GUIDE.md)
- **Server Deployment Guide**: [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md)

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## Related Documentation

- [README](README.md) — Project overview and quick start
- [Installation Guide](INSTALLATION_GUIDE.md) — Installation and environment setup
- [Main Application User Guide](MAIN_USER_GUIDE.md) — Desktop client feature reference
- [Server Component Guide](SERVER_COMPONENT_GUIDE.md) — Architecture, blueprints, and runtime controls
- [Server Deployment Guide](SERVER_DEPLOYMENT_GUIDE.md) — Production deployment and operations
- [Legal Workflow Guide](LEGAL_WORKFLOW_GUIDE.md) — Legal process approval workflow

