# Server Architecture Hierarchy

> Consolidation note (May 2026): This hierarchy view is retained as a supplemental map.
> Canonical server architecture/component reference: [SERVER_COMPONENT_GUIDE.md](SERVER_COMPONENT_GUIDE.md).
> Canonical deployment/runbook reference: [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md).

## 📁 Server Architecture Hierarchy

```
server.py (Main Flask Application)
├── 🔧 Core Framework & Extensions
│   ├── Flask (Web Framework)
│   ├── Flask-SQLAlchemy (ORM)
│   ├── Flask-JWT-Extended (Authentication)
│   ├── Flask-CORS (Cross-Origin Resource Sharing)
│   └── Flask-Limiter (Rate Limiting)
│
├── 📦 Custom Modules (Blueprints)
│   ├── auth_bp.py (Authentication Blueprint)
│   │   ├── /api/v1/auth/login (POST)
│   │   └── /api/v1/auth/refresh (POST)
│   │
│   ├── cases_bp.py (Case Management Blueprint)
│   │   ├── /api/v1/cases (GET, POST)
│   │   ├── /api/v1/cases/<id>/submit (POST)
│   │   ├── /api/v1/cases/<id>/approve (POST)
│   │   ├── /api/v1/cases/<id>/reject (POST)
│   │   ├── /api/v1/cases/<id>/evidence (POST)
│   │   └── /api/v1/cases/<id>/legal (POST)
│   │
│   └── dashboard_bp.py (Dashboard Blueprint)
│       └── /api/v1/dashboard (GET)
│
├── 🗄️ Data Layer
│   └── models.py (SQLAlchemy Models)
│       ├── Case (Main case entity)
│       ├── EvidenceItem (Evidence tracking)
│       └── LegalProcess (Legal process tracking)
│
├── ⚙️ Configuration & Utilities
│   ├── .env (Environment Variables)
│   ├── schemas.py (Marshmallow Validation)
│   └── logs/ (Rotating Log Files)
```

## 🔍 Detailed Module Breakdown

### 1. Core Application (`server.py`)
```
server.py
├── Imports & Dependencies
│   ├── Flask ecosystem imports
│   ├── Blueprint imports (auth_bp, cases_bp, dashboard_bp)
│   └── Utility imports (logging, dotenv)
│
├── Configuration Setup
│   ├── Environment variable loading
│   ├── Flask app configuration
│   └── Extension initialization
│
├── Application Components
│   ├── Blueprint registration
│   ├── Database table creation
│   ├── Error handlers (400, 401, 403, 404, 500)
│   └── Logging setup
│
└── Server Launch
    └── Flask development server startup
```

### 2. Authentication Blueprint (`auth_bp.py`)
```
auth_bp.py
├── Dependencies
│   ├── Flask Blueprint
│   ├── JWT functions
│   ├── LDAP3 (for AD integration)
│   └── Environment config
│
├── Endpoints
│   ├── POST /api/v1/auth/login
│   │   ├── Username/password validation
│   │   ├── AD or local authentication
│   │   └── JWT token generation
│   │
│   └── POST /api/v1/auth/refresh
│       ├── Refresh token validation
│       └── New access token generation
│
└── Helper Functions
    └── determine_role_from_groups() - AD group to role mapping
```

### 3. Cases Blueprint (`cases_bp.py`)
```
cases_bp.py
├── Dependencies
│   ├── Flask Blueprint & JWT
│   ├── SQLAlchemy models
│   └── Validation schemas
│
├── Case Management Endpoints
│   ├── GET /api/v1/cases - List cases (RBAC filtered)
│   ├── POST /api/v1/cases - Create new case
│   ├── POST /api/v1/cases/<id>/submit - Submit for review
│   ├── POST /api/v1/cases/<id>/approve - Approve case
│   ├── POST /api/v1/cases/<id>/reject - Reject with comments
│   ├── POST /api/v1/cases/<id>/evidence - Add evidence item
│   └── POST /api/v1/cases/<id>/legal - Add legal process
│
└── Helper Functions
    ├── get_evidence_details()
    └── get_legal_details()
```

### 4. Dashboard Blueprint (`dashboard_bp.py`)
```
dashboard_bp.py
├── Dependencies
│   ├── Flask Blueprint & JWT
│   └── SQLAlchemy models
│
└── Endpoints
    └── GET /api/v1/dashboard - Supervisor dashboard data
```

### 5. Data Models (`models.py`)
```
models.py
├── SQLAlchemy Base Setup
├── Case Model
│   ├── case_number (Primary Key)
│   ├── assigned_to, status, review_comments
│   └── metadata_json, report_html, appendices
│
├── EvidenceItem Model
│   ├── id, case_number (Foreign Key)
│   ├── item_type, details, imaging_status
│   └── Various evidence metadata fields
│
└── LegalProcess Model
    ├── id, case_number (Foreign Key)
    ├── process_type, provider, status
    └── Dates and legal tracking fields
```

### 6. Validation Schemas (`schemas.py`)
```
schemas.py
├── Marshmallow Schema Definitions
├── LoginSchema - Authentication validation
├── CaseCreateSchema - Case creation validation
├── EvidenceCreateSchema - Evidence item validation
└── LegalProcessCreateSchema - Legal process validation
```

## 🔗 Module Dependencies

- **`server.py`** → Depends on all blueprints and models
- **`auth_bp.py`** → Independent (uses environment config)
- **`cases_bp.py`** → Depends on models and schemas
- **`dashboard_bp.py`** → Depends on models
- **`models.py`** → Independent (SQLAlchemy models)
- **`schemas.py`** → Independent (validation schemas)

## 🚀 Startup Flow

1. `server.py` loads environment variables
2. Initializes Flask app and extensions
3. Imports and registers blueprints
4. Creates database tables if needed
5. Sets up error handlers and logging
6. Starts Flask development server

## 📋 API Endpoints Summary

### Authentication (`/api/v1/auth`)
- `POST /login` - User authentication
- `POST /refresh` - Token refresh

### Cases (`/api/v1/cases`)
- `GET /` - List cases (RBAC filtered)
- `POST /` - Create new case
- `POST /<id>/submit` - Submit case for review
- `POST /<id>/approve` - Approve case
- `POST /<id>/reject` - Reject case with comments
- `POST /<id>/evidence` - Add evidence item
- `POST /<id>/legal` - Add legal process

### Dashboard (`/api/v1/dashboard`)
- `GET /` - Get dashboard data (supervisor/admin only)

This modular architecture allows for independent development, testing, and deployment of each component while maintaining clean separation of concerns.
