#!/usr/bin/env bash
# Install the youtube-transcript standalone CLI + its Python dependencies.
#
# This script:
#   1. Installs the caption dependency (youtube-transcript-api). With
#      YT_TRANSCRIPT_FALLBACK=1 it also installs the Whisper fallback deps
#      (yt-dlp + faster-whisper).
#   2. Exposes the extractor as a standalone command `yt-transcript` on PATH
#      (symlinked into ~/.local/bin), so the utility is runnable on its own —
#      independent of the Claude Code plugin.
#
# Idempotent: safe to re-run. Usage: ./install.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/scripts/extract.py"
BIN_DIR="${YT_TRANSCRIPT_BIN_DIR:-$HOME/.local/bin}"
CMD="$BIN_DIR/yt-transcript"

echo "youtube-transcript — install"

# ----------------------------------------------------------- 1. python + deps
if ! command -v python3 > /dev/null 2>&1; then
  echo "  ! python3 not on PATH — install Python ≥ 3.9 first (brew install python@3.12)"
  exit 1
fi

echo "  • installing caption dependency (youtube-transcript-api)…"
python3 -m pip install --quiet --upgrade youtube-transcript-api

if [ "${YT_TRANSCRIPT_FALLBACK:-0}" = "1" ]; then
  echo "  • installing Whisper fallback deps (yt-dlp + faster-whisper)…"
  python3 -m pip install --quiet --upgrade yt-dlp faster-whisper
  command -v yt-dlp > /dev/null 2>&1 || echo "  ! yt-dlp not on PATH after install — add your pip bin dir to PATH"
else
  echo "  • skipping Whisper fallback deps (set YT_TRANSCRIPT_FALLBACK=1 to include yt-dlp + faster-whisper)"
fi

# ----------------------------------------------------------- 2. standalone CLI
chmod +x "$SCRIPT"
mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT" "$CMD"
echo "  ✓ linked standalone CLI: $CMD -> $SCRIPT"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "  ! $BIN_DIR is not on PATH — add it, e.g.: export PATH=\"$BIN_DIR:\$PATH\"" ;;
esac

echo "  done. Run:  yt-transcript \"https://www.youtube.com/watch?v=ID\" --out transcript.txt"
