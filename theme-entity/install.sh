#!/usr/bin/env bash
# Install the theme-entity standalone CLI + dep (PyYAML). STUB utility.
# Idempotent: safe to re-run. Usage: ./install.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/scripts/build.py"
BIN_DIR="${THEME_ENTITY_BIN_DIR:-$HOME/.local/bin}"
CMD="$BIN_DIR/theme-entity"

echo "theme-entity — install (STUB)"
command -v python3 > /dev/null 2>&1 || { echo "  ! python3 not on PATH — install Python ≥ 3.8"; exit 1; }
echo "  • installing dep (PyYAML)…"
python3 -m pip install --quiet --upgrade PyYAML
chmod +x "$SCRIPT"; mkdir -p "$BIN_DIR"; ln -sf "$SCRIPT" "$CMD"
echo "  ✓ linked standalone CLI: $CMD -> $SCRIPT"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "  ! $BIN_DIR is not on PATH — add it to PATH" ;; esac
echo "  done (stub). Run: theme-entity --batch path/to/sources --themes themes.json"
