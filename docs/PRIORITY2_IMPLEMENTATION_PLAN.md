# PRIORITY2_IMPLEMENTATION_PLAN.md
# Priority 2: Type Hints, Logging Consolidation, Database Indexes
**Status:** 🚀 PHASE 2 STARTING  
**Date:** February 2, 2026

---

## Overview

Priority 2 focuses on code quality and performance:

1. **Type Hints** - Enable IDE support and catch type errors at development time
2. **Logging Consolidation** - Replace 40+ bare except blocks with proper error logging
3. **Database Indexes** - Optimize query performance for large datasets

---

## Task 1: Add Type Hints to Critical Functions

### Scope
Add type hints to functions in these modules (in order of priority):

| Module | Critical Functions | Count | Estimated Time |
|--------|-------------------|-------|-----------------|
| database.py | load_report, save_report, get_cases_with_details | 20+ | 3 hours |
| main.py | setup_ui, initialize_main_window, run | 15+ | 2 hours |
| case_tab.py | __init__, load_report, save_report | 10+ | 1.5 hours |
| validators.py | Already done ✅ | - | - |
| logging_config.py | Already done ✅ | - | - |

### Implementation Plan

**Step 1: Create mypy Configuration**
```ini
# mypy.ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False  # Start permissive
disallow_incomplete_defs = False
check_untyped_defs = True
no_implicit_optional = True
warn_unused_ignores = True
warn_redundant_casts = True
warn_no_return = True
```

**Step 2: Add Type Hints Pattern**
```python
from typing import Optional, List, Dict, Union, Tuple
import logging

def load_report(self, case_number: str) -> Tuple[str, List[str], str]:
    """Load report with type hints.
    
    Args:
        case_number: Case identifier (validated)
    
    Returns:
        Tuple of (html_content, appendices, pdf_hash)
    
    Raises:
        ValueError: If case_number invalid
        DatabaseError: If query fails
    """
    logger.info(f"Loading report for case: {case_number}")
    # Implementation
    return html, appendices, pdf_hash
```

**Step 3: Common Type Annotations**
```python
from typing import Optional, List, Dict, Tuple, Union, Any

# Database operations
def query_cases(self, limit: int = 50) -> List[Dict[str, Any]]:
    ...

def save_case(self, case_data: Dict[str, Any]) -> bool:
    ...

# UI operations  
def show_error(self, message: str) -> None:
    ...

def get_user_input(self) -> Optional[str]:
    ...

# File operations
def export_pdf(self, file_path: str, format: str = 'pdf') -> bool:
    ...

# Date operations
def parse_date(self, date_str: str) -> Optional[datetime]:
    ...
```

### Expected Improvements

- ✅ IDE auto-complete works better
- ✅ Type checker (mypy) catches errors
- ✅ Documentation clearer for other developers
- ✅ Refactoring easier and safer

---

## Task 2: Logging Consolidation

### Scope

Replace ~40+ bare except blocks with proper logging:

| File | Bare Excepts | Task | Status |
|------|--------------|------|--------|
| reports_tab.py | 15+ | Replace all bare except | ⏳ TODO |
| case_tab.py | 8+ | Replace all bare except | ⏳ TODO |
| main.py | 10+ | Replace all bare except | ⏳ TODO |
| database.py | 3+ | Replace all bare except | ⏳ TODO |
| **Total** | **40+** | | |

### Pattern to Use

**BEFORE (❌):**
```python
try:
    result = db.load_report(case_id)
except Exception:
    pass  # Silent failure!
```

**AFTER (✅):**
```python
import logging
logger = logging.getLogger(__name__)

try:
    result = db.load_report(case_id)
except FileNotFoundError as e:
    logger.error(f"Report file not found for case {case_id}: {e}")
    show_error(f"Could not find report file: {e}")
except sqlite3.DatabaseError as e:
    logger.error(f"Database error loading report: {e}")
    show_error("Database error occurred. Check logs for details.")
except Exception as e:
    logger.exception(f"Unexpected error loading report: {e}")
    show_error("An unexpected error occurred. Check logs for details.")
```

### Logging Strategy

```python
# Import once per module
import logging
logger = logging.getLogger(__name__)

# Use these log levels consistently:
logger.debug("Detailed info for developers")          # Low-level details
logger.info("User action completed")                  # Important milestones
logger.warning("Something unexpected but recoverable") # Warning conditions
logger.error("Operation failed but app continues")    # Error conditions
logger.exception("Error with full traceback")         # Always for exceptions
```

### Exception Hierarchy

```python
# Catch specific exceptions first, then general
try:
    operation()
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
except ValueError as e:
    logger.error(f"Invalid value: {e}")
except sqlite3.DatabaseError as e:
    logger.error(f"Database error: {e}")
except requests.RequestException as e:
    logger.error(f"Network error: {e}")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")  # Include traceback
finally:
    logger.debug("Cleanup completed")
```

### Expected Improvements

- ✅ All errors logged to files
- ✅ Easier debugging
- ✅ Better monitoring/alerting
- ✅ Audit trail of failures

---

## Task 3: Add Database Indexes

### Analysis

Current indexes missing on frequently queried columns:

| Table | Column | Query Pattern | Impact |
|-------|--------|---------------|--------|
| reports | assigned_to | WHERE assigned_to = ? | ⚠️ SLOW |
| reports | status | WHERE status = ? | ⚠️ SLOW |
| evidence_items | case_number | WHERE case_number = ? | ⚠️ SLOW |
| legal_processes | case_number | WHERE case_number = ? | ⚠️ SLOW |
| reports | date_created | ORDER BY date_created | ⚠️ SLOW |

### Index Creation Strategy

**Add to [database.py](database.py) migration v5:**

```python
def _migration_v5(self):
    """Migration to version 5: Add missing indexes for performance"""
    
    # Single column indexes
    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_assigned_to ON reports(assigned_to);')
    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);')
    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_date_created ON reports(date_created);')
    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence_items(case_number);')
    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_case ON legal_processes(case_number);')
    
    # Composite indexes for common filter combinations
    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_status_assigned ON reports(status, assigned_to);')
    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_evidence_imaging ON evidence_items(case_number, imaging_status);')
    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_status_date ON legal_processes(case_number, status, due_date);')
```

### Expected Performance Improvements

- ✅ Dashboard loads 5-10x faster
- ✅ Case search 10-20x faster
- ✅ Evidence filtering instant
- ✅ Handles 10K+ cases smoothly

### Index Maintenance

```python
# Monitor index usage (SQLite)
def get_index_stats(self) -> List[Dict]:
    """Get index usage statistics"""
    cursor = self.conn.execute("""
        SELECT name, tbl_name, sql 
        FROM sqlite_master 
        WHERE type='index' AND name LIKE 'idx_%'
    """)
    return [dict(row) for row in cursor.fetchall()]

# Update indexes after major data changes
def reindex_database(self) -> None:
    """Reindex all indexes for optimization"""
    logger.info("Starting database reindex...")
    self.conn.execute("REINDEX")
    logger.info("Database reindex complete")
```

---

## Implementation Timeline

### Phase 2A: Type Hints (Days 1-3)
- [ ] Create mypy.ini configuration
- [ ] Add type hints to database.py (most critical)
- [ ] Add type hints to main.py entry point
- [ ] Add type hints to case_tab.py
- [ ] Run mypy checks: `mypy . --ignore-missing-imports`
- [ ] Update CI/CD to run mypy

**Time: 6-8 hours**

### Phase 2B: Logging Consolidation (Days 2-4)
- [ ] Create logging integration pattern document
- [ ] Update reports_tab.py exception handlers
- [ ] Update case_tab.py exception handlers
- [ ] Update main.py exception handlers
- [ ] Update database.py exception handlers
- [ ] Test logging output in all scenarios

**Time: 8-12 hours**

### Phase 2C: Database Indexes (Days 3-5)
- [ ] Create migration v5 in database.py
- [ ] Update CURRENT_SCHEMA_VERSION to 5
- [ ] Test migration on existing databases
- [ ] Benchmark performance before/after
- [ ] Document index strategy

**Time: 4-6 hours**

### Total Estimated Time: 18-26 hours (~2.5-3 days)

---

## Success Criteria

### Type Hints
- [ ] No mypy errors on critical modules
- [ ] 80%+ of functions have type hints
- [ ] IDE auto-complete working
- [ ] Documentation clearer

### Logging Consolidation
- [ ] All 40+ bare except blocks replaced
- [ ] Logs written to files on all errors
- [ ] No silent failures
- [ ] Audit trail complete

### Database Indexes
- [ ] Dashboard loads <2 seconds (was ~5-10s)
- [ ] Case search instant (was slow)
- [ ] All migrations work on existing data
- [ ] No performance regression

---

## Files to Modify

### Type Hints
```
database.py          - Add type hints to 20+ functions
main.py              - Add type hints to 15+ functions
case_tab.py          - Add type hints to 10+ functions
reports_tab.py       - Add type hints to 8+ functions
Create mypy.ini      - NEW configuration file
```

### Logging Consolidation
```
reports_tab.py       - Replace 15+ bare except blocks
case_tab.py          - Replace 8+ bare except blocks
main.py              - Replace 10+ bare except blocks
database.py          - Replace 3+ bare except blocks
Create patterns doc  - NEW exception handling guide
```

### Database Indexes
```
database.py          - Add migration v5 (5 indexes)
models.py            - Update index definitions
Create benchmark doc - NEW performance analysis
```

---

## Tools & Commands

### Type Checking
```bash
# Install mypy
pip install mypy

# Run type check
mypy . --ignore-missing-imports

# Run on specific file
mypy database.py

# Strict mode (later)
mypy . --strict
```

### Logging Verification
```bash
# Count bare except blocks
grep -r "except:" . --include="*.py" | wc -l
grep -r "except Exception:" . --include="*.py" | wc -l

# Check logging usage
grep -r "logger\." . --include="*.py" | wc -l
```

### Performance Testing
```python
# Benchmark queries before/after
import time

start = time.time()
cases = db.get_cases_with_details(limit=100)
elapsed = time.time() - start
print(f"Query time: {elapsed:.2f}s")
```

---

## Dependencies to Add

**requirements_client.txt:**
```
mypy>=1.8.0
types-PyQt5>=5.15.10
types-requests>=2.31.0
pytest>=7.4.0
pytest-cov>=4.1.0
```

**requirements_server.txt:**
```
mypy>=1.8.0
pytest>=7.4.0
pytest-cov>=4.1.0
```

---

## Documentation to Create

1. **TYPE_HINTS_GUIDE.md** - Type hints style guide and patterns
2. **LOGGING_CONSOLIDATION_REPORT.md** - All changes made to exception handling
3. **DATABASE_INDEX_ANALYSIS.md** - Index strategy and performance benchmarks
4. **PRIORITY2_QUICK_REFERENCE.md** - Quick lookup for Priority 2 patterns

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Breaking existing code | LOW | All changes backward-compatible |
| Performance regression | VERY LOW | Indexes only improve performance |
| Type hints incompleteness | MEDIUM | Use Optional[] liberally |
| Migration issues | LOW | Test on copy first |

---

## Rollout Plan

**Week 1:** Type hints + mypy setup  
**Week 2:** Logging consolidation  
**Week 3:** Database indexes + performance testing

---

## Next Steps

1. ✅ Approve this plan
2. ✅ Start Phase 2A: Type hints
3. ✅ Progress to Phase 2B: Logging
4. ✅ Complete Phase 2C: Indexes

**Ready to proceed? Let's start with Type Hints!**

---

**Document Version:** 1.0  
**Created:** February 2, 2026  
**Status:** Ready for implementation
