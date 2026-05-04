param(
    [switch]$WithVenv,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Failure { Write-Host $args -ForegroundColor Red }

$serverRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $serverRoot
Set-Location $repoRoot

Write-Info "Installing Forensic Server dependencies..."

if ($WithVenv) {
    $venvPath = Join-Path $serverRoot '.venv-server'
    if (-not (Test-Path $venvPath)) {
        Write-Info "Creating server venv at $venvPath"
        python -m venv $venvPath
    }

    $pythonExe = Join-Path $venvPath 'Scripts\python.exe'
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r (Join-Path $repoRoot 'requirements_server.txt')
    Write-Success "Server dependencies installed in .venv-server"
} else {
    python -m pip install --upgrade pip
    python -m pip install -r (Join-Path $repoRoot 'requirements_server.txt')
    Write-Success "Server dependencies installed in current Python environment"
}

$envExample = Join-Path $serverRoot '.env.example'
$envFile = Join-Path $serverRoot '.env'
if (Test-Path $envFile) {
    Write-Info ".env already exists at $envFile"
} elseif (Test-Path $envExample) {
    Copy-Item $envExample $envFile -Force:$Force
    Write-Success "Created .env from template"
} else {
    Write-Warning "No .env.example found. Skipped .env creation."
}

Write-Host ""
Write-Info "Next steps:"
if ($WithVenv) {
    Write-Host "  1. Activate server env: `"$serverRoot\.venv-server\Scripts\Activate.ps1`"" -ForegroundColor White
    Write-Host "  2. Edit Forensic Server\.env" -ForegroundColor White
    Write-Host "  3. Start server: python `"Forensic Server\server.py`"" -ForegroundColor White
} else {
    Write-Host "  1. Edit Forensic Server\.env" -ForegroundColor White
    Write-Host "  2. Start server: python `"Forensic Server\server.py`"" -ForegroundColor White
}
