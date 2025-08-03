#!/bin/bash

# Create requirements directory if it doesn't exist
mkdir -p requirements

# Install pip-tools if not already installed
pip install --upgrade pip-audit pip-tools

# Compile requirements
echo "Compiling requirements..."
pip-compile --strip-extras requirements/base.in -o requirements.txt
echo "Compiling development requirements..."
pip-compile --strip-extras requirements/dev.in -o requirements-dev.txt
echo "Compiling production requirements..."
pip-compile --strip-extras requirements/prod.in -o requirements-prod.txt

# Create a combined requirements file for development
cat requirements.txt requirements-dev.txt | grep -v '^#' | sort -u >requirements-dev.txt.tmp
mv requirements-dev.txt.tmp requirements-dev.txt

echo "Requirements files have been updated in the root directory."
