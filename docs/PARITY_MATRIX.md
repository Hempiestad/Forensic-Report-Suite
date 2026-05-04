# Feature Parity Matrix — Python vs C# Codebase
**Last Updated:** April 24, 2026  
**Source of truth:** live code in both repos  
**Symbols:** ✅ Implemented | ⚠️ Partial / needs improvement | ❌ Missing | N/A Not applicable

---

## Legend

| Priority | Meaning |
|----------|---------|
| **P1** | Blocking — required for production quality parity |
| **P2** | High — significant feature gap |
| **P3** | Medium — improvement needed |
| **P4** | Low — nice-to-have |

---

## 1. Architecture & Code Quality

| Feature | Python | C# | Gap Direction | Priority | Migration Phase |
|---------|--------|----|---------------|----------|----------------|
| Layered architecture (Domain / Application / Infrastructure / Presentation) | ✅ All four layers scaffolded + Phase 2 services implemented | ✅ Clean Architecture | Parity | **P1** | Phase 1–4 |
| Domain entities (rich behaviour, not anemic) | ✅ All core entities implemented (Case, Report, Evidence, LegalProcess, CourtDate, Notification, AuditEntry) | ✅ Full DDD entities | Parity | **P1** | Phase 1 |
| Repository pattern (data-access abstraction) | ✅ Generic IRepository base + 7 typed repository interfaces; InMemoryCaseRepository adapter created | ✅ Typed repositories | Parity | **P1** | Phase 3 |
| Application services (single-responsibility) | ✅ Core services implemented (Case, Audit, Notification, LegalWorkflow); Report shell + Template shell with Phase 5 stubs; all with tests | ✅ CaseService, TemplateService, … | Python parity | **P1** | Phase 2 |
| Service interfaces / dependency inversion | ✅ 6 service interfaces complete; all tested | ✅ Full interface contracts | Parity | **P1** | Phase 2 |
| DTOs (Data Transfer Objects) | ✅ Pagination, LegalWorkflow, CourtDate, Audit, Note DTOs complete | ✅ Typed DTO classes | Parity | **P2** | Phase 2 |
| Unit of Work transaction boundary | ✅ IUnitOfWork interface with 7 repository accessors | ✅ Transaction boundary per use-case | Parity | **P1** | Phase 2–3 |
| Pagination contract (query params + paged result) | ✅ PaginationParams + PagedResult[T] complete | ✅ Paged query patterns | Parity | **P2** | Phase 2 |
| Cross-cutting abstractions (encryption/cache/clock/ID) | ✅ IClock implemented + injected into services; IEncryptionService, IIdGenerator, ICacheService scaffolded | ✅ Interface-driven | Python parity | **P2** | Phase 2–3 |
| Typed repositories per aggregate | ✅ 7 repository interfaces complete (Case, Report, Template, Notification, Audit, LegalProcess, CourtDate) | ✅ Repository-per-aggregate | Parity | **P1** | Phase 2–3 |
| Status state machine at domain level | ⚠️ Partial in status_validator.py | ✅ CaseStatus with transition rules | C# ahead | **P1** | Phase 1 |
| Type annotations (function signatures) | ⚠️ Partial | ✅ Full compile-time types | C# ahead | **P3** | Phase 2 |
| Automated unit tests — domain layer | ❌ None | ❌ None (no test project yet) | Neither | **P1** | Phase 7 |
| Automated unit tests — service layer | ⚠️ Initial application service tests added (case/audit/report/template contracts) | ❌ None | Python ahead | **P1** | Phase 2, 7 |
| Automated integration tests | ⚠️ 15 files (dates, security, archive) | ❌ None | Python ahead | **P3** | Phase 7 |

---

## 2. Domain Entities

| Entity | Python | C# | Gap Direction | Priority | Phase |
|--------|--------|----|---------------|----------|-------|
| Case (aggregate root) | ⚠️ SQLAlchemy model only | ✅ Rich aggregate root | C# ahead | **P1** | Phase 1 |
| Report entity | ⚠️ Minimal SQLAlchemy model | ✅ Encrypted HTML, versions, status | C# ahead | **P1** | Phase 1 |
| Template entity | ⚠️ JSON-backed manager | ✅ Full domain entity + versioning | C# ahead | **P1** | Phase 5 |
| Evidence entity | ⚠️ DB schema only | ✅ Rich entity with status machine | C# ahead | **P2** | Phase 1 |
| LegalProcess entity | ⚠️ DB schema + helper funcs | ✅ Entity with SLA properties | C# ahead | **P2** | Phase 1 |
| AuditEntry entity | ⚠️ File-based (audit_log.py) | ✅ DB-persisted, queryable | C# ahead | **P2** | Phase 3 |
| Notification entity | ✅ notification_manager.py | ❌ Not implemented | Python ahead | **P2** | Phase 6 |
| CourtDate entity | ⚠️ Embedded in case table | ✅ Standalone entity | C# ahead | **P3** | Phase 1 |
| InvestigativeLead entity | ⚠️ DB table only | ✅ Full entity | C# ahead | **P3** | Phase 1 |
| TemplatePlaceholder value object | ❌ None (basic .format() only) | ✅ Typed, validated, with metadata | C# ahead | **P2** | Phase 5 |

---

## 3. Status & Workflow State Machines

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| CaseStatus enum with valid transitions | ⚠️ status_validator.py (partial) | ✅ CaseStatus enum + transitions | C# ahead | **P1** | Phase 1 |
| ReportStatus enum | ❌ None | ✅ Implemented | C# ahead | **P2** | Phase 1 |
| EvidenceStatus enum | ⚠️ String values in DB | ✅ Typed enum | C# ahead | **P2** | Phase 1 |
| LegalProcessStatus enum | ⚠️ String values | ✅ Typed enum | C# ahead | **P2** | Phase 1 |
| Transition validation at entity level | ❌ Validation in UI layer | ✅ At domain entity | C# ahead | **P1** | Phase 1 |
| Domain exceptions for invalid transitions | ❌ Generic exceptions | ✅ InvalidStatusTransitionError, etc. | C# ahead | **P1** | Phase 1 |

---

## 4. Case Management

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Create / edit / delete cases | ✅ Full | ✅ Full | Parity | — | — |
| Assign cases to users | ✅ | ✅ | Parity | — | — |
| Case search & filter | ✅ | ✅ | Parity | — | — |
| Case status workflow (UI) | ✅ Legal workflow dialogs | ✅ CaseDialog | Parity | — | — |
| Archive cases | ✅ archive_case_dialog.py | ❌ Not implemented | Python ahead | **P2** | Phase 6 |
| View / restore archived cases | ✅ archived_cases_dialog.py | ❌ Not implemented | Python ahead | **P2** | Phase 6 |
| Trial / sentencing date tracking | ✅ | ✅ | Parity | — | — |
| Peer reviewer list on case | ✅ | ⚠️ Partial | Python ahead | **P3** | Phase 6 |

---

## 5. Evidence Management

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Add / edit / delete evidence items | ✅ | ✅ | Parity | — | — |
| Evidence imaging status tracking | ✅ | ✅ | Parity | — | — |
| Evidence type classification | ✅ | ✅ | Parity | — | — |
| Auto-generate evidence table in report | ✅ reports_tab.py | ❌ Not implemented | Python ahead | **P2** | Phase 4 |
| NIST template with evidence population | ✅ | ❌ | Python ahead | **P2** | Phase 5 |
| Physical device detail fields (SN, IMEI, etc.) | ✅ | ✅ | Parity | — | — |

---

## 6. Report Editor / Word Processing

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Bold / italic / underline | ✅ | ✅ | Parity | — | — |
| Strikethrough | ✅ word_processor.py | ✅ FontFormattingService | Parity | — | — |
| Superscript / subscript | ✅ | ✅ | Parity | — | — |
| Text foreground color | ✅ | ✅ | Parity | — | — |
| Text background / highlight color | ✅ | ✅ | Parity | — | — |
| Text case conversion (UPPER/lower/Title) | ✅ | ✅ | Parity | — | — |
| Paragraph alignment | ✅ | ✅ | Parity | — | — |
| Indentation (increase / decrease) | ✅ | ✅ | Parity | — | — |
| Line spacing (single / 1.5x / double) | ✅ word_processor.py | ✅ ParagraphFormattingService | Parity | — | — |
| Paragraph spacing (before / after) | ✅ | ✅ | Parity | — | — |
| Heading styles (H1 / H2 / H3 / Normal) | ✅ | ✅ | Parity | — | — |
| Bullet lists | ✅ | ✅ | Parity | — | — |
| Numbered lists | ✅ | ✅ | Parity | — | — |
| Uppercase / lowercase / roman list styles | ✅ word_processor.py | ⚠️ Basic only | Python ahead | **P3** | Phase 4 |
| Find & Replace (case, whole-word, regex) | ✅ word_processor.py | ✅ FindReplaceService | Parity | — | — |
| Format painter (copy / paste formatting) | ✅ word_processor.py | ❌ Not implemented | Python ahead | **P3** | Phase 4 |
| Insert table (advanced, with dialog) | ✅ word_processor.py | ⚠️ Basic only | Python ahead | **P3** | Phase 4 |
| Insert image | ✅ | ✅ | Parity | — | — |
| Insert page break | ✅ | ✅ | Parity | — | — |
| Insert timestamp (local / ISO) | ✅ Ctrl+Shift+T | ⚠️ Conversion only, no insert | Python ahead | **P3** | Phase 4 |
| Auto-save | ✅ | ✅ | Parity | — | — |
| Word count | ✅ | ✅ | Parity | — | — |
| Appendix management (add / view / remove) | ✅ reports_tab.py | ❌ Not implemented | Python ahead | **P2** | Phase 4 |
| Reusable word-processing shell | ⚠️ Tightly coupled to tab widgets | ✅ WordProcessingShell XAML control | C# ahead | **P2** | Phase 4 |
| PDF export | ✅ | ✅ | Parity | — | — |
| DOCX import / export | ⚠️ Import only (basic) | ✅ Full round-trip via ReportExportService | C# ahead | **P2** | Phase 4 |

---

## 7. Template System

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| SWGDE / NIST standard template | ✅ | ✅ | Parity | — | — |
| Basic blank template | ✅ | ✅ | Parity | — | — |
| Template CRUD (add / edit / delete) | ✅ templates.py | ✅ TemplateService | Parity | — | — |
| Database-backed persistence | ❌ File-based JSON | ✅ EF Core / SQLite | C# ahead | **P1** | Phase 5 |
| Template versioning & rollback | ❌ None | ✅ Full history | C# ahead | **P1** | Phase 5 |
| 25 categorised template types | ❌ 2 templates | ✅ 25 categories (SWGDE/mobile/network/…) | C# ahead | **P2** | Phase 5 |
| Typed placeholder validation | ❌ Basic str.format() only | ✅ TemplatePlaceholder value object | C# ahead | **P1** | Phase 5 |
| Auto-detect placeholders from HTML | ❌ | ✅ | C# ahead | **P2** | Phase 5 |
| Template search (full-text) | ❌ | ✅ | C# ahead | **P2** | Phase 5 |
| Template favorites | ❌ | ✅ | C# ahead | **P3** | Phase 5 |
| Usage tracking / statistics | ❌ | ✅ | C# ahead | **P3** | Phase 5 |
| Import from DOCX | ⚠️ Basic | ✅ Full import via ReportExportService | C# ahead | **P2** | Phase 5 |
| Export to DOCX / HTML / JSON | ❌ | ✅ | C# ahead | **P2** | Phase 5 |
| Bulk import / export (ZIP) | ❌ | ✅ | C# ahead | **P3** | Phase 5 |
| Template inheritance / composition | ❌ | ✅ ParentTemplateId | C# ahead | **P3** | Phase 5 |
| Template audit integration | ❌ | ✅ AuditEntry for every CRUD op | C# ahead | **P2** | Phase 5 |

---

## 8. Notes

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Create / edit / delete notes | ✅ | ✅ | Parity | — | — |
| Insert note into report | ✅ | ✅ InsertFromNotesDialog | Parity | — | — |
| Note template support | ✅ | ⚠️ Partial | Python ahead | **P3** | Phase 5 |

---

## 9. Glossary Assist

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| SWGDE term detection while typing | ✅ glossary_assist.py | ✅ GlossaryAssistService | Parity | — | — |
| Suggestion tooltip popup | ✅ | ⚠️ Timer-based, needs polish | Python ahead | **P3** | Phase 4 |
| Auto-insert footnote with numbering | ✅ | ⚠️ Service exists, not fully wired | C# ahead | **P3** | Phase 4 |
| Footnote deduplication | ✅ | ⚠️ Partial | Python ahead | **P3** | Phase 4 |
| Glossary term dictionary | ✅ | ✅ GlossaryTerms.cs | Parity | — | — |

---

## 10. Audit Trail

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Tamper-evident hash-chained entries | ✅ audit_log.py (file) | ✅ AuditEntry entity (DB) | Both good | — | — |
| Database-persisted audit | ❌ File-based per case | ✅ Central DB via AuditLogger service | C# ahead | **P2** | Phase 3 |
| Queryable audit log | ❌ File parse only | ✅ LINQ queryable via IAuditLogger | C# ahead | **P2** | Phase 3 |
| Audit integrity verification | ✅ | ✅ | Parity | — | — |
| Audit on template operations | ❌ | ✅ | C# ahead | **P3** | Phase 5 |
| Audit on every service call (central) | ❌ Manual per module | ✅ Service-level integration | C# ahead | **P2** | Phase 3 |

---

## 11. Authentication & Security

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| User login / local auth | ✅ auth.py | ✅ | Parity | — | — |
| JWT token auth (server) | ✅ Flask-JWT-Extended | N/A (desktop WPF) | Python ahead | — | — |
| Role-based access control | ✅ | ✅ | Parity | — | — |
| Password hashing (bcrypt/scrypt) | ✅ password_utils.py | ✅ | Parity | — | — |
| Secure key / encryption manager | ✅ secure_key_manager.py | ✅ Infrastructure encryption | Parity | — | — |
| Rate limiting | ✅ Flask-Limiter | N/A | Python only | — | — |
| Security headers (CSP, HSTS) | ✅ Flask-Talisman | N/A | Python only | — | — |
| CSRF protection | ✅ Flask-WTF | N/A | Python only | — | — |
| Role locking (read-only enforcement) | ✅ ROLE_LOCKING_GUIDE.md | ⚠️ Partial | Python ahead | **P3** | Phase 2 |

---

## 12. Legal Workflow & SLA

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Investigator approval (with date/name) | ✅ legal_workflow_helpers.py | ⚠️ LegalProcessService partial | Python ahead | **P2** | Phase 6 |
| State attorney approval | ✅ | ⚠️ Partial | Python ahead | **P2** | Phase 6 |
| Judicial approval | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| SLA deadline calculation | ✅ | ❌ | Python ahead | **P1** | Phase 6 |
| Overdue process detection | ✅ | ❌ | Python ahead | **P1** | Phase 6 |
| Workflow state machine (send → ack → close) | ✅ | ⚠️ Basic statuses | Python ahead | **P2** | Phase 6 |
| Automatic notification on status change | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Calendar event integration | ✅ | ❌ | Python ahead | **P3** | Phase 6 |
| Legal workflow UI dialogs | ✅ legal_workflow_dialogs.py | ❌ | Python ahead | **P2** | Phase 6 |

---

## 13. Notifications

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Notification system (manager) | ✅ notification_manager.py | ❌ | Python ahead | **P2** | Phase 6 |
| Court date reminders | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Evidence update alerts | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Legal process alerts | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Unread badge count | ✅ | ❌ | Python ahead | **P3** | Phase 6 |
| System tray integration | ✅ | ❌ | Python ahead | **P3** | Phase 6 |
| DB-persisted notifications | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Configurable notification settings | ✅ notification_settings.py | ❌ | Python ahead | **P3** | Phase 6 |
| Notifications panel UI | ✅ notifications_panel.py | ❌ | Python ahead | **P3** | Phase 6 |

---

## 14. Dashboard & Analytics

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Dashboard view (main screen) | ✅ dashboard_bp.py | ✅ DashboardView | Parity | — | — |
| Case status distribution chart | ✅ | ✅ | Parity | — | — |
| Evidence status chart | ✅ | ⚠️ Partial | Python ahead | **P3** | Phase 6 |
| Case load / performance metrics | ✅ | ⚠️ Partial | Python ahead | **P3** | Phase 6 |
| Configurable chart settings | ✅ dashboard_chart_settings.py | ❌ | Python ahead | **P3** | Phase 6 |
| Chart caching (data-hash driven) | ✅ ChartCache in main.py | ❌ | Python ahead | **P3** | Phase 6 |

---

## 15. Archive System

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Archive a case (with reason) | ✅ archive_case_dialog.py | ❌ | Python ahead | **P2** | Phase 6 |
| View archived cases | ✅ archived_cases_dialog.py | ❌ | Python ahead | **P2** | Phase 6 |
| Restore archived case | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Archive search | ✅ | ❌ | Python ahead | **P3** | Phase 6 |
| Archive audit trail | ✅ | ❌ | Python ahead | **P3** | Phase 6 |

---

## 16. Peer Review

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Export report for peer review (.json) | ✅ reports_tab.py | ❌ | Python ahead | **P2** | Phase 6 |
| Import reviewed report | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Change tracking (insert/delete markup) | ✅ peer_review.py | ❌ | Python ahead | **P2** | Phase 6 |
| Inline comments with timestamps | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Sign-off workflow | ✅ | ❌ | Python ahead | **P2** | Phase 6 |
| Review summary display | ✅ | ❌ | Python ahead | **P3** | Phase 6 |
| Portable peer review mode | ✅ peer_review_portable.py | ❌ | Python ahead | **P3** | Phase 6 |
| Server-side peer review API | ✅ peer_review_bp.py | N/A | Python ahead | — | — |

---

## 17. Accessibility & Themes

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Light theme | ✅ accessibility.py | ✅ ThemeService | Parity | — | — |
| Dark theme | ✅ | ⚠️ Basic only | Python ahead | **P3** | Phase 4 |
| High-contrast theme | ✅ | ❌ | Python ahead | **P3** | Phase 4 |
| Per-component stylesheet tokens | ✅ THEME_COLOR_TOKENS | ❌ | Python ahead | **P3** | Phase 4 |
| Theme persistence to config | ✅ | ⚠️ Partial | Python ahead | **P3** | Phase 4 |
| Font scaling options | ✅ | ❌ | Python ahead | **P3** | Phase 4 |
| Configurable keyboard shortcuts | ✅ | ⚠️ Basic | Python ahead | **P3** | Phase 4 |

---

## 18. Testing

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Domain entity unit tests | ❌ | ❌ | Neither | **P1** | Phase 7 |
| Service layer unit tests | ❌ | ❌ | Neither | **P1** | Phase 7 |
| Repository integration tests | ❌ | ❌ | Neither | **P1** | Phase 7 |
| Security / auth tests | ✅ test_security.py | ❌ | Python ahead | **P2** | Phase 7 |
| Date / timezone tests | ✅ test_court_dates.py etc. | ❌ | Python ahead | **P2** | Phase 7 |
| Dashboard tests | ✅ test_dashboard.py | ❌ | Python ahead | **P3** | Phase 7 |
| Archive system tests | ✅ test_archive_system.py | ❌ | Python ahead | **P2** | Phase 7 |
| Performance / load tests | ✅ test_performance_optimization.py | ❌ | Python ahead | **P3** | Phase 7 |
| Validator tests | ✅ tests/test_validators.py | ❌ | Python ahead | **P2** | Phase 7 |

---

## 19. Persistence & Data Layer

| Feature | Python | C# | Gap Direction | Priority | Phase |
|---------|--------|----|---------------|----------|-------|
| Local encrypted SQLite | ✅ database.py | ✅ ForensicDbContext + repositories | Parity | — | — |
| DB schema migrations | ✅ _migration_v1…v8 | ✅ EF Core migrations | Parity | — | — |
| Indexed columns | ✅ DATABASE_INDEX_ANALYSIS.md | ✅ EF Core Fluent API | Parity | — | — |
| Connection resilience / retry | ✅ get_db_connection() | ✅ pool_pre_ping | Parity | — | — |
| Separation of concerns in data access | ❌ All in DatabaseManager | ✅ Separate repositories per entity | C# ahead | **P1** | Phase 3 |
| Remote server proxy mode | ✅ DatabaseManager (server vs local) | N/A (desktop app) | Python only | — | — |
| Dashboard cache (Redis / in-memory) | ✅ | ⚠️ In-memory only | Python ahead | **P3** | — |
| Encrypted BLOB fields | ✅ | ✅ | Parity | — | — |

---

## Summary Counts

| Status | Architecture | Domain | Persistence | Editor | Templates | Legal/Workflow | Notifications | Testing |
|--------|-------------|--------|-------------|--------|-----------|---------------|--------------|---------|
| Parity (both ✅) | 0 | 2 | 5 | 14 | 2 | 2 | 0 | 0 |
| C# ahead | 8 | 8 | 2 | 3 | 10 | 1 | 0 | 0 |
| Python ahead | 0 | 1 | 1 | 7 | 0 | 7 | 9 | 8 |
| Neither has it | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |

**Total P1 gaps (bring Python to C# level):** 14  
**Total P2 gaps:** 28  
**Total Python features to preserve / add to C# (tracked separately):** 32
