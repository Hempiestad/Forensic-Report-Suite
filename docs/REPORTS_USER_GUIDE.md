# Reports Tab User Guide — FuDog Labs Forensic Report Suite

## Overview

The Reports Tab is a powerful document creation and management tool within the Forensic Suite application. It provides advanced rich text editing, timestamp management, appendices handling, PDF generation with integrity verification, peer review capabilities, and seamless integration with case evidence and notes.

## Getting Started

### Opening the Reports Tab

The Reports Tab is accessible within each case file. To open reports for a specific case:

1. Open a case in the main application
2. Navigate to the Reports section
3. The reports interface will display with a rich text editor and formatting toolbar

### Interface Layout

- **Report Editor**: Central rich text editor supporting HTML formatting
- **Formatting Toolbar**: Quick access to text formatting, colors, alignment, and lists
- **Status Bar**: Shows PDF hash information and editor statistics
- **Menu Bar**: File, Edit, Insert, Format, and Appendices operations
- **Hash Display**: Shows SHA-256 hash of the final PDF for integrity verification

## Basic Report Operations

### Creating and Editing Reports

- Reports are automatically loaded when opening the Reports Tab
- Type directly in the editor - content supports rich HTML formatting
- Changes are tracked and can be saved manually or automatically

### Saving Reports

Reports are saved when:
- You manually save via **File → Save**
- The application closes (auto-save on closeEvent)
- You export or finalize the report

### PDF Export and Finalization

#### Export PDF
1. **File → Export PDF** or `Ctrl+E`
2. Choose save location for the PDF file
3. The report is converted to PDF using WeasyPrint
4. SHA-256 hash is computed and displayed

#### Finalize Report
1. **File → Finalize Report**
2. Exports PDF and saves the report data to the database
3. Includes appendices and hash verification
4. Audit trail is updated with finalization details

**Requirements**: WeasyPrint library must be installed for PDF generation

## Text Formatting

### Basic Formatting

- **Bold**: Toolbar Style dropdown or `Ctrl+B` (not directly available, use toolbar)
- **Italic**: Toolbar Style dropdown
- **Underline**: Toolbar Style dropdown
- **Strikethrough**: Toolbar Style dropdown → Strikethrough
- **Subscript/Superscript**: Toolbar Style dropdown

### Font and Size

- **Font Family**: Select from the font dropdown in the toolbar
- **Font Size**: Choose from the size dropdown (8pt to 72pt)
- **Advanced Font Settings**: **Format → Font...** for complete font control

### Colors

- **Text Color**: **Format → Text Color...** or Color dropdown
- **Background Color**: **Format → Background Color...** or Color dropdown

### Alignment

- **Left Align**: Default alignment
- **Center**: **Format → Align Center** or Alignment dropdown
- **Right Align**: **Format → Align Right** or Alignment dropdown
- **Justify**: **Format → Justify** or Alignment dropdown

### Lists

- **Bullet Lists**: **Format → Lists → Bullet List** or Lists dropdown
- **Numbered Lists**: **Format → Lists → Numbered List** or Lists dropdown

### Indentation

- **Increase Indent**: **Format → Indent → Increase Indent** or Indent dropdown
- **Decrease Indent**: **Format → Indent → Decrease Indent** or Indent dropdown

## Timestamp Management

### Inserting Timestamps

- **Local Format**: **Insert → Timestamps → Insert Date/Time (Local)** or `Ctrl+Shift+T`
  - Format: `YYYY-MM-DD HH:MM:SS`
- **ISO Format**: **Insert → Timestamps → Insert ISO Date/Time (with TZ)** or `Ctrl+Alt+Shift+T`
  - Format: `YYYY-MM-DDTHH:MM:SS±HH:MM`

### Converting Timestamps

1. Select a timestamp in the text
2. **Insert → Timestamps → Convert Selected Timestamp** or `Ctrl+Shift+C`
3. Choose target timezone from the dialog
4. Select output format (ISO 8601 or Readable)
5. The timestamp will be converted and replaced

**Supported Timezones**: UTC, System Local, America/New_York, America/Chicago, America/Denver, America/Los_Angeles

**Supported Abbreviations**: PST, PDT, MST, MDT, CST, CDT, EST, EDT, AKST, AKDT, HST, UTC, GMT

## Templates

### Loading Templates

1. Right-click in editor → **Insert Template**
2. Select from available templates
3. Content is inserted at cursor position

### NIST Template

1. **File → Load NIST Template**
2. Pre-built SWGDE/NIST standard template loads
3. Evidence table is automatically populated from case data
4. Placeholders are replaced with case information

### Import from DOCX

1. **File → Import Template from DOCX**
2. Select a Microsoft Word (.docx) file
3. Content is converted to HTML and loaded
4. Basic formatting (bold, italic, underline) is preserved
5. Tables are converted to HTML tables

**Requirements**: python-docx library for DOCX import

### Legal Template Library Integration

The report writer is used as the editor for legal-process templates.

Workflow:

1. Open **Tools → Legal Template Library** from the main application.
2. Select a template and choose **Open in Report Writer**.
3. Edit, validate, and save updates.
4. Reuse finalized content in active case reports.

Sharing and portability options:

- Share a single template
- Share an entire folder scope (vendor or vendor + type)
- Share your full library
- Import/export template libraries between machines

## Appendices Management

### Adding Appendices

1. **Appendices → Add Appendix**
2. Select any file type from your computer
3. File is copied to `cases/{case_number}/appendices/`
4. SHA-256 hash is computed for integrity
5. File path is validated to prevent directory traversal

### Viewing Appendices

1. **Appendices → View Appendices**
2. Dialog shows list of all attached files
3. File names are displayed (not opened)

### Removing Appendices

1. **Appendices → Remove Appendix**
2. Select appendix from list
3. Confirm removal
4. File is removed from appendices list and audit logged

## Peer Review System

### Exporting for Peer Review

1. **File → Export for Peer Review**
2. Report data is saved as JSON file (.peerreview.json)
3. Includes: case info, HTML content, appendices, PDF hash, export metadata
4. File can be shared with peer reviewers

### Importing Peer Review

1. **File → Import Peer Review**
2. Select reviewed JSON file (.reviewed.json)
3. Review summary is displayed
4. Shows reviewer information, comments count, and summary
5. Import is logged in audit trail

## Insert Features

### Images

1. **Insert → Image**
2. Select image file (PNG, JPG, JPEG, BMP, GIF)
3. Image is embedded in the report HTML

### Tables

1. **Insert → Table**
2. Advanced table insertion using word processor
3. Configurable table properties

### Page Breaks

1. **Insert → Page Break**
2. Inserts HTML page break for PDF/printing formatting

### Notes from Notes Tab

1. **Insert → Note from Notes Tab**
2. Select from available notes for the current case
3. Note content is inserted at cursor position
4. Selection includes note name and timestamp

## Context Menu Features

Right-click in the report editor to access:

- **Insert Date/Time (Local)**: Quick local timestamp insertion
- **Insert ISO Date/Time (with TZ)**: Quick ISO timestamp insertion
- **Convert Selected Timestamp**: Convert highlighted timestamps
- **Insert Template**: Insert predefined templates
- **Validate Section**: Basic validation (checks for case number)
- **Export Selection as PDF**: Export selected text as HTML file
- **Embed Evidence Reference**: Insert evidence links (#evidence:ID)

## Evidence Integration

### Automatic Evidence Table

When loading NIST template, the system:
- Retrieves evidence details from case database
- Builds HTML table with: Item ID, Description, Make/Model, Serial/IMEI, Hash
- Populates template with actual case evidence
- Includes empty row for manual additions

### Evidence References

1. Right-click → **Embed Evidence Reference**
2. Enter evidence ID or filename
3. HTML link is inserted: `<a href='#evidence:ID'>Evidence: ID</a>`

## Export and Integration

### Export Selection

1. Select text in the editor
2. Right-click → **Export Selection as PDF**
3. Save as HTML file (note: menu says PDF but exports HTML)

### Integration with Notes

- Notes can be inserted directly into reports
- Maintains connection between notes and final report
- Audit trail tracks note insertions
- Legal templates can be refined in Reports and saved back to the template library

## Find and Replace

### Using Find/Replace

1. **Edit → Find and Replace** or `Ctrl+F`
2. Enter search term and replacement text
3. Navigate through matches
4. Replace individual or all occurrences

## Configuration

### Context Menu Settings

Control context menu availability via `config.json`:

```json
{
  "context_menu": {
    "reports": {
      "insert_timestamp": true,
      "convert_timestamp": true,
      "insert_template": true,
      "validate_section": true,
      "export_pdf": true,
      "embed_evidence": true
    }
  }
}
```

### Timezone Configuration

Set preferred timezone in `config.json`:

```json
{
  "timezone": "America/New_York"
}
```

## Keyboard Shortcuts

### File Operations
- `Ctrl+S`: Save Report
- `Ctrl+E`: Export PDF
- `Ctrl+W`: Close Window

### Editing
- `Ctrl+Z`: Undo
- `Ctrl+Y`: Redo
- `Ctrl+X`: Cut
- `Ctrl+C`: Copy
- `Ctrl+V`: Paste

### Timestamps
- `Ctrl+Shift+T`: Insert Local Timestamp
- `Ctrl+Alt+Shift+T`: Insert ISO Timestamp
- `Ctrl+Shift+C`: Convert Selected Timestamp

### Tools
- `Ctrl+F`: Find and Replace

## Data Storage and Security

### File Structure

Reports are stored in the case directory:
```
cases/{case_number}/
├── report.pdf              # Exported PDF
├── appendices/             # Attached files
│   └── [appendix files]
└── [database storage]      # HTML content, appendices list, PDF hash
```

### Data Integrity

- PDF files include SHA-256 hashes for verification
- All changes logged in audit trail
- Appendix files hashed for integrity checking
- Path validation prevents directory traversal attacks

### Security Features

- Secure file handling for appendices
- Audit logging for all operations
- Hash verification for exported PDFs
- Path traversal protection

## Troubleshooting

### PDF Export Issues

**WeasyPrint Not Available**
- Install with: `pip install weasyprint`
- May require additional system dependencies

**PDF Generation Fails**
- Check HTML content for validity
- Ensure sufficient disk space
- Verify file permissions

### Template Loading Issues

**NIST Template Not Found**
- Check templates.py file exists
- Verify DEFAULT_TEMPLATES contains SWGDE/NIST entry

**DOCX Import Fails**
- Install python-docx: `pip install python-docx`
- Ensure file is valid .docx format

### Timestamp Conversion Issues

**Timezone Detection Fails**
- Ensure timestamp includes recognizable timezone abbreviation
- Check config.json for timezone setting
- Verify dateutil and zoneinfo availability

### Performance Considerations

- Large appendices may slow loading
- Complex HTML may increase PDF generation time
- Regular saving prevents data loss
- Hash computation may take time for large PDFs

## Integration with Case Management

### Case Data Integration

- Case number automatically populated in templates
- Evidence details pulled from case database
- Appendices stored within case directory structure
- All operations logged with case number reference

## Related Documentation

- [README](README.md) — Project overview and quick start
- [Main Application User Guide](MAIN_USER_GUIDE.md) — Dashboard, menus, and case management
- [Notes Tab User Guide](NOTES_USER_GUIDE.md) — Case note-taking
- [Legal Workflow Guide](LEGAL_WORKFLOW_GUIDE.md) — Legal process approval stages
- [Server User Guide](SERVER_USER_GUIDE.md) — Server API and authentication


---

This guide covers all major features of the Reports Tab. The Reports Tab provides a complete solution for creating, formatting, and managing forensic reports with professional PDF output and peer review capabilities. For additional support or feature requests, please refer to the main application documentation or contact your system administrator.
