#!/bin/bash

# Find all HTML files in the templates directory
find app/templates -name "*.html" | while read -r file; do
  echo "Checking $file..."

  # Check for inline script tags
  if grep -q "<script>" "$file" || grep -q "</script>" "$file"; then
    echo "  WARNING: Found inline <script> tags in $file"
    grep -n "<script>\|</script>" "$file"
  fi

  # Check for HTML event handlers
  if grep -E -q 'on(click|submit|change|keyup|keydown|focus|blur|input)\s*=' "$file"; then
    echo "  WARNING: Found HTML event handlers in $file"
    grep -nE 'on(click|submit|change|keyup|keydown|focus|blur|input)\s*=' "$file"
  fi

  # Check for javascript: in HTML attributes
  if grep -q 'javascript:' "$file"; then
    echo "  WARNING: Found 'javascript:' in $file"
    grep -n 'javascript:' "$file"
  fi
done
