#!/bin/bash

# Create requirements directory if it doesn't exist
mkdir -p requirements

# Install pip-tools if not already installed
pip install --upgrade pip-tools

# Compile requirements
pip-compile requirements/base.in -o requirements.txt
pip-compile requirements/dev.in -o requirements-dev.txt
pip-compile requirements/prod.in -o requirements-prod.txt

# Create a combined requirements file for development
cat requirements.txt requirements-dev.txt | grep -v '^#' | sort -u >requirements-dev.txt.tmp
mv requirements-dev.txt.tmp requirements-dev.txt

echo "Requirements files have been updated in the root directory."
