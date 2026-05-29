#!/usr/bin/env bash
# Install the nitpicker studio's Python package (the `nit` CLI) into a venv.
#
# The nitpicker is review-only and mostly pure-Python. Its optional extra is
# *capture* — rasterising a target so visual QA has pixels: pypdfium2 (PDF),
# pillow, and playwright (URL/HTML). Text-only review (md/txt) needs none of it;
# `nit doctor` reports capture-tool status and `nit capture` degrades with an
# install hint when a backend is absent.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "Creating venv…"
  python3 -m venv .venv
fi

echo "Installing the 'nit' package (editable)…"
.venv/bin/pip install -q --upgrade pip

# Install with the capture extra unless NITPICKER_NO_CAPTURE=1 (text-only setups).
if [ "${NITPICKER_NO_CAPTURE:-0}" = "1" ]; then
  .venv/bin/pip install -q -e .
  echo "  (text-only install — capture backends skipped)"
else
  .venv/bin/pip install -q -e ".[capture]"
  # Playwright needs its browser binary for URL/HTML capture.
  echo
  echo "Installing the Chromium browser for playwright (URL/HTML capture)…"
  if .venv/bin/playwright install chromium > /dev/null 2>&1; then
    echo "  ✓ chromium installed"
  else
    echo "  ✗ 'playwright install chromium' failed — URL/HTML capture will fall"
    echo "    back to wkhtmltoimage if present. Retry: .venv/bin/playwright install chromium"
  fi
fi

# PPTX capture needs LibreOffice (a native app, not pip-installable).
echo
echo "Checking LibreOffice (optional — PPTX capture):"
if command -v libreoffice > /dev/null 2>&1 || command -v soffice > /dev/null 2>&1; then
  echo "  ✓ libreoffice present"
else
  echo "  ✗ libreoffice not found — install with: brew install --cask libreoffice"
  echo "    (only needed to capture .pptx targets; other targets render without it)"
fi

echo
echo "✓ nitpicker studio installed. Try:"
echo "    .venv/bin/nit doctor"
echo "    .venv/bin/nit tests list"
echo "    .venv/bin/nit config show"
echo "    .venv/bin/nit new --name demo-review --target ./asset.pdf --brief ./brief.md"
