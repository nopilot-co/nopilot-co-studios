#!/usr/bin/env bash
# Install the analytics studio's Python package (the `analytics` CLI) into a venv.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'analytics' package (editable)…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

echo
echo "✓ analytics studio installed. Try:"
echo "    .venv/bin/analytics doctor"
echo "    .venv/bin/analytics analysis new --engagement demo"
echo "    .venv/bin/analytics analysis materialise --engagement demo --analysis-json <path>"
