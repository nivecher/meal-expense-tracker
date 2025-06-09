#!/bin/bash

# Create requirements directory if it doesn't exist
mkdir -p requirements

# Install pip-tools if not already installed
pip install --upgrade pip-tools

# Compile requirements
pip-compile requirements/base.in -o requirements/requirements.txt
pip-compile requirements/dev.in -o requirements/dev-requirements.txt
pip-compile requirements/prod.in -o requirements/prod-requirements.txt
pip-compile requirements/security.in -o requirements/security-requirements.txt

echo "Requirements files have been updated in the requirements/ directory."
