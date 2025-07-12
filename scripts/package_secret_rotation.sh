#!/bin/bash
set -e

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
LAMBDA_DIR="$TEMP_DIR/lambda"
OUTPUT_DIR="${PWD}/dist"

# Create directory structure
mkdir -p "$LAMBDA_DIR"

# Copy Lambda function code
cp terraform/lambda/secret_rotation/secret_rotation.py "$LAMBDA_DIR/"

# Install dependencies
pip install -r terraform/lambda/secret_rotation/requirements.txt -t "$LAMBDA_DIR" --no-cache-dir

# Create ZIP package
cd "$LAMBDA_DIR"
zip -r9 "${OUTPUT_DIR}/secret_rotation.zip" .
cd "$OLDPWD"

# Clean up
rm -rf "$TEMP_DIR"

echo "Lambda package created: secret_rotation.zip"
