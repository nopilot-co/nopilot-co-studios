#!/usr/bin/env bash
# Install the commercial studio's Python package (the `commercial` CLI) into a
# venv.
#
# The commercial studio is pure-Python: it scaffolds + validates the shared
# commercial store (rate cards, pricing policy, client financials), runs the
# beancounter's deterministic checks, materialises the commercial officer's
# analysis, and reuses the nitpicker engine for scoring (shells out to
# `nit aggregate`). So its only real dependency is the `nit` CLI —
# `commercial doctor` reports whether it is reachable.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'commercial' package (editable)…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

# Scoring is reused from the nitpicker engine over the CLI boundary.
echo
echo "Checking the nitpicker 'nit' CLI (required — check-commercials scoring):"
if command -v nit > /dev/null 2>&1 || [ -x "$ROOT/../nitpicker/.venv/bin/nit" ]; then
  echo "  ✓ nit reachable"
else
  echo "  ✗ nit not found — run '../nitpicker/install.sh' (commercial check needs it)"
fi

echo
echo "✓ commercial studio installed. Try:"
echo "    .venv/bin/commercial doctor"
echo "    .venv/bin/commercial policy init"
echo "    .venv/bin/commercial check new --deal-slug demo-deal --deal-file <path>"
