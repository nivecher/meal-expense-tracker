#!/bin/bash
set -e

# Get the root directory of the project
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Copy the application code
cp -r "$ROOT_DIR/app" "$TEMP_DIR/"

# Copy the Lambda handler
mkdir -p "$TEMP_DIR/lambda"
cp "$ROOT_DIR/terraform/lambda/app/main.py" "$TEMP_DIR/lambda/"

# Install dependencies
if [ -f "$ROOT_DIR/requirements.txt" ]; then
    pip install -r "$ROOT_DIR/requirements.txt" -t "$TEMP_DIR"
fi

# Create the zip file (from inside the temp directory to avoid full paths in the zip)
(cd "$TEMP_DIR" && zip -r "$ROOT_DIR/terraform/app.zip" .)

echo "Lambda package created: $ROOT_DIR/terraform/app.zip"
