# Hired. - one-shot dev bootstrap (Windows PowerShell).
# Verifies toolchain, installs all deps, runs DB migrations, and reports back.

#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "!!  $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "xx  $msg" -ForegroundColor Red; exit 1 }

# --- tool checks --------------------------------------------------------
function Test-NodeVersion {
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodeCmd) {
        Fail "Node not found. Install Node 20+ from https://nodejs.org"
    }
    $raw = node --version          # e.g. v22.10.0
    $major = [int]($raw.TrimStart('v').Split('.')[0])
    if ($major -lt 20) { Fail "Node $raw is too old; need >= 20." }
    Step "Node $raw OK"
}

function Test-PythonVersion {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyCmd) { $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $pyCmd) {
        Fail "Python not found. Install Python 3.11+ from https://python.org"
    }
    $raw = & $pyCmd.Source --version 2>&1   # "Python 3.12.10"
    $parts = $raw.Split(' ')[1].Split('.')
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Fail "$raw is too old; need >= 3.11."
    }
    Step "$raw OK"
}

function Test-RustToolchain {
    $rustCmd = Get-Command rustc -ErrorAction SilentlyContinue
    if (-not $rustCmd) {
        Warn "rustc not found. Tauri build will be skipped."
        Warn "Install Rust from https://rustup.rs"
        $script:RustOk = $false
    } else {
        Step "$(rustc --version) OK"
        $script:RustOk = $true
    }
}

function Test-Uv {
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvCmd) {
        Fail "uv not found. Install with: powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
    }
    Step "$(uv --version) OK"
}

function Test-Pnpm {
    $pnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue
    if (-not $pnpmCmd) {
        Fail "pnpm not found. Install with: iwr https://get.pnpm.io/install.ps1 -useb | iex  (or corepack enable in an admin shell)"
    }
    Step "pnpm $(pnpm --version) OK"
}

# --- install steps ------------------------------------------------------
function Install-Frontend {
    Step "Installing frontend deps (pnpm install)"
    Push-Location frontend
    try { pnpm install } finally { Pop-Location }
}

function Install-Backend {
    Step "Installing backend deps (uv sync)"
    Push-Location backend
    try { uv sync } finally { Pop-Location }
}

function Invoke-DbMigration {
    Step "Running DB migrations (alembic upgrade head)"
    Push-Location backend
    try { uv run alembic upgrade head } finally { Pop-Location }
}

function Get-RustDeps {
    if (-not $script:RustOk) {
        Warn "Skipping cargo fetch (Rust not installed)."
        return
    }
    if (-not (Test-Path src-tauri)) {
        Warn "Skipping cargo fetch (src-tauri\ does not exist yet - added in Phase 1 task 1.2)."
        return
    }
    Step "Fetching Rust deps (cargo fetch)"
    Push-Location src-tauri
    try { cargo fetch } finally { Pop-Location }
}

# --- run ----------------------------------------------------------------
Write-Host "Hired. bootstrap - checking toolchain..." -ForegroundColor DarkGray
Test-NodeVersion
Test-PythonVersion
Test-RustToolchain
Test-Uv
Test-Pnpm

Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor DarkGray
Install-Frontend
Install-Backend
Invoke-DbMigration
Get-RustDeps

Write-Host ""
Step "Setup complete. Run 'pnpm tauri dev' to start."
Write-Host "  (or run backend + frontend separately during Phase 1:" -ForegroundColor DarkGray
Write-Host "    cd backend  ; uv run uvicorn api.main:app --reload --port 8765" -ForegroundColor DarkGray
Write-Host "    cd frontend ; pnpm dev" -ForegroundColor DarkGray
Write-Host "  )" -ForegroundColor DarkGray
