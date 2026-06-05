#!/usr/bin/env bash
# Install the growth studio's Python package (the `growth` CLI) into a venv.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'growth' package (editable)…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

echo
echo "✓ growth studio installed. Try:"
echo "    .venv/bin/growth doctor"
echo "    .venv/bin/growth leads new --engagement demo"
echo "    .venv/bin/growth market new --engagement demo"
