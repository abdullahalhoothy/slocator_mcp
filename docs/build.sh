#!/usr/bin/env bash
# Build the documentation PDF.
# Run from the docs/ directory: bash build.sh
set -e
cd "$(dirname "$0")"

echo "==> Generating Mermaid figures..."
python generate_figures.py

echo ""
echo "==> Building PDF with tectonic..."
tectonic main.tex

echo ""
echo "==> Done! Output: docs/main.pdf"