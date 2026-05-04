# Server View and Discovery API

This document describes the new role-based server management APIs.

## Auth Model

All protected endpoints require JWT bearer tokens.

- Admin: full access to server views and admin user management.
- Supervisor: access to case management and discovery views, no user management.

Tokens should include role metadata.

Example claims:

```json
{
  "sub": "alice",
  "role": "admin",
  "username": "alice"
}
```

## Server View Endpoints

Base path: `/api/v1/server-view`

### GET `/layout`

Returns role-specific tabs and toolbar actions.

### GET `/cases?view=case|examiner&search=&status=&examiner=`

Case management view data.

- `view=case`: case rows
- `view=examiner`: grouped by examiner/investigator

### GET `/search?q=<text>&scope=all|cases|examiners|investigators`

Global server-side search for case management.

### GET `/admin/users` (Admin only)

List user accounts.

### POST `/admin/users` (Admin only)

Create/reactivate a user.

Request body:

```json
{
  "username": "super1",
  "role": "supervisor"
}
```

### DELETE `/admin/users/<username>` (Admin only)

Soft-disable a user account.

### Supervisor Assignment Endpoints (Admin only)

- GET `/api/v1/server-view/admin/supervisor-assignments`
- POST `/api/v1/server-view/admin/supervisor-assignments`
- DELETE `/api/v1/server-view/admin/supervisor-assignments/<assignment_id>`

Assignment payload:

```json
{
  "supervisor": "sup1",
  "investigator": "invest1",
  "examiner": "exam1"
}
```

## Report Workflow Endpoints

Base path: `/api/v1/reports`

- GET `/<case_number>`: view report + comments + workflow + peer review status
- PUT `/<case_number>`: edit report content
- GET `/<case_number>/comments`: list report comments
- POST `/<case_number>/comments`: add comment
- POST `/<case_number>/approve`: approve report (admin/supervisor)
- POST `/<case_number>/deny`: deny report with required reason (admin/supervisor)

Deny payload:

```json
{
  "reason": "Need clearer chain-of-custody narrative."
}
```

## Case Evidence and Court Date Endpoints

Base path: `/api/v1/cases`

- POST `/<case_number>/evidence`: add evidence to case
- GET `/<case_number>/court-dates`: list court dates
- POST `/<case_number>/court-dates`: add court date
- PUT `/<case_number>/assignments`: update investigator/examiner assignment

Court date payload:

```json
{
  "date_type": "hearing",
  "event_date": "2026-05-10",
  "notes": "initial hearing"
}
```

## Examiner Peer Review Connection Endpoints

Base path: `/api/peer-review`

- GET `/connections`: list peer-review connections
- POST `/connections/request`: examiner requests reviewer connection
- POST `/connections/<connection_id>/approve`: reviewer/admin approves connection

Connection request payload:

```json
{
  "reviewer": "exam2"
}
```

## Discovery Endpoints

Base path: `/api/v1/discovery`

### POST `/heartbeat`

Main desktop applications call this to register presence.

Request body example:

```json
{
  "app_id": "main-01",
  "hostname": "examiner-laptop",
  "ip": "192.168.1.25",
  "port": 5000,
  "username": "alice",
  "version": "1.2.0"
}
```

Optional header:

- `X-Discovery-Token`: required if `DISCOVERY_SHARED_TOKEN` is configured.

### GET `/endpoints` (Admin/Supervisor)

List known endpoints from heartbeat and active scan.

### POST `/scan` (Admin/Supervisor)

Actively scans configured LAN ranges for candidate main apps.

### PUT `/trust/<app_id>` (Admin only)

Update endpoint trust state.

Request body:

```json
{
  "trust_state": "trusted"
}
```

Allowed trust states:

- `trusted`
- `pending`
- `untrusted`

## Notes

- API blueprints are CSRF-exempt because they use bearer tokens.
- Discovery scan defaults to `/24` heuristics if `DISCOVERY_SCAN_CIDRS` is empty.
- Active scan yields `active-scan-candidate` or `active-scan-verified` sources.
- Desktop main app auto-registers with discovery heartbeat on startup (and periodically) when `server_url` is configured in `config.json`.
- Desktop heartbeat config lives in `config.json` under `discovery_heartbeat`:

```json
{
  "discovery_heartbeat": {
    "enabled": true,
    "interval_seconds": 60,
    "shared_token": "",
    "probe_enabled": true,
    "probe_port": 8765
  }
}
```

- If server `DISCOVERY_SHARED_TOKEN` is set, use the same value in desktop `discovery_heartbeat.shared_token`.
- When `probe_enabled` is true, desktop app serves `GET /api/v1/client/discovery` on `probe_port` to allow active-scan verification.
