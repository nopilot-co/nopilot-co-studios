#!/usr/bin/env bash
# Install the delivery studio's Python package (the `delivery` CLI) into a venv.
#
# Pure-Python: scaffolds the engagement plan store, validates the plan + RAID
# payloads, derives rollups. No native deps; no nitpicker reuse (delivery
# produces an artefact rather than running a review-class gate). The Producer
# may route a delivery plan to the nitpicker for an objective review later,
# but that's its own session.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'delivery' package (editable)…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

echo
echo "✓ delivery studio installed. Try:"
echo "    .venv/bin/delivery doctor"
echo "    .venv/bin/delivery plan new --engagement demo --plan-json <path>"
echo "    .venv/bin/delivery raid add --engagement demo --kind risk --title 'vendor outage'"
