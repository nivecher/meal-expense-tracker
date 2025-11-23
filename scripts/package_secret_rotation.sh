#!/bin/bash
set -e

# Default architecture (can be overridden with --arm64/--x86_64/--arch)
ARCHITECTURE="arm64"

# Parse simple args for architecture
while [[ $# -gt 0 ]]; do
  case "$1" in
    --arm64)
      ARCHITECTURE="arm64"
      shift
      ;;
    --x86_64)
      ARCHITECTURE="x86_64"
      shift
      ;;
    -a|--arch)
      ARCHITECTURE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"; exit 1;
      ;;
  esac
done

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
LAMBDA_DIR="$TEMP_DIR/lambda"
OUTPUT_DIR="${PWD}/dist/${ARCHITECTURE}"

# Create directory structure
mkdir -p "$LAMBDA_DIR"

# Copy Lambda function code
cp terraform/lambda/secret_rotation/secret_rotation.py "$LAMBDA_DIR/"

# Install dependencies
pip install -r terraform/lambda/secret_rotation/requirements.txt -t "$LAMBDA_DIR" --no-cache-dir

# Create ZIP package (architecture-first path and name)
cd "$LAMBDA_DIR"
mkdir -p "$OUTPUT_DIR"
zip -r9 "${OUTPUT_DIR}/secret_rotation-${ARCHITECTURE}.zip" .
cd "$OLDPWD"

# Clean up
rm -rf "$TEMP_DIR"

echo "Lambda package created: dist/${ARCHITECTURE}/secret_rotation-${ARCHITECTURE}.zip"
