#!/usr/bin/env bash
# Install the context studio's Python package (the `context` CLI) into a venv.
#
# Pure-Python; this studio is *infrastructural*: it orchestrates the tools/
# tier (notion-sources, source-enrich, source-summarise, theme-propose,
# theme-cluster, theme-entity, youtube-transcript) over the CLI boundary.
# Tools install separately; `context doctor` reports which are reachable.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'context' package (editable)…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

echo
echo "✓ context studio installed. Try:"
echo "    .venv/bin/context doctor    # tool-bench reachability report"
echo "    .venv/bin/context engagement new --engagement demo"
echo "    .venv/bin/context ingest --engagement demo --notion-db <id>"
