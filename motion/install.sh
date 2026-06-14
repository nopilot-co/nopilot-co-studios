#!/usr/bin/env bash
# Install motion-studio plugin: symlink + workspace + dependency check.
set -euo pipefail

PLUGIN_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_LINK="$HOME/.claude/plugins/motion-studio"
CONTEXT_ROOT="$HOME/context/studios/motion"

echo "==> motion-studio installer"
echo "    source: $PLUGIN_SRC"
echo "    link:   $PLUGIN_LINK"
echo "    workspace: $CONTEXT_ROOT"
echo

# 1. Symlink the plugin into ~/.claude/plugins/
mkdir -p "$(dirname "$PLUGIN_LINK")"
if [[ -L "$PLUGIN_LINK" ]]; then
  current="$(readlink "$PLUGIN_LINK")"
  if [[ "$current" == "$PLUGIN_SRC" ]]; then
    echo "✓ symlink already points to $PLUGIN_SRC"
  else
    echo "! symlink exists pointing to $current — replacing"
    rm "$PLUGIN_LINK"
    ln -s "$PLUGIN_SRC" "$PLUGIN_LINK"
    echo "✓ symlink updated"
  fi
elif [[ -e "$PLUGIN_LINK" ]]; then
  echo "✗ $PLUGIN_LINK exists and is not a symlink — refusing to overwrite"
  exit 1
else
  ln -s "$PLUGIN_SRC" "$PLUGIN_LINK"
  echo "✓ symlink created"
fi

# 2. Create the workspace root
mkdir -p "$CONTEXT_ROOT"
echo "✓ workspace ready: $CONTEXT_ROOT"

# 3. Check runtime dependencies
echo
echo "==> dependency check"
missing=()

if ! command -v brew > /dev/null 2>&1; then
  echo "  ⚠ Homebrew not found — install from https://brew.sh first to get the tools below"
fi

check() {
  local name="$1" install_hint="$2"
  if command -v "$name" > /dev/null 2>&1; then
    echo "  ✓ $name"
  else
    echo "  ✗ $name — install with: $install_hint"
    missing+=("$name")
  fi
}

check node "brew install node"
check ffmpeg "brew install ffmpeg"

# Find a Python ≥ 3.10 — prefer newer
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" > /dev/null 2>&1; then
    ver="$($cand -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2> /dev/null)"
    major="${ver%.*}"
    minor="${ver#*.}"
    if ((major > 3)) || { ((major == 3)) && ((minor >= 10)); }; then
      PY="$cand"
      echo "  ✓ python ($cand → $ver)"
      break
    fi
  fi
done
if [[ -z "$PY" ]]; then
  echo "  ✗ python ≥ 3.10 not found — install with: brew install python@3.12"
  missing+=("python>=3.10")
fi

# 4. Install the Python orchestrator (editable)
echo
echo "==> installing motion Python package (editable)"
if [[ -n "$PY" ]]; then
  set +e
  $PY -m pip install --user -e "$PLUGIN_SRC" 2>&1 | tail -10
  pip_rc=${PIPESTATUS[0]}
  set -e
  if ((pip_rc == 0)); then
    echo "✓ motion package installed (using $PY)"
  else
    echo "✗ pip install failed (rc=$pip_rc) — symlink + workspace are still set up"
    echo "  retry manually: $PY -m pip install --user -e $PLUGIN_SRC"
  fi
else
  echo "✗ skipped — no Python ≥ 3.10 available"
fi

echo
echo "  Providers (optional, for the digital-twin presenter) are cloud services —"
echo "  set DID_API_KEY and ELEVENLABS_API_KEY in your environment to enable them."
echo

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "⚠ install incomplete — missing: ${missing[*]}"
  echo "  install the items above, then run: motion doctor"
  exit 0
fi

echo "✓ motion-studio installed."
echo "  Next: run  motion doctor  (or open a Claude Code session and run /motion-studio)"
