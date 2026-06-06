#!/usr/bin/env bash
# Hired. - one-shot dev bootstrap (macOS / Linux).
# Verifies toolchain, installs all deps, runs DB migrations, and reports back.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# --- colors -------------------------------------------------------------
if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_DIM=""; C_RST=""
fi

step()  { printf "%s==>%s %s\n" "$C_GRN" "$C_RST" "$*"; }
warn()  { printf "%s!! %s %s\n" "$C_YEL" "$C_RST" "$*"; }
fail()  { printf "%sxx %s %s\n" "$C_RED" "$C_RST" "$*" >&2; exit 1; }

# --- tool checks --------------------------------------------------------
check_node() {
  command -v node >/dev/null || fail "Node not found. Install Node 20+ from https://nodejs.org"
  local raw major
  raw="$(node --version)"            # e.g. v22.10.0
  major="${raw#v}"; major="${major%%.*}"
  (( major >= 20 )) || fail "Node $raw is too old; need >= 20."
  step "Node $raw OK"
}

check_python() {
  local py=""
  if command -v python3 >/dev/null; then py=python3
  elif command -v python  >/dev/null; then py=python
  else fail "Python not found. Install Python 3.11+ from https://python.org"
  fi
  local raw major minor
  raw="$($py --version 2>&1)"        # "Python 3.12.4"
  major="$(echo "$raw" | awk '{print $2}' | cut -d. -f1)"
  minor="$(echo "$raw" | awk '{print $2}' | cut -d. -f2)"
  if (( major < 3 )) || { (( major == 3 )) && (( minor < 11 )); }; then
    fail "$raw is too old; need >= 3.11."
  fi
  step "$raw OK"
}

check_rust() {
  if ! command -v rustc >/dev/null; then
    warn "rustc not found. Tauri build will be skipped."
    warn "Install Rust from https://rustup.rs (rustup default stable)."
    RUST_OK=0
  else
    step "$(rustc --version) OK"
    RUST_OK=1
  fi
}

check_uv() {
  if ! command -v uv >/dev/null; then
    fail "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
  fi
  step "$(uv --version) OK"
}

check_pnpm() {
  if ! command -v pnpm >/dev/null; then
    fail "pnpm not found. Install with: corepack enable  (or https://pnpm.io/installation)"
  fi
  step "pnpm $(pnpm --version) OK"
}

# --- install steps ------------------------------------------------------
install_frontend() {
  step "Installing frontend deps (pnpm install)"
  ( cd frontend && pnpm install )
}

install_backend() {
  step "Installing backend deps (uv sync)"
  ( cd backend && uv sync )
}

migrate_db() {
  step "Running DB migrations (alembic upgrade head)"
  ( cd backend && uv run alembic upgrade head )
}

fetch_rust_deps() {
  if [[ "${RUST_OK:-0}" -ne 1 ]]; then
    warn "Skipping cargo fetch (Rust not installed)."
    return
  fi
  if [[ ! -d src-tauri ]]; then
    warn "Skipping cargo fetch (src-tauri/ does not exist yet - added in Phase 1 task 1.2)."
    return
  fi
  step "Fetching Rust deps (cargo fetch)"
  ( cd src-tauri && cargo fetch )
}

# --- run ----------------------------------------------------------------
echo "${C_DIM}Hired. bootstrap - checking toolchain...${C_RST}"
check_node
check_python
check_rust
check_uv
check_pnpm

echo ""
echo "${C_DIM}Installing dependencies...${C_RST}"
install_frontend
install_backend
migrate_db
fetch_rust_deps

echo ""
step "Setup complete. Run ${C_GRN}pnpm tauri dev${C_RST} to start."
echo "  ${C_DIM}(or run backend + frontend separately during Phase 1:${C_RST}"
echo "  ${C_DIM}  cd backend  && uv run uvicorn api.main:app --reload --port 8765${C_RST}"
echo "  ${C_DIM}  cd frontend && pnpm dev${C_RST}"
echo "  ${C_DIM})${C_RST}"
