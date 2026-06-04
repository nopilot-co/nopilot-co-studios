#!/usr/bin/env bash
# Install the audience studio's Python package (the `audience` CLI) into a venv.
#
# The audience studio is pure-Python: it models the reader + critiques work, and
# reuses the nitpicker engine for scoring (it shells out to `nit aggregate`). So
# its only real dependency is the nitpicker `nit` CLI — `audience doctor` reports
# whether it is reachable, and `audience review score` fails with an install hint
# if it is absent.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'audience' package (editable)…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

# Scoring is reused from the nitpicker engine over the CLI boundary.
echo
echo "Checking the nitpicker 'nit' CLI (required — reader-fit scoring engine):"
if command -v nit > /dev/null 2>&1 || [ -x "$ROOT/../nitpicker/.venv/bin/nit" ]; then
  echo "  ✓ nit reachable"
else
  echo "  ✗ nit not found — run '../nitpicker/install.sh' (audience review score needs it)"
fi

echo
echo "✓ audience studio installed. Try:"
echo "    .venv/bin/audience doctor"
echo "    .venv/bin/audience persona new --audience demo-reader"
echo "    .venv/bin/audience rubric derive --audience demo-reader"
