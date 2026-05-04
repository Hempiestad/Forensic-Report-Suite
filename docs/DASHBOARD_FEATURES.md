Dashboard Overview — Features added
=================================

Summary
-------
This project now includes an enhanced dashboard overview showing per-case evidence and legal summaries, trial/sentencing dates, and inline editing for quick updates.

At-a-glance columns
- Case #: case identifier
- Assigned To: who is responsible
- Evidence: color-coded badges and per-item detail (hover for tooltips)
- Legal: color-coded badges for legal processes (Investigator view)
- Report Status: case workflow status
- Trial Date: optional ISO date (YYYY-MM-DD)
- Sentencing: optional ISO date (YYYY-MM-DD)

Quick features
- Inline editing: double-click or context-menu → "Edit Dates..." to update trial/sentencing. Edits are validated (ISO) and saved locally or via server API.
- In-place edits: trial/sentencing cells are editable directly; changes are saved when the cell is changed.
- Upcoming Trials: set the number of days to consider as "upcoming" and toggle highlighting or filter to show only upcoming trials.
- Sorting: trial-date column is sortable. The last sort preference is persisted in `config.json` under `dashboard_sort`.

Server API
- `PUT /api/v1/cases/<case_number>/dates` — update `trial_date` and/or `sentencing_date` (requires assigned user or admin/supervisor). Dates must be ISO formatted (YYYY-MM-DD).

Notes
- Local DB column migration automatically adds `trial_date` and `sentencing_date` to the `reports` table.
- Tests covering local DB save and server endpoint behavior are included: `test_db_dates.py`, `test_server_dates.py`, `test_server_dates_permissions.py`.
