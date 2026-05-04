# Phased Migration Plan — Python to C# Architectural Parity
**Project:** FuDog Labs Forensic Report Suite  
**Start Date:** April 23, 2026  
**Goal:** Bring the Python codebase up to the structural and feature quality level of the C# implementation without breaking any existing functionality.

---

## Guiding Principles

1. **Additive first.** New architecture layers live alongside existing code; nothing is deleted until the replacement is verified.
2. **No feature regressions.** Python-only features (notifications, archive, peer review, legal workflow, accessibility) are preserved and eventually become first-class citizens.
3. **Existing tests must keep passing** throughout every phase.
4. **Incremental extraction.** Move one concern at a time — domain → application → infrastructure → presentation.
5. **Reference the C# code**, not copy it. The C# is the architectural blueprint; Python idioms (dataclasses, ABCs, typing) apply.

## Future-Proofing Decisions (Locked In Early)

1. **Contract-first services.** All business use-cases must have explicit ABC contracts before implementation.
2. **Typed DTO boundaries.** Avoid `dict`/`object` payload drift between layers; define DTOs up-front for every feature domain.
3. **Built-in pagination contract.** Collection queries use `PaginationParams` + `PagedResult[T]` to avoid breaking signatures later.
4. **Transactional consistency.** Use `IUnitOfWork` for multi-step writes (e.g., state change + audit record) from Phase 2 onward.
5. **Replaceable cross-cutting services.** Encryption, clock/time, ID generation, and caching are interface-driven in application layer.
6. **Repository specialization.** Keep `IRepository[T]` as base, but define typed repositories (`ICaseRepository`, etc.) for query clarity.

---

## Phase 0 — Architecture Scaffolding ✅ DONE
**Scope:** Create the four-layer directory skeleton with proper `__init__.py` files, base interfaces, and placeholder modules. No business logic moved yet.

**Deliverables (this session):**
- `domain/` — entities, enums, exceptions, interfaces
- `application/` — interfaces (ABCs), services skeleton, DTOs skeleton
- `infrastructure/` — persistence/repositories skeleton, encryption, logging
- `presentation/` — marker package (existing UI files will migrate here)
- `PARITY_MATRIX.md` — living comparison document
- `MIGRATION_PLAN.md` — this file

**Success criteria:** All four packages import cleanly; no existing tests broken.

---

## Phase 1 — Domain Layer
**Effort:** ~5–7 days  
**Priority:** P1 — blocks all later phases

### What to build

| File | Description |
|------|-------------|
| `domain/enums/case_status.py` | `CaseStatus` enum with valid-transition rules (state machine) |
| `domain/enums/report_status.py` | `ReportStatus` enum |
| `domain/enums/evidence_status.py` | `EvidenceStatus` enum |
| `domain/enums/template_category.py` | 25 template categories matching C# `TemplateCategory` |
| `domain/enums/notification_type.py` | `NotificationType` enum |
| `domain/exceptions/domain_exceptions.py` | `InvalidStatusTransitionError`, `DomainValidationError`, `EntityNotFoundError`, `DuplicateEntityError` |
| `domain/interfaces/base.py` | `IEntity`, `IAuditable` protocols |
| `domain/entities/case.py` | Aggregate root — encapsulated collections, transition methods, computed props |
| `domain/entities/report.py` | Report with encrypted content, appendices, status |
| `domain/entities/evidence.py` | Evidence with imaging status machine |
| `domain/entities/legal_process.py` | SLA properties, approval tracking |
| `domain/entities/audit_entry.py` | SHA-256 hash-chained entry |
| `domain/entities/notification.py` | Notification entity |
| `domain/entities/court_date.py` | CourtDate entity |
| `domain/entities/investigative_lead.py` | Lead entity |
| `domain/entities/template.py` | Template with versioning, placeholders |
| `domain/entities/template_placeholder.py` | Typed placeholder value object |
| `domain/entities/template_version.py` | Immutable version snapshot |

### Rules
- Domain layer has **zero** external dependencies (no SQLAlchemy, no PyQt5, no Flask).
- All validation raises domain exceptions, not `ValueError`/`AssertionError`.
- Entities use Python `dataclasses` or `__slots__` classes with factory classmethods (`Entity.create(...)`).
- Collections are encapsulated — callers get copies, mutations go through intent methods.

### Migration path for existing code
- `status_validator.py` → absorb transition logic into `CaseStatus.can_transition_to()`, then deprecate
- `models.py` (SQLAlchemy) → keep for server/API layer; domain entities are separate
- `database.py` → unchanged until Phase 3

### Tests to write
```
tests/domain/test_case_status_transitions.py
tests/domain/test_case_entity.py
tests/domain/test_audit_entry_hashing.py
tests/domain/test_template_placeholder.py
```

---

## Phase 2 — Application Layer (Services & DTOs)
**Effort:** ~7–10 days  
**Priority:** P1  
**Status:** 🟢 **70% Complete** (as of 2026-04-24)

### What to build

| File | Description |
|------|-------------|
| `application/interfaces/i_repository.py` | Generic `IRepository[T]` ABC |
| `application/interfaces/i_case_service.py` | `ICaseService` ABC |
| `application/interfaces/i_report_service.py` | `IReportService` ABC |
| `application/interfaces/i_template_service.py` | `ITemplateService` ABC — full 35-method contract matching C# |
| `application/interfaces/i_audit_service.py` | `IAuditService` ABC |
| `application/interfaces/i_notification_service.py` | `INotificationService` ABC |
| `application/interfaces/i_legal_workflow_service.py` | `ILegalWorkflowService` ABC |
| `application/interfaces/i_evidence_service.py` | `IEvidenceService` ABC |
| `application/interfaces/i_peer_review_service.py` | `IPeerReviewService` ABC |
| `application/interfaces/i_note_service.py` | `INoteService` ABC |
| `application/interfaces/i_glossary_service.py` | `IGlossaryService` ABC |
| `application/interfaces/i_encryption_service.py` | `IEncryptionService` ABC |
| `application/interfaces/i_unit_of_work.py` | `IUnitOfWork` ABC + repository accessors + commit/rollback |
| `application/interfaces/i_clock.py` | `IClock` ABC for deterministic time handling |
| `application/interfaces/i_id_generator.py` | `IIdGenerator` ABC for deterministic IDs in tests |
| `application/interfaces/i_cache_service.py` | `ICacheService` ABC for dashboard/template cache |
| `application/interfaces/i_case_repository.py` | `ICaseRepository` typed repository interface |
| `application/interfaces/i_report_repository.py` | `IReportRepository` typed repository interface |
| `application/interfaces/i_template_repository.py` | `ITemplateRepository` typed repository interface |
| `application/interfaces/i_notification_repository.py` | `INotificationRepository` typed repository interface |
| `application/interfaces/i_audit_repository.py` | `IAuditRepository` typed repository interface |
| `application/dtos/case_dto.py` | `CaseDto`, `CreateCaseDto`, `UpdateCaseDto` |
| `application/dtos/report_dto.py` | `ReportDto` |
| `application/dtos/template_dto.py` | `TemplateDto`, `TemplatePlaceholderDto` |
| `application/dtos/evidence_dto.py` | `EvidenceDto` |
| `application/dtos/notification_dto.py` | `NotificationDto` |
| `application/dtos/legal_workflow_dto.py` | `LegalProcessDto`, `CreateLegalProcessDto`, `UpdateLegalProcessDto` |
| `application/dtos/court_date_dto.py` | `CourtDateDto`, `CreateCourtDateDto` |
| `application/dtos/audit_dto.py` | `AuditEntryDto` |
| `application/dtos/note_dto.py` | `NoteDto`, `CreateNoteDto`, `UpdateNoteDto` |
| `application/dtos/pagination.py` | `PaginationParams`, `PagedResult[T]` |
| `application/services/case_service.py` | Implements `ICaseService`, calls repositories + audit |
| `application/services/report_service.py` | Implements `IReportService` |
| `application/services/audit_service.py` | Replaces `audit_log.py` as central service |
| `application/services/notification_service.py` | Replaces `notification_manager.py` |
| `application/services/legal_workflow_service.py` | Replaces `legal_workflow_helpers.py` |

### Rules
- Services depend only on interfaces (ABCs), never concrete infrastructure classes.
- Every state-changing service method emits an audit event.
- DTOs are plain dataclasses — no framework imports.
- Collection endpoints must support pagination contracts (`PaginationParams`/`PagedResult`) even if v1 callers request full lists.
- Services that write multiple records in one use-case must use `IUnitOfWork`.

### Migration path for existing code
- `legal_workflow_helpers.py` → logic moves to `LegalWorkflowService`; existing module becomes thin shim calling new service
- `notification_manager.py` → logic moves to `NotificationService`; existing module becomes thin shim
- `audit_log.py` → logic moves to `AuditService`; existing file-based implementation becomes `FileAuditRepository` in infrastructure
- `templates.py` → logic moves to `TemplateService`; existing `TemplateManager` dialog remains as UI only

### Tests to write
```
tests/application/test_case_service.py
tests/application/test_template_service.py
tests/application/test_legal_workflow_service.py
tests/application/test_notification_service.py
```

---

## Phase 3 — Infrastructure Layer (Persistence & Repositories)
**Effort:** ~7–10 days  
**Priority:** P1  
**Status:** 🟢 **100% Complete** (as of 2026-04-24)

### What to build

| File | Description |
|------|-------------|
| `infrastructure/persistence/db_context.py` | Thin wrapper exposing connection (local SQLite + server mode) |
| `infrastructure/persistence/repositories/case_repository.py` | Implements `ICaseRepository`, maps DB rows → domain entities |
| `infrastructure/persistence/repositories/report_repository.py` | Encrypted HTML BLOB handling |
| `infrastructure/persistence/repositories/evidence_repository.py` | Evidence CRUD |
| `infrastructure/persistence/repositories/legal_process_repository.py` | Legal process CRUD |
| `infrastructure/persistence/repositories/audit_repository.py` | DB-persisted audit entries (replaces file log) |
| `infrastructure/persistence/repositories/notification_repository.py` | Persistent notifications |
| `infrastructure/persistence/repositories/template_repository.py` | Template + version + placeholder persistence |
| `infrastructure/persistence/repositories/peer_review_repository.py` | Peer review export/import persistence |
| `infrastructure/persistence/repositories/note_repository.py` | Notes persistence and search |
| `infrastructure/encryption/encryption_service.py` | Extracts from `secure_key_manager.py` behind an interface |
| `infrastructure/caching/cache_service.py` | Concrete cache adapter (in-memory now, Redis-ready later) |
| `infrastructure/logging/audit_logger.py` | Concrete `AuditService` backed by `AuditRepository` |
| `infrastructure/time/system_clock.py` | `IClock` implementation |
| `infrastructure/ids/uuid_id_generator.py` | `IIdGenerator` implementation |

### Rules
- Repositories depend only on domain entities and `db_context.py`.
- No business logic inside repositories — map data, nothing else.
- `DatabaseManager` in `database.py` is **not deleted** yet; new repositories are wired in parallel and tested against the same SQLite file.
- Encryption service wraps existing `secure_key_manager.py` behind `IEncryptionService` ABC so it can be swapped.
- Cache service is adapter-based so dashboard/template caches can move to Redis without changing application services.

### Migration path for existing code
- `database.py` → remains as legacy shim until all callers are migrated; add deprecation notice at top
- `secure_key_manager.py` → wrapped by `EncryptionService`, not deleted

### Tests to write
```
tests/infrastructure/test_case_repository.py
tests/infrastructure/test_template_repository.py
tests/infrastructure/test_audit_repository.py
tests/infrastructure/test_encryption_service.py
```

---

## Phase 4 — Presentation Layer Cleanup (Editor Features)
**Effort:** ~5–7 days  
**Priority:** P2

### What to build / improve

| File | Description |
|------|-------------|
| `presentation/` | Move all UI modules here; `main.py` becomes entry point only |
| `presentation/tabs/case_tab.py` | Thin — delegate to `CaseService`, no direct DB calls |
| `presentation/tabs/notes_tab.py` | Thin — delegate to service |
| `presentation/tabs/reports_tab.py` | Thin — delegate to `ReportService` |
| `presentation/editors/word_processor.py` | Moved from root; stays intact, gains `FormatPainterService` |
| `presentation/editors/base_editor.py` | Stays intact; absorbs shared toolbar logic |
| `presentation/dialogs/` | All dialog modules moved here |
| `presentation/services/format_painter_service.py` | Copy-paste formatting (Python-only feature, not in C#) |
| `presentation/services/report_export_service.py` | DOCX/PDF export extracted from `reports_tab.py` |
| `presentation/services/timestamp_insert_service.py` | Insert-local / insert-ISO-timestamp actions |
| `presentation/services/advanced_table_service.py` | Evidence table auto-generation |

### Closing gaps vs C#
- Add uppercase/lowercase/roman list style variants to word processor toolbar
- Wire appendix management into `ReportService` (not raw DB call)
- Add DOCX round-trip (import+export) backed by `ReportExportService`

### Tests to write
```
tests/presentation/test_word_processor_formatting.py
tests/presentation/test_report_export_service.py
```

---

## Phase 5 — Template System Upgrade
**Effort:** ~7–10 days  
**Priority:** P1 (C# is significantly ahead here)

### What to build

| File | Description |
|------|-------------|
| `application/services/template_service.py` | Full `ITemplateService` implementation |
| `infrastructure/persistence/repositories/template_repository.py` | DB-backed template + version + placeholder |
| `domain/entities/template.py` | Full entity with versioning, composition (Phase 1 scaffold promoted to full) |
| `domain/entities/template_placeholder.py` | Typed placeholder with validation patterns |
| `domain/entities/template_version.py` | Immutable version snapshot with rollback support |
| `domain/enums/template_category.py` | 25 categories (Phase 0 scaffold promoted to full) |
| `presentation/dialogs/template_manager_dialog.py` | Replace `templates.py` TemplateManager — DB-backed, categorised, searchable |
| Migration v9 | Add `templates`, `template_versions`, `template_placeholders` tables to SQLite |

### Rules
- Must remain backward-compatible: existing `templates.json` auto-imported on first run.
- Template CRUD must emit audit events via `AuditService`.

---

## Phase 6 — Python-Only Feature Hardening
**Effort:** ~10–14 days  
**Priority:** P2 — preserve Python's advantages

These features exist in Python only; they need service-layer backing (from Phases 2–3) before they can be properly maintained.

| Feature | Current file | Action |
|---------|-------------|--------|
| Notifications | notification_manager.py | Wire to `NotificationService` + `NotificationRepository` |
| Archive system | archive_case_dialog.py, archived_cases_dialog.py | Wire to `CaseService.archive()` / `CaseService.restore()` |
| Peer review | peer_review.py, peer_review_portable.py | Wire to `ReportService.export_for_review()` + `PeerReviewService` |
| Legal workflow | legal_workflow_helpers.py + dialogs | Wire to `LegalWorkflowService` |
| Dashboard charts | dashboard_bp.py, dashboard_chart_settings.py | Wire to `CaseService.get_dashboard_metrics()` |
| Accessibility themes | accessibility.py | Extract `ThemeService` behind interface |

---

## Phase 7 — Test Coverage
**Effort:** ~7–10 days  
**Priority:** P1 (both codebases have gaps here)

### Test targets

```
tests/
  domain/
    test_case_entity.py           # Factory, transitions, computed props
    test_case_status_transitions.py  # All valid/invalid transitions
    test_audit_entry_hashing.py   # SHA-256 chain integrity
    test_template_placeholder.py  # Type validation, format output
    test_template_versioning.py   # Create version, rollback
  application/
    test_case_service.py          # CRUD + audit events emitted
    test_template_service.py      # Full lifecycle incl. versioning
    test_legal_workflow_service.py  # SLA, approvals, overdue detection
    test_notification_service.py  # Trigger conditions, read/unread
  infrastructure/
    test_case_repository.py       # Round-trip: entity → DB → entity
    test_template_repository.py   # Versions + placeholders persisted
    test_audit_repository.py      # Chain integrity in DB
    test_encryption_service.py    # Encrypt/decrypt round-trip
  presentation/
    test_word_processor_formatting.py
    test_report_export_service.py
```

Existing test files (`test_security.py`, `test_court_dates.py`, etc.) must remain green after each phase.

---

## Dependency Map Between Phases

```
Phase 0 (Scaffold)
    └─► Phase 1 (Domain entities + enums + exceptions)
            └─► Phase 2 (Application services + interfaces + DTOs)
                    ├─► Phase 3 (Infrastructure: repositories + encryption)
                    └─► Phase 4 (Presentation cleanup)
                                └─► Phase 5 (Template system upgrade)
                                        └─► Phase 6 (Python-only feature hardening)
                                                └─► Phase 7 (Test coverage)
```

Phase 4 and Phase 3 can proceed in parallel once Phase 2 interfaces are defined.

---

## Target Directory Structure (end state)

```
Forensic-Report-and-Notes-main/
├── domain/                            # Zero external deps
│   ├── entities/
│   │   ├── case.py
│   │   ├── report.py
│   │   ├── template.py
│   │   ├── template_placeholder.py
│   │   ├── template_version.py
│   │   ├── evidence.py
│   │   ├── legal_process.py
│   │   ├── audit_entry.py
│   │   ├── notification.py
│   │   ├── court_date.py
│   │   └── investigative_lead.py
│   ├── enums/
│   │   ├── case_status.py
│   │   ├── report_status.py
│   │   ├── evidence_status.py
│   │   ├── template_category.py
│   │   └── notification_type.py
│   ├── exceptions/
│   │   └── domain_exceptions.py
│   └── interfaces/
│       └── base.py
│
├── application/                       # Depends on domain only
│   ├── interfaces/
│   │   ├── i_repository.py
│   │   ├── i_case_service.py
│   │   ├── i_report_service.py
│   │   ├── i_template_service.py
│   │   ├── i_audit_service.py
│   │   ├── i_notification_service.py
│   │   └── i_legal_workflow_service.py
│   ├── services/
│   │   ├── case_service.py
│   │   ├── report_service.py
│   │   ├── template_service.py
│   │   ├── audit_service.py
│   │   ├── notification_service.py
│   │   └── legal_workflow_service.py
│   └── dtos/
│       ├── case_dto.py
│       ├── report_dto.py
│       ├── template_dto.py
│       ├── evidence_dto.py
│       └── notification_dto.py
│
├── infrastructure/                    # Depends on application + domain
│   ├── persistence/
│   │   ├── db_context.py
│   │   └── repositories/
│   │       ├── case_repository.py
│   │       ├── report_repository.py
│   │       ├── evidence_repository.py
│   │       ├── legal_process_repository.py
│   │       ├── audit_repository.py
│   │       ├── notification_repository.py
│   │       └── template_repository.py
│   ├── encryption/
│   │   └── encryption_service.py
│   └── logging/
│       └── audit_logger.py
│
├── presentation/                      # Depends on application only
│   ├── tabs/
│   │   ├── case_tab.py
│   │   ├── notes_tab.py
│   │   └── reports_tab.py
│   ├── dialogs/
│   │   ├── archive_case_dialog.py
│   │   ├── archived_cases_dialog.py
│   │   ├── legal_workflow_dialogs.py
│   │   ├── status_color_dialog.py
│   │   └── template_manager_dialog.py
│   ├── editors/
│   │   ├── word_processor.py
│   │   └── base_editor.py
│   ├── services/
│   │   ├── format_painter_service.py
│   │   ├── report_export_service.py
│   │   └── timestamp_insert_service.py
│   └── components/
│       ├── notifications_panel.py
│       ├── notification_settings.py
│       └── dashboard_chart_settings.py
│
├── main.py                            # Entry point only — wires DI
├── server.py                          # Flask server — unchanged
├── auth.py, security.py, ...         # Root-level modules (migrated later)
│
└── tests/
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── presentation/
```

---

## Progress Tracker

| Phase | Status | Started | Completed |
|-------|--------|---------|-----------|
| Phase 0 — Scaffold | ✅ Complete | 2026-04-23 | 2026-04-23 |
| Phase 1 — Domain Layer | ✅ Complete | 2026-04-23 | 2026-04-23 |
| Phase 2 — Application Layer | 🟡 In Progress | 2026-04-23 | — |
| Phase 3 — Infrastructure | ⬜ Not Started | — | — |
| Phase 4 — Presentation Cleanup | ⬜ Not Started | — | — |
| Phase 5 — Template System | ⬜ Not Started | — | — |
| Phase 6 — Python Feature Hardening | ⬜ Not Started | — | — |
| Phase 7 — Test Coverage | ⬜ Not Started | — | — |
