"""
application — Orchestration layer.

Layer rules:
  - MAY import from domain only.
  - No SQLAlchemy, no PyQt5, no Flask imports.
  - All external dependencies are behind interfaces (ABCs).
  - Services emit audit events; UI / infrastructure wire them up.
"""
