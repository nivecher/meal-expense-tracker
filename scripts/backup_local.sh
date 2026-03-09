#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups/local}"
DB_PATH="${DB_PATH:-$ROOT_DIR/instance/app-development.db}"
TIMESTAMP="$(date +%F-%H%M%S)"

mkdir -p "$BACKUP_ROOT/db"

log() {
  printf '%s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

backup_db() {
  require_command sqlite3

  if [[ ! -f "$DB_PATH" ]]; then
    log "Database file not found: $DB_PATH"
    exit 1
  fi

  local dest="$BACKUP_ROOT/db/app-development-$TIMESTAMP.db"
  sqlite3 "$DB_PATH" ".backup '$dest'"
  log "Database backup created: $dest"
}

backup_db
