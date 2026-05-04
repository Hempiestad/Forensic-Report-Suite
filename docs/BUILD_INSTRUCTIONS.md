# Build Instructions - FuDog Labs Forensic Report Suite

## Overview

This guide provides step-by-step instructions for compiling the Forensic Report Suite into standalone executables for distribution and alpha testing.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Build Checklist](#pre-build-checklist)
3. [Building the Application](#building-the-application)
4. [Post-Build Verification](#post-build-verification)
5. [Troubleshooting](#troubleshooting)
6. [Distribution](#distribution)

---

## Prerequisites

### Required Software

- **Python 3.8 or higher** (Download from [python.org](https://www.python.org/downloads/))
- **PyInstaller 6.0+** (Installed via pip)
- **Git** (Optional, for version control)
- **PowerShell 5.1+** (Windows) or Bash (Linux/macOS)

### System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Ubuntu 18.04+
- **RAM**: Minimum 8GB (16GB recommended for build process)
- **Disk Space**: 2GB free space for build artifacts
- **Visual C++ Build Tools** (Windows only, for some Python packages)

### Install PyInstaller

```powershell
pip install pyinstaller
```

---

## Pre-Build Checklist

### 1. Install Dependencies

Ensure all required Python packages are installed:

```powershell
# Install all dependencies
pip install -r requirements.txt

# Verify critical packages
pip show PyQt5 pandas weasyprint openpyxl cryptography
```

### 2. Verify Critical Files

Ensure these files exist in your project directory:

**Required for Client Build:**
- ✓ `main.py` - Main application entry point
- ✓ `config.json` - Configuration file
- ✓ `database.py` - Database management
- ✓ `ForensicReportWriter.spec` - PyInstaller specification
- ✓ `forensic_client.ico` - Application icon
- ✓ All user guides (*.md files)
- ✓ All module files (case_tab.py, notes_tab.py, etc.)

**Required for Server Build:**
- ✓ `server.py` - Server application
- ✓ `ForensicCaseServer.spec` - Server PyInstaller spec
- ✓ `forensic_server.ico` - Server icon

### 3. Configuration Check

Review `config.json` for default settings:

```json
{
    "use_ad": false,
    "server_url": "",
    "ad_server": "",
    "status_colors": { ... },
    "notifications": { ... }
}
```

### 4. Run Tests (Recommended)

```powershell
# Install pytest if not already installed
pip install pytest

# Run test suite
pytest tests/ -v
```

### 5. Check Icon Files

Ensure icon files exist:
- `forensic_client.ico` (256x256 or 128x128 recommended)
- `forensic_server.ico` (for server builds)

If missing, create placeholder icons or PyInstaller will use defaults.

---

## Building the Application

### Option 1: Automated Build Script (Recommended)

Use the provided PowerShell build script with comprehensive pre-checks:

#### Build Client Only
```powershell
.\build.ps1 -Client
```

#### Build Server Only
```powershell
.\build.ps1 -Server
```

#### Build Both Client and Server
```powershell
.\build.ps1 -Both
```

#### Clean Build (Remove Previous Build Artifacts)
```powershell
.\build.ps1 -Client -Clean
```

#### Skip Tests (Faster Build)
```powershell
.\build.ps1 -Client -SkipTests
```

### Option 2: Manual Build Process

#### Build Client Application

```powershell
# Clean previous builds (optional)
Remove-Item -Recurse -Force build, dist

# Build the client
pyinstaller ForensicReportWriter.spec --clean --noconfirm
```

#### Build Server Application

```powershell
# Build the server
pyinstaller ForensicCaseServer.spec --clean --noconfirm
```

### Build Process Overview

The build process typically takes 3-10 minutes depending on your system:

1. **Analysis Phase**: PyInstaller analyzes dependencies
2. **Collection Phase**: Gathers all required modules and libraries
3. **Packaging Phase**: Bundles everything into executable
4. **Compression Phase**: Applies UPX compression (if available)

---

## Post-Build Verification

### 1. Check Build Output

After successful build, verify the following structure:

```
dist/
├── ForensicReportWriter/
│   ├── ForensicReportWriter.exe (Windows) or ForensicReportWriter (Linux/Mac)
│   ├── config.json
│   ├── *.md (documentation files)
│   └── [various DLL files and dependencies]
└── ForensicCaseServer/ (if server was built)
    ├── ForensicCaseServer.exe
    └── [dependencies]
```

### 2. Test the Executable

#### Basic Functionality Test

```powershell
# Navigate to distribution directory
cd dist\ForensicReportWriter

# Run the executable
.\ForensicReportWriter.exe
```

**Verify the following:**
- ✓ Application launches without errors
- ✓ Main window appears with Dashboard tab
- ✓ Can create a new case
- ✓ Can access File > Documentation menu
- ✓ Can access File > Settings
- ✓ Themes can be switched (Light/Dark/High Contrast)
- ✓ Can view Notifications menu

#### Feature Testing Checklist

**Dashboard:**
- ✓ Case table displays
- ✓ Charts render correctly
- ✓ Filtering works
- ✓ Export functions (CSV, PDF, Excel)

**Case Management:**
- ✓ Create new case
- ✓ Add evidence items
- ✓ Add legal processes
- ✓ Add leads

**Notes Tab:**
- ✓ Create and edit notes
- ✓ Formatting toolbar works
- ✓ Timestamp insertion
- ✓ Template loading

**Reports Tab:**
- ✓ Rich text editing
- ✓ PDF export
- ✓ Appendices management
- ✓ NIST template loading

**Notifications:**
- ✓ Notifications menu accessible
- ✓ Notifications panel opens
- ✓ Settings configurable

### 3. Check for Missing Dependencies

If the application fails to start, check for missing DLLs or Python modules:

```powershell
# Run with console output to see errors
.\ForensicReportWriter.exe --debug
```

### 4. File Size Check

Typical executable sizes:
- **Client**: 150-300 MB (depending on included libraries)
- **Server**: 50-100 MB

If sizes are significantly larger, review included data files in the .spec file.

---

## Troubleshooting

### Common Issues

#### Issue: "PyInstaller not found"
**Solution:**
```powershell
pip install pyinstaller
```

#### Issue: "ModuleNotFoundError" in built executable
**Solution:** Add missing module to `hiddenimports` in the .spec file:
```python
hiddenimports = [
    # ... existing imports
    "missing_module_name",
]
```

#### Issue: Application crashes on startup
**Possible causes:**
1. Missing `config.json` - Ensure it's included in `datas` in .spec file
2. Database initialization error - Check write permissions
3. Missing Qt platform plugins

**Solution for Qt plugins:**
```python
# Add to .spec file
from PyInstaller.utils.hooks import collect_data_files
datas += collect_data_files('PyQt5.QtCore')
```

#### Issue: WeasyPrint PDF export fails
**Solution:** Ensure WeasyPrint and its dependencies are properly collected:
```python
hiddenimports += collect_submodules("weasyprint")
hiddenimports += collect_submodules("cssselect2")
hiddenimports += collect_submodules("tinycss2")
```

#### Issue: Charts not displaying
**Solution:** Verify matplotlib/pyqtgraph are included:
```python
hiddenimports += ["matplotlib", "pyqtgraph"]
```

#### Issue: Large executable size
**Solutions:**
1. Enable UPX compression (requires UPX installed)
2. Exclude unnecessary packages
3. Use `--onefile` mode (slower startup but single exe)

### Debug Mode

To get detailed error information:

1. Edit the .spec file and set `console=True` in the EXE section
2. Rebuild
3. Run from command line to see console output

```python
exe = EXE(
    # ... other parameters
    console=True,  # Change from False to True
    # ... other parameters
)
```

### Check Build Logs

PyInstaller creates log files:
- `build/ForensicReportWriter/warn-ForensicReportWriter.txt` - Warnings during build
- Check for missing modules or libraries

---

## Distribution

### Packaging for Alpha Test

#### 1. Create Distribution Package

```powershell
# Create a zip file for distribution
Compress-Archive -Path "dist\ForensicReportWriter" -DestinationPath "ForensicReportSuite_v1.2_Alpha_Win64.zip"
```

#### 2. Include Documentation

Ensure the following are included in the distribution:
- ✓ `README.md` - Overview and quick start
- ✓ `MAIN_USER_GUIDE.md` - Complete user guide
- ✓ `NOTES_USER_GUIDE.md` - Notes feature documentation
- ✓ `REPORTS_USER_GUIDE.md` - Reports feature documentation
- ✓ `INSTALLATION_GUIDE.md` - Installation instructions
- ✓ `config.json` - Default configuration

#### 3. Create Release Notes

Create `RELEASE_NOTES_Alpha.md` with:
- Version number and date
- New features
- Known issues
- Testing instructions
- Contact information for bug reports

### Alpha Testing Checklist

**Before Distribution:**
- ✓ Full feature testing completed
- ✓ Documentation included
- ✓ Known issues documented
- ✓ Test on clean system (no Python installed)
- ✓ Virus scan completed
- ✓ Version numbers updated

**For Testers:**
- Provide clear testing instructions
- Set up bug reporting system (File > Report Bug in application)
- Request specific testing scenarios
- Collect feedback via File > Request Feature

### Installation Instructions for Testers

Include these instructions:

1. Extract the ZIP file to desired location
2. Navigate to the extracted folder
3. Run `ForensicReportWriter.exe`
4. On first run, application will create necessary directories
5. Access documentation via File > Documentation

**No Python installation required for end users!**

---

## Platform-Specific Notes

### Windows

- **Antivirus**: May flag PyInstaller executables as suspicious. Request testers add exception.
- **SmartScreen**: May show warning on first run. Instruct users to click "More info" > "Run anyway"
- **Dependencies**: All required DLLs are bundled

### macOS

- **Notarization**: For production release, consider Apple notarization
- **Gatekeeper**: Unsigned apps require right-click > Open on first run
- **Code Signing**: Consider signing for production distribution

### Linux

- **Dependencies**: Some system libraries may need separate installation
- **Permissions**: Make executable: `chmod +x ForensicReportWriter`
- **Desktop Integration**: Create .desktop file for menu integration

---

## Build Variants

### One-File vs One-Folder

**Current**: One-Folder mode (faster startup, easier debugging)

**To switch to One-File**:
Edit .spec file:
```python
exe = EXE(
    # ... parameters
    # Remove or comment out the COLLECT section
)
# COLLECT(...) <- Comment this out
```

### Debug vs Release

**Debug Build** (with console):
- Shows error messages
- Useful for testing
- Set `console=True` in .spec

**Release Build** (no console):
- Clean user experience
- Set `console=False` in .spec
- Current default

---

## Additional Resources

- **PyInstaller Documentation**: https://pyinstaller.org/
- **Python Packaging Guide**: https://packaging.python.org/
- **Qt Deployment**: https://doc.qt.io/qt-5/deployment.html

---

## Version History

- **v1.2 (February 2026)**: Alpha release with notification system and documentation menu
- **v1.1 (January 2026)**: Added peer review and enhanced features
- **v1.0 (December 2025)**: Initial release

---

## Support

For build issues or questions:
- Use the application's File > Report Bug feature
- Check troubleshooting section above
- Review PyInstaller documentation

---

**Last Updated**: February 3, 2026
**Build Script Version**: 1.0
