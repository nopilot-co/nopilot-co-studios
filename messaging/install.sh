#!/usr/bin/env bash
# Install the messaging studio's Python package (the `message` CLI) into a venv.
#
# Messaging is text-first and mostly pure-Python. The one optional native
# dependency is MJML (a Node CLI), needed only to render HTML email
# (`.html`/`.eml`). Text targets (.txt/.md) render without it; `message doctor`
# reports MJML status and `message render` skips HTML/eml with an install hint
# when MJML is absent.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'message' package (editable)…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

# ---- optional native dep: MJML (HTML email) --------------------------------
echo
echo "Checking MJML (optional — HTML email rendering):"
if command -v mjml > /dev/null 2>&1; then
  echo "  ✓ mjml ($(mjml --version 2> /dev/null | head -1))"
else
  if command -v npm > /dev/null 2>&1; then
    # Only install automatically when MESSAGING_INSTALL_MJML=1 — otherwise just hint.
    if [ "${MESSAGING_INSTALL_MJML:-0}" = "1" ]; then
      echo "  → installing mjml globally via npm…"
      if npm install -g mjml > /dev/null 2>&1; then
        echo "  ✓ mjml installed ($(mjml --version 2> /dev/null | head -1))"
      else
        echo "  ✗ npm install -g mjml failed — try: sudo npm install -g mjml"
      fi
    else
      echo "  ✗ mjml not found — install with: npm install -g mjml"
      echo "    (or re-run with MESSAGING_INSTALL_MJML=1 ./install.sh to install it now)"
    fi
  else
    echo "  ✗ mjml not found and node/npm is not on PATH"
    echo "    install Node (https://nodejs.org), then: npm install -g mjml"
  fi
  echo "    HTML email is optional — txt/md targets render without it."
fi

echo
echo "✓ messaging studio installed. Try:"
echo "    .venv/bin/message doctor"
echo "    .venv/bin/message formats list"
echo "    .venv/bin/message new --brand demo --name test-outreach --format outreach-email"
