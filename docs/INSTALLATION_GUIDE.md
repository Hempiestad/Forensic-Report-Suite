# Installation Guide — FuDog Labs Forensic Report Suite

## Overview

The FuDog Labs Forensic Report Suite consists of two main components:

- **Client Application**: Desktop GUI application for case management and report generation
- **Server Application**: Optional backend service for multi-user collaboration and centralized data storage

This guide covers installation of both components and configuration for client-server connectivity.

## Prerequisites

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+ or equivalent Linux
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 500MB free space for installation + case data

### Required Software
- Python 3.8+ (download from python.org)
- Git (optional, for cloning repository)
- Text editor (VS Code recommended)

## Install Profiles

- **Client-only profile**: Desktop app with local SQLite storage.
- **Client + Server profile**: Desktop app plus centralized API backend for multi-user operations.

Use the split requirements files for faster, cleaner installs:

- `requirements_client.txt`
- `requirements_server.txt`

## Client Application Installation

### Step 1: Install Python Dependencies

1. **Download or clone the project**:
   ```bash
   git clone https://github.com/your-org/forensic-report-writer.git
   cd forensic-report-writer
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install client packages**:
   ```bash
   pip install -r requirements_client.txt
   ```

   **Platform-specific notes**:
   - **Windows**: May need Visual C++ Build Tools for some packages
   - **Linux**: Install system dependencies:
     ```bash
     sudo apt update
     sudo apt install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 python3-dev
     ```
   - **macOS**: Install Homebrew dependencies:
     ```bash
     brew install cairo pango
     ```

### Step 2: Initial Configuration

1. **Copy configuration template**:
   ```bash
   cp config.json config.json.backup  # Backup original
   ```

2. **Edit config.json** for your environment:
   ```json
   {
     "use_ad": false,
     "server_url": "",
     "theme": "dark",
     "timezone": "local"
   }
   ```

### Step 3: Run the Application

```bash
python main.py
```

The application should launch with the main dashboard window.

## Server Application Installation

### Step 1: Install Server Dependencies

The server requires additional packages beyond the client dependencies:

```bash
pip install -r requirements_server.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Critical Security Settings
JWT_SECRET=your-super-secure-32-character-or-longer-secret-key-here-change-this-in-production

# Database Configuration (SQLite default)
DATABASE_URL=sqlite:///server.db

# Server Settings
FLASK_ENV=production
FLASK_DEBUG=False
SERVER_HOST=0.0.0.0
SERVER_PORT=5000

# TLS/HTTPS (Required for production)
TLS_ENABLED=True
TLS_CERT_PATH=/path/to/your/certificate.pem
TLS_KEY_PATH=/path/to/your/private.key

# Optional: Redis for caching
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

**Security Note**: Generate a strong JWT_SECRET:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 3: Database Setup

For SQLite (default):
- Database is created automatically on first run

For PostgreSQL/MySQL:
1. Create database:
   ```sql
   CREATE DATABASE forensic_reports;
   ```

2. Update DATABASE_URL in .env:
   ```bash
   DATABASE_URL=postgresql://username:password@localhost/forensic_reports
   # or
   DATABASE_URL=mysql://username:password@localhost/forensic_reports
   ```

### Step 4: Start the Server

```bash
python server.py
```

The server will start and display:
```
Secure Forensic Case Management Server starting...
Database: sqlite:///server.db
Running in PRODUCTION mode (debug disabled)
Using TLS certificates from: /path/to/certificate.pem
```

## Client-Server Connection Setup

### Option 1: Standalone Mode (Default)

The client runs independently without a server:
- All data stored locally in SQLite database
- No user authentication required
- Suitable for single-user operation

**Configuration**:
```json
{
  "server_url": "",
  "use_ad": false
}
```

### Option 2: Server Mode (Multi-User)

Connect client to server for collaborative features:

#### Server Configuration

1. **Ensure server is running** on accessible host/port
2. **Note the server URL**: `https://your-server.com:5000` (or `http://localhost:5000` for local)

#### Client Configuration

1. **Edit config.json**:
   ```json
   {
     "server_url": "https://your-server.com:5000",
     "use_ad": false
   }
   ```

2. **Restart the client application**

#### Authentication Setup

The server supports multiple authentication methods:

**Local Authentication** (Default):
- Users created automatically on first login
- No additional setup required

**Active Directory Integration**:
1. Configure AD settings in server .env:
   ```bash
   AD_SERVER=dc.company.com
   AD_DOMAIN=company.com
   AD_BASE_DN=DC=company,DC=com
   ```

2. Update client config.json:
   ```json
   {
     "use_ad": true,
     "ad_server": "dc.company.com",
     "ad_domain": "company.com",
     "ad_base_dn": "DC=company,DC=com"
   }
   ```

### Testing Connection

1. **Start the server** (if not already running)
2. **Launch the client** with server_url configured
3. **Attempt login** - successful authentication indicates proper connection
4. **Check server logs** for connection attempts

## Network Configuration

### Firewall Settings

**Server Ports**:
- **5000**: Default HTTP port (development)
- **443**: HTTPS port (production)

**Client Requirements**:
- Outbound HTTPS access to server URL
- No inbound ports required (client initiates connections)

### TLS/SSL Certificates

For production deployment:

1. **Obtain SSL certificate** (Let's Encrypt, commercial, or self-signed for testing)
2. **Configure paths** in server .env:
   ```bash
   TLS_CERT_PATH=/etc/ssl/certs/forensic-server.pem
   TLS_KEY_PATH=/etc/ssl/private/forensic-server.key
   ```

3. **Client connection** must use `https://` URL

### Proxy Configuration

If server is behind a reverse proxy (nginx, Apache):

1. **Configure proxy** to forward requests to server port
2. **Set server to run on localhost**:
   ```bash
   SERVER_HOST=127.0.0.1
   SERVER_PORT=5000
   ```

3. **Client connects** to proxy URL (e.g., `https://forensic.company.com`)

## Deployment Options

### Development Environment

```bash
# Client
FLASK_DEBUG=True python main.py

# Server
FLASK_ENV=development python server.py
```

### Production Environment

#### Using Systemd (Linux)

1. **Create service file** `/etc/systemd/system/forensic-server.service`:
   ```ini
   [Unit]
   Description=Forensic Report Server
   After=network.target

   [Service]
   User=forensic
   WorkingDirectory=/path/to/forensic-app
   ExecStart=/usr/bin/python3 server.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and start service**:
   ```bash
   sudo systemctl enable forensic-server
   sudo systemctl start forensic-server
   ```

### Load Balancing

For high-availability deployments:

1. **Multiple server instances** behind load balancer
2. **Shared database** (PostgreSQL/MySQL required)
3. **Shared Redis** for session/cache consistency
4. **Sticky sessions** or JWT-based routing

## Troubleshooting Installation

### Common Client Issues

**Application won't start**
- Verify Python 3.8+ installation
- Check all dependencies installed: `pip list`
- Run with debug: `python main.py --debug`

**Charts not displaying**
- Install matplotlib: `pip install matplotlib`
- For Linux: `sudo apt install python3-tk`

**PDF export fails**
- Install weasyprint system dependencies
- Check write permissions in case directories

### Common Server Issues

**Server won't start**
- Check JWT_SECRET is set and >=32 characters
- Verify database URL format
- Ensure port 5000 is not in use: `netstat -tlnp | grep 5000`

**Database connection fails**
- Test connection manually
- Check database server is running
- Verify credentials in DATABASE_URL

**TLS certificate errors**
- Validate certificate paths and permissions
- Check certificate validity: `openssl x509 -in cert.pem -text`
- Ensure full certificate chain

**Client can't connect to server**
- Verify server is running and accessible
- Check firewall rules
- Test connection: `curl https://your-server.com:5000/api/v1/auth/login`

### Logs and Debugging

**Client Logs**:
- Application logs in console/output
- Error details in terminal

**Server Logs**:
- Main logs: `logs/server.log`
- Startup issues: console output
- Debug mode: set `FLASK_DEBUG=True`

## Post-Installation Setup

### Initial Data Setup

1. **Create admin user** (if using server)
2. **Import existing cases** (if migrating from standalone)
3. **Configure user roles and permissions**

### Legal Template Library Setup

After first login, users can build legal template libraries for preservation letters, subpoenas, and search warrants:

1. Open **Tools → Legal Template Library** in the desktop app.
2. Create vendor folders and template type subfolders.
3. Add one or more templates per folder.
4. Use **Share Folder** for limited sharing or **Share Library** for full sharing.
5. Use import/export to move template sets between environments.

### Security Hardening

1. **Change default passwords**
2. **Enable TLS/HTTPS**
3. **Configure firewall rules**
4. **Set up log monitoring**
5. **Regular backup procedures**

### Performance Tuning

1. **Database indexing** (automatic)
2. **Cache configuration** (Redis recommended for production)
3. **Connection pooling** settings
4. **Monitor resource usage**

## Related Documentation

- [Main Application User Guide](MAIN_USER_GUIDE.md)
- [Server User Guide](SERVER_USER_GUIDE.md)
- [Server Component Guide](SERVER_COMPONENT_GUIDE.md)
- [Server Deployment Guide](SERVER_DEPLOYMENT_GUIDE.md)
- [Legal Workflow Guide](LEGAL_WORKFLOW_GUIDE.md)

