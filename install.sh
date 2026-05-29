#!/usr/bin/env bash
# Install the Studios marketplace + plugins.
#
# This script:
#   1. Registers this repo as a Claude Code / Cowork plugin marketplace
#      (via the .claude-plugin/marketplace.json manifest).
#   2. Installs the three studios plugins (studios, design-studio,
#      messaging-studio) from that marketplace.
#   3. Reports per-studio Python CLI status and native dependency status.
#
# Idempotent: safe to re-run any time (existing marketplace/plugin installs
# are detected and skipped).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGINS=("studios" "design-studio" "messaging-studio" "nitpicker-studio")

# ---------------------------------------------------------------- 1. marketplace
register_marketplace() { # register_marketplace <host-cli>
  local host="$1"
  if ! command -v "$host" > /dev/null 2>&1; then
    echo "  • $host not on PATH — skip (manual: $host plugin marketplace add $ROOT)"
    return 1
  fi
  # `add` errors if already added; treat that as success.
  if "$host" plugin marketplace add "$ROOT" 2>&1 | grep -qE "(Successfully added|already)"; then
    echo "  ✓ marketplace registered with $host"
    return 0
  fi
  # Fall back to listing — if 'studios' shows up, we're good.
  if "$host" plugin marketplace list 2> /dev/null | grep -q "studios"; then
    echo "  ✓ marketplace already registered with $host"
    return 0
  fi
  echo "  ! $host did not accept 'plugin marketplace add $ROOT' — register manually"
  return 1
}

install_plugins() { # install_plugins <host-cli>
  local host="$1" name
  for name in "${PLUGINS[@]}"; do
    if "$host" plugin list 2> /dev/null | grep -q "^  ❯ $name@studios"; then
      echo "  • $name@studios already installed"
    else
      if "$host" plugin install "$name@studios" > /dev/null 2>&1; then
        echo "  ✓ installed $name@studios"
      else
        echo "  ✗ failed to install $name@studios — run 'claude plugin install $name@studios' for details"
      fi
    fi
  done
}

echo "Studios marketplace:"
if [ ! -f "$ROOT/.claude-plugin/marketplace.json" ]; then
  echo "  ✗ .claude-plugin/marketplace.json missing — aborting"
  exit 1
fi
for host in claude cowork; do
  if register_marketplace "$host"; then
    echo "  Installing plugins via $host:"
    install_plugins "$host" | sed 's/^/  /'
  fi
done

# ---------------------------------------------------------------- 2. python CLIs
echo
echo "Studio Python CLIs (the skills call these — install for full functionality):"
if [ -f "$ROOT/design/install.sh" ]; then
  if [ -x "$ROOT/design/.venv/bin/studio" ]; then
    echo "  ✓ studio CLI present (design/.venv/bin/studio)"
  else
    echo "  → run 'design/install.sh'     for the design 'studio' CLI (Quarto-backed)"
  fi
fi
if [ -f "$ROOT/messaging/install.sh" ]; then
  if [ -x "$ROOT/messaging/.venv/bin/message" ]; then
    echo "  ✓ message CLI present (messaging/.venv/bin/message)"
  else
    echo "  → run 'messaging/install.sh'  for the messaging 'message' CLI"
  fi
fi
if [ -f "$ROOT/nitpicker/install.sh" ]; then
  if [ -x "$ROOT/nitpicker/.venv/bin/nit" ]; then
    echo "  ✓ nit CLI present (nitpicker/.venv/bin/nit)"
  else
    echo "  → run 'nitpicker/install.sh'  for the nitpicker 'nit' CLI"
  fi
fi

# ---------------------------------------------------------------- 3. native deps
echo
echo "Runtime dependencies:"
check() { # check <tool> <hint>
  local t="$1" hint="$2"
  if command -v "$t" > /dev/null 2>&1; then
    echo "  ✓ $t"
  else
    echo "  ✗ $t — $hint"
  fi
}
check quarto "brew install --cask quarto       (design — required to render)"
check typst "brew install typst                (design — PDF engine; usually bundled with Quarto)"
check libreoffice "brew install --cask libreoffice  (design — PPTX→PDF for QA; binary may be 'soffice')"
check mjml "npm install -g mjml              (messaging — optional, HTML email only)"

echo
echo "Done. Try:"
echo "    /studio <your brief>             (creative-director)"
echo "    /design-studio <file.md>          (design studio directly)"
echo "    /messaging-studio                 (messaging studio directly)"
echo "    /nitpicker-studio <asset>         (nitpicker studio directly)"
