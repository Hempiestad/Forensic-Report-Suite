# FuDog Labs Forensic Report Suite - Codebase Structure and Interactions

## Overview
This document outlines the structural hierarchy of the codebase and how the various components interact with each other. The application is built using PyQt5 for the GUI and SQLite for local data storage, with optional server mode support.

## Core Architecture

### Entry Point
- **main.py**: Application entry point
  - Initializes QApplication
  - Handles authentication (local or AD/server)
  - Creates MainWindow instance
  - Manages application lifecycle

### Main Components

#### 1. MainWindow (main.py)
**Purpose**: Main application window managing the overall UI and case management.

**Key Responsibilities**:
- Dashboard display with case overview
- Menu bar with File, Tools, View options
- Tab widget for case tabs and dashboard
- User view switching (Investigator/Examiner)
- Export functionality (CSV, PDF, Excel)
- Theme management

**Interactions**:
- Creates DatabaseManager instance
- Instantiates CaseTab for each case
- Manages ThemeManager for UI theming
- Handles authentication results

#### 2. CaseTab (case_tab.py)
**Purpose**: Individual case management interface.

**Key Responsibilities**:
- Case-specific dashboard with metrics
- Sub-tabs for Evidence, Legal Processes, Lead Tracker
- Workflow buttons (Submit, Approve, Reject, Close)
- Integration with Notes and Reports windows
- Audit logging for case activities

**Interactions**:
- Uses DatabaseManager for data operations
- Creates NotesWindow and ReportsWindow
- Manages AuditLogger for activity tracking
- Communicates with MainWindow for dashboard refresh

#### 3. NotesWindow (notes_tab.py)
**Purpose**: Dedicated notes editing interface.

**Key Responsibilities**:
- Rich text editing with formatting toolbar
- Dropdown menus for grouped actions (Style, Color, Alignment, Lists, Indent)
- Save/load functionality
- Integration with audit logging

**Interactions**:
- Uses DatabaseManager for persistence
- Reports to AuditLogger for changes
- Called from CaseTab

#### 4. ReportsWindow (reports_tab.py)
**Purpose**: Report writing and editing interface.

**Key Responsibilities**:
- Rich text editing with formatting toolbar
- Template loading
- PDF export with hashing
- Peer review functionality
- Glossary assistance

**Interactions**:
- Uses DatabaseManager for report storage
- Integrates with TemplateManager
- Manages PeerReview and GlossaryAssist modules
- Reports to AuditLogger

#### 5. DatabaseManager (database.py)
**Purpose**: Data persistence layer.

**Key Responsibilities**:
- SQLite database management
- CRUD operations for cases, evidence, legal processes, leads
- Report storage and retrieval
- User management and authentication
- Case workflow state management

**Interactions**:
- Used by all UI components for data access
- Supports both local SQLite and server modes
- Provides data to dashboard and tables

## Supporting Modules

### UI Components
- **accessibility.py**: ThemeManager for UI theming (light/dark/high contrast)
- **status_color_dialog.py**: Custom status color configuration
- **glossary.py**: SWGDE glossary search dialog
- **glossary_assist.py**: In-editor glossary assistance

### Business Logic
- **audit_log.py**: Activity logging and audit trails
- **peer_review.py**: Peer review workflow management
- **templates.py**: Report template management
- **secure_key_manager.py**: Encryption key management
- **security.py**: Security utilities (hashing, encryption)

### Authentication & Configuration
- **auth.py**: Authentication handling (local/AD/server)
- **config.json**: Application configuration

## Data Flow

### Case Creation Flow
1. User selects "New Case" from MainWindow menu
2. MainWindow shows case creation dialog
3. DatabaseManager saves case data
4. MainWindow creates CaseTab instance
5. CaseTab loads case data and initializes UI

### Report Writing Flow
1. User opens case tab
2. Clicks "Open Reports" button
3. ReportsWindow loads existing report from DatabaseManager
4. User edits report with formatting tools
5. Changes auto-save or manual save to DatabaseManager
6. AuditLogger records changes

### Evidence Management Flow
1. User adds evidence via CaseTab dialog
2. DatabaseManager stores evidence data
3. CaseTab refreshes evidence table
4. MainWindow dashboard updates metrics
5. AuditLogger records addition

## Dependencies

### External Libraries
- PyQt5: GUI framework
- pandas: Data manipulation for exports
- matplotlib: Chart generation
- weasyprint: PDF generation
- sqlite3: Database (built-in)
- Optional: language_tool_python, enchant, html2text

### Internal Dependencies
- All UI components depend on DatabaseManager
- Audit logging integrated across all data-changing operations
- Theme management affects all UI elements
- Security module used for encryption and hashing

## Error Handling
- Database operations include try/catch blocks
- UI operations show QMessageBox for errors
- Optional dependencies gracefully degrade functionality
- Authentication failures prevent application startup

## Testing
- Unit tests in test_*.py files
- Focus on database operations and UI interactions
- Chart generation and export functionality tested

This structure ensures modular, maintainable code with clear separation of concerns and comprehensive audit trails for forensic accountability.
