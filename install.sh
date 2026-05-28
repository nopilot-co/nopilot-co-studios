#!/usr/bin/env bash
# Install the Studios plugins.
#
# Two paths, both kept working:
#   1. Marketplace registration (preferred for new installs) — registers this
#      repo as a Claude Code / Cowork plugin marketplace so the three plugins
#      (studios, design-studio, messaging-studio) can be installed/updated via
#      the host's plugin commands.
#   2. Direct symlinks into ~/.claude/plugins (backward-compat) — for hosts/
#      versions that load plugins straight from that directory.
#
# Reports runtime dependency status — does not install system tools for you.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGINS="$HOME/.claude/plugins"
mkdir -p "$PLUGINS"

# ---------------------------------------------------------------- 1. symlinks
link() { # link <target-dir> <plugin-name>
  local target="$1" name="$2" dest="$PLUGINS/$2"
  if [ -L "$dest" ] || [ -e "$dest" ]; then
    echo "  • $name already present ($dest)"
  else
    ln -s "$target" "$dest"
    echo "  ✓ linked $name -> $target"
  fi
}

echo "Installing Studios plugins (symlinks):"
link "$ROOT" "studios"
# Each active studio in studios.yml ships its own plugin; link the ones present.
[ -d "$ROOT/design" ]    && link "$ROOT/design"    "design-studio"
[ -d "$ROOT/messaging" ] && link "$ROOT/messaging" "messaging-studio"

# ---------------------------------------------------------------- 2. marketplace
# `.claude-plugin/marketplace.json` declares the three plugins; register this
# repo with whichever hosts are on PATH. Best-effort: prints the manual command
# if a host's CLI lacks the subcommand or isn't installed.
register_marketplace() { # register_marketplace <host-cli>
  local host="$1"
  if ! command -v "$host" >/dev/null 2>&1; then
    echo "  • $host not on PATH — skip (manual: $host plugin marketplace add $ROOT)"
    return
  fi
  if "$host" plugin marketplace add "$ROOT" >/dev/null 2>&1; then
    echo "  ✓ registered with $host"
  else
    echo "  ! $host did not accept 'plugin marketplace add $ROOT'"
    echo "    run manually (or check 'host plugin --help' for the right command)"
  fi
}

echo
echo "Registering as a plugin marketplace:"
if [ -f "$ROOT/.claude-plugin/marketplace.json" ]; then
  register_marketplace claude
  register_marketplace cowork
else
  echo "  ✗ .claude-plugin/marketplace.json missing — skipping marketplace registration"
fi

# ---------------------------------------------------------------- 3. python pkg
echo
echo "Studio Python packages:"
if [ -f "$ROOT/design/install.sh" ]; then
  echo "  → run 'design/install.sh'     for the design 'studio' CLI (Quarto-backed)"
fi
if [ -x "$ROOT/design/.venv/bin/studio" ]; then
  echo "    ✓ studio CLI present (design/.venv/bin/studio)"
fi
if [ -f "$ROOT/messaging/install.sh" ]; then
  echo "  → run 'messaging/install.sh'  for the messaging 'message' CLI (MJML for HTML email)"
fi
if [ -x "$ROOT/messaging/.venv/bin/message" ]; then
  echo "    ✓ message CLI present (messaging/.venv/bin/message)"
fi

# ---------------------------------------------------------------- 4. runtime deps
echo
echo "Runtime dependencies (for rendering):"
check() { # check <tool> <hint>
  local t="$1" hint="$2"
  if command -v "$t" >/dev/null 2>&1; then
    echo "  ✓ $t"
  else
    echo "  ✗ $t — $hint"
  fi
}
check quarto      "brew install --cask quarto       (design — required to render)"
check typst       "brew install typst                (design — PDF engine)"
check libreoffice "brew install --cask libreoffice  (design — PPTX→PDF for QA; binary may be 'soffice')"
check mjml        "npm install -g mjml              (messaging — optional, HTML email only)"

echo
echo "Done. Try:  /studio <your brief>     (creative-director)"
echo "      or:   /design-studio <file.md> (design studio directly)"
echo "      or:   /messaging-studio        (messaging studio directly)"
