#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() {
  echo -e "${RED}[ERROR]${NC} $1" >&2
  exit 1
}

# Get the root directory of the project (one level up from scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"
ZIP_FILE="${ZIP_FILE:-$DIST_DIR/app.zip}"

# Default values with environment variable overrides
PACKAGE_DIR="${PACKAGE_DIR:-$ROOT_DIR/package}"
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"

# Create necessary directories if they don't exist
mkdir -p "$DIST_DIR" "$PACKAGE_DIR"

# Clean up any existing package
info "🧹 Cleaning up previous build..."
rm -rf "${PACKAGE_DIR:?}/"* 2>/dev/null || true
rm -f "$ZIP_FILE" 2>/dev/null || true

# Use PACKAGE_DIR for all packaging
PACKAGE_DIR="${PACKAGE_DIR:-$ROOT_DIR/package}"
mkdir -p "$PACKAGE_DIR"

# Function to copy files with error handling
copy_files() {
  local src=$1
  local dest=$2
  if [ -e "$src" ]; then
    cp -r "$src" "$dest" || error "Failed to copy $src to $dest"
    info "  → Copied $(basename "$src")"
    return 0
  else
    warn "  → $src not found, skipping"
    return 1
  fi
}

# Clean up the package directory
info "🧹 Cleaning package directory..."
rm -rf "${PACKAGE_DIR:?}/"* 2>/dev/null || true

# Copy the application code
info "📂 Copying application code..."
copy_files "$ROOT_DIR/app" "$PACKAGE_DIR/"

# Copy configuration files
info "📄 Copying configuration files..."
copy_files "$ROOT_DIR/wsgi.py" "$PACKAGE_DIR/"
copy_files "$ROOT_DIR/config.py" "$PACKAGE_DIR/"

# Make alembic.ini optional
if [ -f "$ROOT_DIR/alembic.ini" ]; then
  copy_files "$ROOT_DIR/alembic.ini" "$PACKAGE_DIR/"
else
  warn "⚠️  alembic.ini not found, but continuing without it"
fi

# Copy requirements files if they exist
for req_file in "requirements.txt" "requirements-dev.txt"; do
  if [ -f "$ROOT_DIR/$req_file" ]; then
    copy_files "$ROOT_DIR/$req_file" "$PACKAGE_DIR/"
  fi
done

# Install Python dependencies including aws-wsgi
if [ -f "$PACKAGE_DIR/requirements.txt" ]; then
  info "📦 Installing Python dependencies in package directory..."

  # Create a temporary requirements file without aws-wsgi if it exists in the original
  TMP_REQ=$(mktemp)
  grep -v '^aws-wsgi' "$PACKAGE_DIR/requirements.txt" >"$TMP_REQ"

  # Install all dependencies except aws-wsgi
  pip install -r "$TMP_REQ" -t "$PACKAGE_DIR" \
    --no-cache-dir \
    --disable-pip-version-check \
    --python-version "$PYTHON_VERSION" \
    --implementation cp \
    --only-binary=:all: \
    --platform manylinux2014_x86_64 || error "Failed to install dependencies"

  # Clean up the temporary file
  rm -f "$TMP_REQ"

  info "  → Dependencies installed successfully in $PACKAGE_DIR"
else
  warn "⚠️  requirements.txt not found in package directory. No Python dependencies will be installed."
fi

# Install aws-wsgi only if not already installed
if ! python3 -c "import awsgi" 2>/dev/null; then
  info "🔧 Installing AWS WSGI adapter in package directory..."
  pip install aws-wsgi==0.2.0 -t "$PACKAGE_DIR" \
    --no-cache-dir \
    --disable-pip-version-check || error "Failed to install aws-wsgi"
fi

# Create the zip file from the package directory
info "📦 Creating deployment package from $PACKAGE_DIR..."
# Run zip command and ignore its exit code
(cd "$PACKAGE_DIR" && zip -r9q "$ZIP_FILE" .) || true

# Verify the zip file was created
if [ ! -f "$ZIP_FILE" ]; then
  error "Failed to create zip file: $ZIP_FILE"
  # No need for exit 1 here as error() already exits with 1
fi

# Set appropriate permissions
chmod 644 "$ZIP_FILE"

# Show package summary
info "✅ Lambda package created: $ZIP_FILE"
info "📦 Package size: $(du -h "$ZIP_FILE" | cut -f1)"

# Show package contents summary
info "📋 Package contents summary:"
unzip -l "$ZIP_FILE" | head -n 15
echo "..."
unzip -l "$ZIP_FILE" | tail -n 3

info "✨ Package creation complete!"
