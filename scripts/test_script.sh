#!/bin/bash

# This is a test script to demonstrate pre-commit hooks

echo "Hello, World!"

# Fixed: Quoted variable
GREETING="hello"
echo "$GREETING"

# Fixed: Properly quoted variable and fixed formatting
if [ "$1" = "test" ]; then
  echo "Testing..."
fi
