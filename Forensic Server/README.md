# Forensic Server

This folder contains the extracted server component for the Forensic Report Suite.

## Run

### Quick Install

```powershell
./install_server.ps1 -WithVenv
```

This installs server dependencies and creates `.env` from `.env.example` if needed.

Edit `Forensic Server/.env` and set at least `JWT_SECRET` before starting.

### Start Server

Set the required environment variables first, especially `JWT_SECRET`, then run:

```powershell
python server.py
```

You can also run the package entrypoint:

```powershell
python -m forensic_server
```

## Notes

- The repo-root `server.py` remains as a compatibility wrapper.
- The desktop app can continue importing root wrappers such as `cases_bp.py` during the transition.
- Server code in this folder no longer depends on `database.py` for dashboard or peer-review routes.
