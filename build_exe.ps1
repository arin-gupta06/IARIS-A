# IARIS Executable Bundle Builder - PowerShell Script
# Usage: .\build_exe.ps1 -Clean
# Or: .\build_exe.ps1

param(
    [switch]$Clean = $false
)

$ErrorActionPreference = "Stop"

# ─── Colors ─────────────────────────────────────────────────────────────────

$Colors = @{
    Header   = "`e[95m"
    Blue     = "`e[94m"
    Cyan     = "`e[96m"
    Green    = "`e[92m"
    Yellow   = "`e[93m"
    Red      = "`e[91m"
    Reset    = "`e[0m"
    Bold     = "`e[1m"
}

function Write-Step {
    param([string]$Message)
    Write-Host "$($Colors.Bold)$($Colors.Cyan)[BUILD]$($Colors.Reset) $Message"
}

function Write-Success {
    param([string]$Message)
    Write-Host "$($Colors.Green)✓ $Message$($Colors.Reset)"
}

function Write-Error {
    param([string]$Message)
    Write-Host "$($Colors.Red)✗ $Message$($Colors.Reset)"
}

# ─── Header ─────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "$($Colors.Header)$($Colors.Bold)╔══════════════════════════════════════════════════════╗"
Write-Host "║         IARIS Executable Bundle Builder v1.0         ║"
Write-Host "╚══════════════════════════════════════════════════════╝$($Colors.Reset)"
Write-Host ""

# ─── Validation ──────────────────────────────────────────────────────────────

Write-Step "Validating environment..."

if (-not (Test-Path "pyproject.toml")) {
    Write-Error "pyproject.toml not found!"
    Write-Host "Please run this script from the IARIS project root directory."
    exit 1
}

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python not found in PATH!"
    Write-Host "Please install Python 3.11+ from https://www.python.org/"
    exit 1
}

$pythonVersion = & python --version 2>&1
Write-Success "Python found: $pythonVersion"

# Check Node.js
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Error "Node.js not found in PATH!"
    Write-Host "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
}

$nodeVersion = & node --version
Write-Success "Node.js found: $nodeVersion"

# Check venv
if (-not (Test-Path ".venv") -and -not (Test-Path "venv")) {
    Write-Error "Virtual environment not found!"
    Write-Host "Please set up the venv first:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\pip install -e ."
    exit 1
}

Write-Success "Virtual environment found"
Write-Host ""

# ─── Build ───────────────────────────────────────────────────────────────────

Write-Step "Starting build process..."
Write-Host ""

$buildArgs = @()
if ($Clean) {
    $buildArgs += "--clean"
}

& python build_exe.py @buildArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Error "Build failed!"
    exit 1
}

Write-Host ""
Write-Host "$($Colors.Green)$($Colors.Bold)╔══════════════════════════════════════════════════════╗"
Write-Host "║              BUILD SUCCESSFUL! ✓                     ║"
Write-Host "╚══════════════════════════════════════════════════════╝$($Colors.Reset)"
Write-Host ""

# ─── Completion ─────────────────────────────────────────────────────────────

Write-Host "📦 Your executable is ready!"
Write-Host "📍 Location: frontend\dist-electron\"
Write-Host "🚀 Next step: Double-click the .exe to run IARIS"
Write-Host ""

# Optional: Open folder
$outputDir = Join-Path $PWD "frontend\dist-electron"
if (Test-Path $outputDir) {
    $response = Read-Host "Open output folder? (y/n)"
    if ($response -eq "y" -or $response -eq "yes") {
        Invoke-Item $outputDir
    }
}
