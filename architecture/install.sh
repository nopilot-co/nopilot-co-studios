#!/usr/bin/env bash
# Install the architecture studio's Python package (the `arch` CLI) into a venv.
#
# Pure-Python: scaffolds the engagement architecture store, validates the
# spec + invariants, maintains ADRs. Optional integration with the design
# studio's `studio render-asset` lets `arch render` draw a diagram from the
# spec; degrades cleanly when design isn't installed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'architecture' package (editable)…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

echo
echo "✓ architecture studio installed. Try:"
echo "    .venv/bin/arch doctor"
echo "    .venv/bin/arch spec new --engagement demo --spec-json <path>"
echo "    .venv/bin/arch adr add --engagement demo --title 'event bus over REST' --status accepted"
