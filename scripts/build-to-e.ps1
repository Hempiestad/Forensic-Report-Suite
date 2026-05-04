# Build Script for Komainu Labs Forensic Report Suite - E:\ Drive Output
# Version: 1.1 Alpha Build to E:\
# Date: February 4, 2026
# Description: Automated build script with output to E:\ drive

param(
    [switch]$Client,
    [switch]$Server,
    [switch]$Both,
    [switch]$Clean,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

# Set output directory to E:\ drive
$outputDir = "E:\"
$distPath = Join-Path $outputDir "ForensicSuite_Alpha_v1.2"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Failure { Write-Host $args -ForegroundColor Red }

# Banner
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Komainu Labs Forensic Report Suite - Build System            ║" -ForegroundColor Cyan
Write-Host "║  Version 1.2 - Alpha Build to E:\ Drive                       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Info "Output Directory: $distPath"
Write-Host ""

# Determine what to build
if (-not $Client -and -not $Server -and -not $Both) {
    Write-Warning "No build target specified. Use -Client, -Server, or -Both"
    Write-Info "Example: .\build-to-e.ps1 -Both"
    exit 1
}

if ($Both) {
    $Client = $true
    $Server = $true
}

# Create output directory if it doesn't exist
if (-not (Test-Path $distPath)) {
    Write-Info "Creating output directory: $distPath"
    New-Item -ItemType Directory -Path $distPath -Force | Out-Null
    Write-Success "✓ Output directory created"
}

# Pre-Build Checks
Write-Info "═══ Phase 1: Pre-Build Checks ═══"
Write-Host ""

# Check Python version
Write-Info "Checking Python version..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "✓ $pythonVersion"
    
    # Verify Python 3.8+
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
            Write-Failure "✗ Python 3.8 or higher required"
            exit 1
        }
    }
} catch {
    Write-Failure "✗ Python not found in PATH"
    exit 1
}

# Check PyInstaller
Write-Info "Checking PyInstaller..."
try {
    $pyinstallerVersion = pyinstaller --version 2>&1
    Write-Success "✓ PyInstaller $pyinstallerVersion"
} catch {
    Write-Warning "PyInstaller not found. Installing..."
    pip install pyinstaller
    Write-Success "✓ PyInstaller installed"
}

# Check critical files exist
Write-Info "Checking critical files..."
$criticalFiles = @(
    "main.py",
    "config.json",
    "src\\database.py",
    "packaging\\ForensicReportWriter.spec"
)

if ($Server) {
    $criticalFiles += "Forensic Server\server.py"
    $criticalFiles += "packaging\\ForensicCaseServer.spec"
}

$missingFiles = @()
foreach ($file in $criticalFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
        Write-Failure "✗ Missing: $file"
    } else {
        Write-Success "✓ Found: $file"
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Failure "Build aborted: Missing critical files"
    exit 1
}

# Check dependencies
Write-Info "Checking Python dependencies..."
$requiredPackages = @(
    "PyQt5",
    "pandas",
    "weasyprint",
    "openpyxl",
    "cryptography",
    "argon2-cffi",
    "bcrypt",
    "keyring"
)

if ($Server) {
    $requiredPackages += "Flask"
    $requiredPackages += "Flask-SQLAlchemy"
}

$missingPackages = @()
foreach ($package in $requiredPackages) {
    try {
        pip show $package > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ $package installed"
        } else {
            $missingPackages += $package
            Write-Warning "⚠ $package not found"
        }
    } catch {
        $missingPackages += $package
        Write-Warning "⚠ $package not found"
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Warning "Missing packages detected. Install with:"
    if ($Server) {
        Write-Host "  pip install -r requirements_server.txt" -ForegroundColor Yellow
    } else {
        Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    }
    
    $response = Read-Host "Continue anyway? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 1
    }
}

# Run tests if not skipped
if (-not $SkipTests) {
    Write-Info "`n═══ Phase 2: Running Tests ═══"
    Write-Host ""
    
    # Check if pytest is available
    try {
        pip show pytest > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Running unit tests..."
            pytest tests/ -v --tb=short
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "⚠ Some tests failed. Continue anyway? (y/N)"
                $response = Read-Host
                if ($response -ne "y" -and $response -ne "Y") {
                    exit 1
                }
            } else {
                Write-Success "✓ All tests passed"
            }
        } else {
            Write-Warning "pytest not installed. Skipping tests."
        }
    } catch {
        Write-Warning "Could not run tests"
    }
}

# Clean previous builds if requested
if ($Clean) {
    Write-Info "`n═══ Cleaning Previous Builds ═══"
    Write-Host ""
    
    $cleanDirs = @("build", "dist")
    foreach ($dir in $cleanDirs) {
        if (Test-Path $dir) {
            Write-Info "Removing $dir..."
            Remove-Item -Recurse -Force $dir
            Write-Success "✓ Cleaned $dir"
        }
    }
    
    # Remove .spec temp files
    Get-ChildItem -Filter "*.spec~" | Remove-Item -Force
}

# Build Phase
Write-Info "`n═══ Phase 3: Building Executables ═══"
Write-Host ""

$buildSuccess = $true

# Build Client
if ($Client) {
    Write-Info "Building ForensicReportWriter (Client)..."
    Write-Host "This may take several minutes..." -ForegroundColor Yellow
    
    try {
        pyinstaller packaging\ForensicReportWriter.spec --clean --noconfirm
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Client build completed"
        } else {
            Write-Failure "✗ Client build failed"
            $buildSuccess = $false
        }
    } catch {
        Write-Failure "✗ Client build error: $_"
        $buildSuccess = $false
    }
}

# Build Server
if ($Server) {
    Write-Info "`nBuilding ForensicCaseServer (Server)..."
    Write-Host "This may take several minutes..." -ForegroundColor Yellow
    
    try {
        pyinstaller packaging\ForensicCaseServer.spec --clean --noconfirm
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Server build completed"
        } else {
            Write-Failure "✗ Server build failed"
            $buildSuccess = $false
        }
    } catch {
        Write-Failure "✗ Server build error: $_"
        $buildSuccess = $false
    }
}

# Post-Build Verification and Copy to E:\ Drive
Write-Info "`n═══ Phase 4: Post-Build Verification & Copy to E:\ ═══"
Write-Host ""

$localDistPath = "dist"
if (-not (Test-Path $localDistPath)) {
    Write-Failure "✗ Distribution directory not found"
    exit 1
}

if ($Client) {
    $clientExe = Join-Path $localDistPath "ForensicReportWriter\ForensicReportWriter.exe"
    if (Test-Path $clientExe) {
        $size = (Get-Item $clientExe).Length / 1MB
        Write-Success "✓ Client executable: $clientExe ($([math]::Round($size, 2)) MB)"
        
        # Copy to E:\ drive
        $clientDestPath = Join-Path $distPath "ForensicReportWriter"
        Write-Info "Copying client to E:\..."
        Copy-Item -Path (Join-Path $localDistPath "ForensicReportWriter") -Destination $clientDestPath -Recurse -Force
        Write-Success "✓ Client copied to: $clientDestPath"
    } else {
        Write-Failure "✗ Client executable not found"
        $buildSuccess = $false
    }
}

if ($Server) {
    $serverExe = Join-Path $localDistPath "ForensicCaseServer\ForensicCaseServer.exe"
    if (Test-Path $serverExe) {
        $size = (Get-Item $serverExe).Length / 1MB
        Write-Success "✓ Server executable: $serverExe ($([math]::Round($size, 2)) MB)"
        
        # Copy to E:\ drive
        $serverDestPath = Join-Path $distPath "ForensicCaseServer"
        Write-Info "Copying server to E:\..."
        Copy-Item -Path (Join-Path $localDistPath "ForensicCaseServer") -Destination $serverDestPath -Recurse -Force
        Write-Success "✓ Server copied to: $serverDestPath"
    } else {
        Write-Failure "✗ Server executable not found"
        $buildSuccess = $false
    }
}

# Copy documentation and config files to distribution
Write-Info "`nCopying documentation files..."
$docFiles = @("README.md", "MAIN_USER_GUIDE.md", "NOTES_USER_GUIDE.md", "REPORTS_USER_GUIDE.md", "INSTALLATION_GUIDE.md", "ALPHA_BUILD_READINESS_REPORT.md", "PRECOMPILATION_TEST_REPORT.md")

if ($Client) {
    $clientDistPath = Join-Path $distPath "ForensicReportWriter"
    foreach ($doc in $docFiles) {
        if (Test-Path $doc) {
            Copy-Item $doc $clientDistPath -Force
            Write-Success "✓ Copied $doc to client distribution"
        }
    }
}

# Final Summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

if ($buildSuccess) {
    Write-Success "`n✓ BUILD SUCCESSFUL!"
    Write-Host ""
    Write-Info "Distribution location: $distPath"
    
    if ($Client) {
        Write-Info "  Client: $distPath\ForensicReportWriter\"
    }
    if ($Server) {
        Write-Info "  Server: $distPath\ForensicCaseServer\"
    }
    
    Write-Host ""
    Write-Info "Next Steps:"
    Write-Host "  1. Navigate to: $distPath" -ForegroundColor White
    Write-Host "  2. Test the executable(s) thoroughly" -ForegroundColor White
    Write-Host "  3. Check for any missing DLLs or dependencies" -ForegroundColor White
    Write-Host "  4. Verify all features work correctly" -ForegroundColor White
    Write-Host "  5. Package for distribution" -ForegroundColor White
    Write-Host ""
    Write-Success "✓ Build artifacts ready on E:\ drive!"
    Write-Host ""
    
    exit 0
} else {
    Write-Failure "`n✗ BUILD FAILED"
    Write-Host ""
    Write-Info "Check the error messages above for details."
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Missing dependencies (run: pip install -r requirements.txt)" -ForegroundColor Yellow
    Write-Host "  - Incorrect Python version (requires 3.8+)" -ForegroundColor Yellow
    Write-Host "  - Missing icon files (.ico)" -ForegroundColor Yellow
    Write-Host ""
    
    exit 1
}
