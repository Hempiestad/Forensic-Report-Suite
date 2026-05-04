# Quick Start: Building for Alpha Release

> Consolidation note (May 2026): This guide is retained as a quick-start companion.
> Canonical build and packaging reference: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md).
> If instructions conflict, follow BUILD_INSTRUCTIONS.md.

## For the Impatient 🚀

**Just want to build right now?**

```powershell
# 1. Install dependencies (if not done already)
pip install -r requirements.txt

# 2. Run the automated build script
.\build.ps1 -Client

# 3. Find your executable
cd dist\ForensicReportWriter
.\ForensicReportWriter.exe
```

Done! ✓

---

## Recommended Build Process

### Step 1: Pre-Flight Check (2 minutes)
```powershell
# Verify Python and dependencies
python --version          # Should be 3.8+
pip install pyinstaller   # If not already installed
pip install -r requirements.txt
```

### Step 2: Build (5-10 minutes)
```powershell
# Clean build with all checks
.\build.ps1 -Client -Clean
```

The script will:
- ✓ Check Python version
- ✓ Verify dependencies
- ✓ Run tests (optional)
- ✓ Build executable
- ✓ Verify output
- ✓ Copy documentation

### Step 3: Test (5 minutes)
```powershell
cd dist\ForensicReportWriter
.\ForensicReportWriter.exe

# Quick test checklist:
# - Application launches?
# - Dashboard appears?
# - Can create a case?
# - Documentation menu works?
```

### Step 4: Package for Distribution
```powershell
# Back to project root
cd ..\..

# Create distribution package
Compress-Archive -Path "dist\ForensicReportWriter" -DestinationPath "ForensicReportSuite_v1.2_Alpha_Win64.zip"
```

---

## Build Options

### Standard Build
```powershell
.\build.ps1 -Client
```

### Fast Build (Skip Tests)
```powershell
.\build.ps1 -Client -SkipTests
```

### Clean Build (Remove Previous Artifacts)
```powershell
.\build.ps1 -Client -Clean
```

### Build Both Client and Server
```powershell
.\build.ps1 -Both -Clean
```

### Run Server Addon (Extracted)
```powershell
# Install server deps
pip install -r requirements_server.txt

# Configure env from template
Copy-Item "Forensic Server\.env.example" "Forensic Server\.env"

# Start server addon
python "Forensic Server\server.py"
```

---

## Troubleshooting One-Liners

### "PyInstaller not found"
```powershell
pip install pyinstaller
```

### "Missing dependencies"
```powershell
pip install -r requirements.txt
```

### "Module not found in built executable"
Edit `ForensicReportWriter.spec` and add to `hiddenimports`:
```python
hiddenimports = [
    # ... existing
    "your_missing_module",
]
```

### "Can't find config.json"
Ensure in `.spec` file:
```python
datas = [
    (os.path.join(base_path, "config.json"), "."),
]
```

### Build Failed - Need Details
```powershell
# Run PyInstaller directly for verbose output
pyinstaller ForensicReportWriter.spec --clean --noconfirm --log-level DEBUG
```

---

## What Gets Built?

```
dist/ForensicReportWriter/
├── ForensicReportWriter.exe    ← Your executable (150-300 MB)
├── config.json                  ← Default configuration
├── MAIN_USER_GUIDE.md          ← Documentation
├── NOTES_USER_GUIDE.md
├── REPORTS_USER_GUIDE.md
├── INSTALLATION_GUIDE.md
├── [Many DLL files]             ← Dependencies
└── [Qt platform plugins]        ← GUI support
```

---

## Common Questions

**Q: Why is the exe so large?**  
A: It includes Python, PyQt5, and all dependencies - no installation needed!

**Q: Can I make it smaller?**  
A: Yes, use UPX compression (already enabled) or switch to one-file mode.

**Q: Do users need Python installed?**  
A: No! The executable is completely standalone.

**Q: How long does building take?**  
A: 3-10 minutes depending on your system.

**Q: Can I build on other platforms?**  
A: Yes! Mac/Linux use similar process, but use `bash` scripts instead of PowerShell.

---

## Next Steps After Building

1. **Test Thoroughly** - Use [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)
2. **Read Release Notes** - See [RELEASE_NOTES_Alpha_v1.2.md](RELEASE_NOTES_Alpha_v1.2.md)
3. **Package for Distribution** - Create ZIP with docs
4. **Send to Testers** - Include testing instructions
5. **Collect Feedback** - Via app's built-in bug report feature

---

## Full Documentation

- **Complete Build Guide**: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)
- **Pre-Build Checklist**: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)
- **Release Notes**: [RELEASE_NOTES_Alpha_v1.2.md](RELEASE_NOTES_Alpha_v1.2.md)

---

**Still having issues?** Check [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for detailed troubleshooting.

**Ready to build?** Run `.\build.ps1 -Client` and you're off! 🎯
