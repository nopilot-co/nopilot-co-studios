#!/usr/bin/env bash
# Install the nopilot-co-studios marketplace + plugins.
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
PLUGINS=("studios" "design-studio" "messaging-studio" "nitpicker-studio" "audience-studio" "commercial-studio" "delivery-studio" "architecture-studio" "context-studio")

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
  # Fall back to listing — if 'nopilot-co-studios' shows up, we're good.
  if "$host" plugin marketplace list 2> /dev/null | grep -q "nopilot-co-studios"; then
    echo "  ✓ marketplace already registered with $host"
    return 0
  fi
  echo "  ! $host did not accept 'plugin marketplace add $ROOT' — register manually"
  return 1
}

install_plugins() { # install_plugins <host-cli>
  local host="$1" name
  for name in "${PLUGINS[@]}"; do
    if "$host" plugin list 2> /dev/null | grep -q "^  ❯ $name@nopilot-co-studios"; then
      echo "  • $name@nopilot-co-studios already installed"
    else
      if "$host" plugin install "$name@nopilot-co-studios" > /dev/null 2>&1; then
        echo "  ✓ installed $name@nopilot-co-studios"
      else
        echo "  ✗ failed to install $name@nopilot-co-studios — run 'claude plugin install $name@nopilot-co-studios' for details"
      fi
    fi
  done
}

echo "nopilot-co-studios marketplace:"
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

# The root `planner` CLI (composite-document planning) ships with the root
# `studios` plugin itself — no sub-install.sh — so install it here (editable).
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" > /dev/null 2>&1; then
    ver="$($cand -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2> /dev/null)"
    if [ -n "$ver" ] && [ "$(printf '%s\n3.10\n' "$ver" | sort -V | head -1)" = "3.10" ]; then
      PY="$cand"
      break
    fi
  fi
done
if [ -n "$PY" ]; then
  if "$PY" -m pip install --user -e "$ROOT" > /dev/null 2>&1; then
    echo "  ✓ planner CLI installed (root composite-document planner)"
  else
    echo "  ✗ planner CLI install failed — retry: $PY -m pip install --user -e $ROOT"
  fi
else
  echo "  ✗ planner CLI skipped — no Python ≥ 3.10 found"
fi

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
if [ -f "$ROOT/audience/install.sh" ]; then
  if [ -x "$ROOT/audience/.venv/bin/audience" ]; then
    echo "  ✓ audience CLI present (audience/.venv/bin/audience)"
  else
    echo "  → run 'audience/install.sh'   for the audience CLI (reuses 'nit' for scoring)"
  fi
fi
if [ -f "$ROOT/commercial/install.sh" ]; then
  if [ -x "$ROOT/commercial/.venv/bin/commercial" ]; then
    echo "  ✓ commercial CLI present (commercial/.venv/bin/commercial)"
  else
    echo "  → run 'commercial/install.sh' for the commercial CLI (reuses 'nit' for scoring)"
  fi
fi
if [ -f "$ROOT/delivery/install.sh" ]; then
  if [ -x "$ROOT/delivery/.venv/bin/delivery" ]; then
    echo "  ✓ delivery CLI present (delivery/.venv/bin/delivery)"
  else
    echo "  → run 'delivery/install.sh'   for the delivery CLI (optional cost via commercial)"
  fi
fi
if [ -f "$ROOT/architecture/install.sh" ]; then
  if [ -x "$ROOT/architecture/.venv/bin/arch" ]; then
    echo "  ✓ arch CLI present (architecture/.venv/bin/arch)"
  else
    echo "  → run 'architecture/install.sh' for the architecture CLI (optional diagram render via design)"
  fi
fi
if [ -f "$ROOT/context-studio/install.sh" ]; then
  if [ -x "$ROOT/context-studio/.venv/bin/context" ]; then
    echo "  ✓ context CLI present (context-studio/.venv/bin/context)"
  else
    echo "  → run 'context-studio/install.sh' for the context CLI (orchestrates the tools/ tier)"
  fi
fi

# ---------------------------------------------------------------- 3. native deps
echo
echo "Runtime dependencies:"
check() { # check <name> <hint> [alt-binary ...]
  local name="$1" hint="$2"
  shift 2
  local cand
  for cand in "$name" "$@"; do
    if command -v "$cand" > /dev/null 2>&1; then
      echo "  ✓ $name"
      return
    fi
  done
  echo "  ✗ $name — $hint"
}
check quarto "brew install --cask quarto       (design — required to render)"
check typst "brew install typst                (design — PDF engine; usually bundled with Quarto)"
check libreoffice "brew install --cask libreoffice  (design — PPTX→PDF for QA; binary may be 'soffice')" soffice
check mjml "npm install -g mjml              (messaging — optional, HTML email only)"

# ---------------------------------------------------------------- 4. tools tier
echo
echo "Tools tier (dumb deterministic CLIs — ADR-004):"
if [ ! -f "$ROOT/tools.yml" ]; then
  echo "  ✗ tools.yml missing — tools tier not scaffolded"
else
  tool_count="$(grep -cE '^\s*-\s*slug:' "$ROOT/tools.yml" 2> /dev/null || echo 0)"
  if [ "$tool_count" -eq 0 ]; then
    echo "  • tools.yml present, no tools registered yet (see tools/README.md)"
  else
    echo "  $tool_count tool(s) registered in tools.yml:"
    # Parse slug + cli + status from tools.yml. POSIX char classes only —
    # BSD awk on macOS doesn't grok \s.
    awk '
      /^[[:space:]]*-[[:space:]]*slug:/ { slug=$3; cli="" }
      /^[[:space:]]*cli:/                { cli=$2 }
      /^[[:space:]]*status:/             {
        printf "    %-22s cli: %-22s status: %s\n", slug, (cli?cli:"-"), $2
      }
    ' "$ROOT/tools.yml" | head -50
  fi

  # Per-tool install.sh — opt-in (the studios install above is the default).
  # Set STUDIOS_INSTALL_TOOLS=1 to chain through every tool's install.sh.
  if [ "${STUDIOS_INSTALL_TOOLS:-}" = "1" ]; then
    echo
    echo "  Installing tool CLIs (STUDIOS_INSTALL_TOOLS=1):"
    for tdir in "$ROOT"/tools/*/; do
      [ -x "$tdir/install.sh" ] || continue
      name="$(basename "$tdir")"
      if "$tdir/install.sh" > /dev/null 2>&1; then
        echo "    ✓ $name"
      else
        echo "    ✗ $name — re-run manually: $tdir/install.sh"
      fi
    done
  else
    echo "  → set STUDIOS_INSTALL_TOOLS=1 ./install.sh to also install tool CLIs"
  fi
fi

echo
echo "Done. Try:"
echo "    /studio <your brief>             (Principal → Producer)"
echo "    /design-studio <file.md>          (design studio directly)"
echo "    /messaging-studio                 (messaging studio directly)"
echo "    /nitpicker-studio <asset>         (nitpicker studio directly)"
echo "    /audience-studio <reader>         (audience studio directly)"
echo "    /commercial-studio <client>       (commercial studio directly)"
echo "    /delivery-studio <engagement>     (delivery studio directly)"
echo "    /architecture-studio <engagement> (architecture studio directly)"
echo "    /context-studio <engagement>      (context studio directly)"
