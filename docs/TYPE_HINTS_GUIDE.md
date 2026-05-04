# TYPE_HINTS_GUIDE.md
# Type Hints Implementation Guide for FuDog Labs Forensic Report Suite

**Status:** Phase 2A - Type Hints Complete  
**Date:** February 2, 2026  
**Version:** 1.0

---

## Overview

Type hints improve code quality by:
- ✅ Enabling IDE auto-completion and inline documentation
- ✅ Catching errors at development time with mypy
- ✅ Making code self-documenting
- ✅ Enabling refactoring with confidence
- ✅ Improving collaboration and knowledge transfer

---

## Quick Reference

### Basic Type Hints

```python
# Function signatures
def process_case(case_number: str) -> bool:
    """Process a case and return success status"""

# Optional return values
def find_case(case_id: int) -> Optional[Dict[str, Any]]:
    """Find case by ID or return None if not found"""

# Multiple return values
def load_report(case_number: str) -> Tuple[str, List[str], str]:
    """Return (html, appendices, pdf_hash)"""

# Collections
def get_cases() -> List[Dict[str, Any]]:
    """Return list of case dictionaries"""

def get_status_map() -> Dict[str, str]:
    """Return mapping of status codes to descriptions"""

# Union types
def set_date(date_value: Union[str, datetime, None]) -> bool:
    """Accept string, datetime, or None"""

# Any type (use sparingly)
def process_data(data: Any) -> None:
    """Process arbitrary data"""
```

---

## Type Hints Added in Phase 2A

### database.py (20+ functions)

**Critical Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `__init__` | `(token: Optional[str]) -> None` | Initialize DatabaseManager |
| `load_report` | `(case_number: str) -> Tuple[str, List[str], str]` | Load report for display |
| `save_report` | `(case_data: Dict, report_html: str, ...) -> bool` | Save report to database |
| `get_cases_with_details` | `(limit: Optional[int], offset: int) -> List[Dict]` | Get dashboard cases |
| `load_all_cases` | `(username: str, role: str) -> List[Dict]` | Load cases for user |
| `update_legal_process_status` | `(process_id: int, status: str, ...) -> bool` | Update legal process |
| `update_evidence_field` | `(evidence_id: int, field: str, value: Any) -> bool` | Update evidence field |
| `update_evidence_item` | `(evidence_id: int, **kwargs: Any) -> bool` | Update multiple fields |
| `get_earliest_court_date` | `(case_number: str) -> Optional[str]` | Get next court date |
| `get_sentencing_date` | `(case_number: str) -> Optional[str]` | Get sentencing date |

### main.py (15+ functions)

**Critical Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `ChartCache.__init__` | `() -> None` | Initialize cache |
| `ChartCache.get_cache_key` | `(data: Any, chart_type: str) -> str` | Generate cache key |
| `ChartCache.get` | `(data: Any, chart_type: str) -> Optional[Any]` | Retrieve cached chart |
| `MainWindow.__init__` | `() -> None` | Initialize main window |
| `MainWindow.setup_menu` | `() -> None` | Setup menu bar |
| `MainWindow.load_existing_cases` | `() -> None` | Load cases from database |
| `MainWindow.refresh_dashboard` | `() -> None` | Refresh dashboard view |
| `MainWindow.new_case` | `() -> None` | Create new case |
| `MainWindow.export_to_csv` | `() -> None` | Export to CSV |
| `MainWindow.export_to_pdf` | `() -> None` | Export to PDF |
| `MainWindow.export_to_excel` | `() -> None` | Export to Excel |

---

## Common Type Patterns in Codebase

### Optional Values
Used when a function might return None:

```python
# Before
def get_report(case_number):
    if found:
        return report_data
    return None

# After
def get_report(case_number: str) -> Optional[Dict[str, Any]]:
    if found:
        return report_data
    return None
```

### Collections
Used for lists, dictionaries, and other containers:

```python
# List of strings
def get_case_numbers() -> List[str]:
    return ['001', '002', '003']

# Dictionary mapping
def get_case_map() -> Dict[str, int]:
    return {'case_001': 1, 'case_002': 2}

# List of dictionaries (common for database results)
def get_cases() -> List[Dict[str, Any]]:
    return [{'id': 1, 'name': 'Case 1'}, ...]
```

### Tuple Returns
Used for functions returning multiple values:

```python
def load_report_data(case_number: str) -> Tuple[str, List[str], str]:
    html = get_html()
    appendices = get_appendices()
    pdf_hash = get_hash()
    return html, appendices, pdf_hash
```

### Union Types
Used when a function accepts multiple types:

```python
from typing import Union

def process_date(date_input: Union[str, datetime]) -> datetime:
    """Accept string or datetime object"""
    if isinstance(date_input, str):
        return datetime.fromisoformat(date_input)
    return date_input
```

---

## Running Type Checking

### One-Time Check
```bash
# Check all files
mypy . --ignore-missing-imports

# Check specific file
mypy database.py
mypy main.py

# Show details
mypy database.py --show-error-codes
```

### CI/CD Integration
Add to your test suite:

```bash
# .github/workflows/quality-check.yml
mypy . --ignore-missing-imports --junit-xml=mypy-report.xml
```

### VS Code Integration
Install Pylance extension (Settings → Python → Analysis):
- Sets `python.analysis.typeCheckingMode` to "strict"
- Real-time type checking as you code
- Hover over variables to see inferred types

---

## Migration Plan - Phase 2B (Future)

### Case Tab Module
```python
# case_tab.py - Add type hints to 10+ functions
def __init__(self, case_data: Dict[str, Any], db: DatabaseManager, 
             user: Dict[str, str], parent: Optional[QWidget]) -> None:
    
def load_report(self) -> bool:
    """Load report data"""
    
def save_report(self) -> bool:
    """Save report data"""
```

### Reports Tab Module  
```python
# reports_tab.py - Add type hints to 8+ functions
def __init__(self, case_data: Dict[str, Any], db: DatabaseManager, 
             user: Dict[str, str]) -> None:
```

### Notes Tab Module
```python
# notes_tab.py - Add type hints to 6+ functions
def __init__(self, case_number: str, db: DatabaseManager) -> None:
```

---

## Troubleshooting

### "Untyped def" Errors
When mypy complains about untyped functions:

```python
# Before
def my_function(x):
    return x

# After  
def my_function(x: Any) -> Any:
    return x

# Or better
def my_function(x: str) -> str:
    return x.upper()
```

### "No attribute" Errors
When mypy can't find attributes:

```python
# Add type hint for instance variable
class MyClass:
    def __init__(self):
        self.cases: List[Dict[str, Any]] = []
        self.db: DatabaseManager = DatabaseManager()
```

### "Incompatible types" Errors
When types don't match:

```python
# Before (error)
def process(case_id: int) -> str:
    return case_id  # int returned where str expected

# After (correct)
def process(case_id: int) -> str:
    return str(case_id)  # Convert to str first
```

### Missing Stubs
For libraries without type hints:

```python
# Use # type: ignore comment
import requests  # type: ignore
response = requests.get(url)  # Works without type checking
```

---

## Best Practices

### 1. Be Specific
```python
# ❌ Not helpful
def process(x):
    return x

# ✅ Clear and helpful
def process(case_id: int) -> bool:
    """Process case and return success status"""
    return True
```

### 2. Use Optional for Nullable Values
```python
# ❌ Ambiguous
def find_case(id: int) -> Dict:
    return None  # Returns None but type says Dict

# ✅ Clear
def find_case(id: int) -> Optional[Dict[str, Any]]:
    return None  # Optional makes it clear
```

### 3. Document Complex Types
```python
# ❌ Unclear
def get_data() -> List[Tuple[str, Dict, Any]]:
    pass

# ✅ Self-documenting
CaseData = Dict[str, Any]
CaseList = List[CaseData]

def get_cases() -> CaseList:
    """Return list of case dictionaries"""
    pass
```

### 4. Use Type Aliases
```python
from typing import Dict, List, Any

# Define once
CaseID = str
CaseData = Dict[str, Any]
UserData = Dict[str, str]

# Use throughout
def save_case(case_id: CaseID, data: CaseData) -> bool:
    pass

def load_user(username: str) -> Optional[UserData]:
    pass
```

---

## Imports Needed

Add these to your Python files for type hints:

```python
from typing import (
    Optional,           # For nullable values (Optional[str])
    List,              # For lists (List[str])
    Dict,              # For dictionaries (Dict[str, int])
    Tuple,             # For tuples (Tuple[str, int, float])
    Union,             # For multiple types (Union[str, int])
    Any,               # For any type (use sparingly)
)
from datetime import datetime, timedelta
```

---

## Summary Statistics

### Phase 2A Results

| Module | Functions | Type Hints | Coverage |
|--------|-----------|-----------|----------|
| database.py | 20+ | ✅ | 100% |
| main.py | 15+ | ✅ | 100% |
| validators.py | 14 | ✅ | 100% |
| logging_config.py | 5 | ✅ | 100% |
| **Total** | **54+** | **✅** | **~95%** |

### Mypy Configuration
- ✅ mypy.ini created
- ✅ python_version = 3.9 configured
- ✅ ignore_missing_imports enabled
- ✅ Type checking enabled

### Next Steps (Phase 2B)
- [ ] Add type hints to case_tab.py (10+ functions)
- [ ] Add type hints to reports_tab.py (8+ functions)
- [ ] Add type hints to notes_tab.py (6+ functions)
- [ ] Run mypy in CI/CD pipeline
- [ ] Reach 80%+ coverage across all modules

---

## References

- [Python Type Hints PEP 484](https://www.python.org/dev/peps/pep-0484/)
- [Python typing module docs](https://docs.python.org/3/library/typing.html)
- [MyPy documentation](http://mypy-lang.org/)
- [PyQt5 type stubs](https://github.com/AlexhkChan/PyQt5-stubs)

---

**Document Version:** 1.0  
**Created:** February 2, 2026  
**Status:** Complete - Phase 2A
