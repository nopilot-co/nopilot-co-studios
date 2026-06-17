#!/usr/bin/env bash
# Studios reflection gate (soft). Shipped via hooks/hooks.json (plugin
# auto-discovery). Three modes:
#
#   --session-start : record this session's start (mtime marker keyed by id),
#                     and garbage-collect old markers.
#   --subagent      : no-op (reflection is a top-level, engagement-close concern).
#   (default, Stop) : if a studio run happened THIS session but no learning was
#                     logged since, emit ONE non-blocking reminder. Never blocks.
#
# "A studio run happened this session" = the activity marker
# (.studios/last-studio-run, touched by the Producer when it starts routing) is
# newer than this session's start marker. The LLM can't know its own session_id,
# so the SessionStart hook owns the id-keyed marker and the Producer only touches
# a plain activity file — the gate compares their mtimes.
#
# All paths resolve from the plugin root (this script's parent dir, or
# $CLAUDE_PLUGIN_ROOT) so it travels with the clone — no hardcoded user paths.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$SCRIPT_DIR")}"
MARK_DIR="$PLUGIN_ROOT/.studios"
LEARNINGS_DIR="$PLUGIN_ROOT/learnings"
ACTIVITY="$MARK_DIR/last-studio-run"

MODE="${1:-stop}"
INPUT="$(cat || true)"

_field() {
  printf '%s' "$INPUT" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('$1',''))
except Exception: print('')" 2>/dev/null || echo ""
}

SESSION_ID="$(_field session_id)"

if [[ "$MODE" == "--session-start" ]]; then
  mkdir -p "$MARK_DIR"
  [[ -n "$SESSION_ID" ]] && : > "$MARK_DIR/started-$SESSION_ID"
  # Keep .studios/ from growing unbounded.
  find "$MARK_DIR" -maxdepth 1 -type f \( -name 'started-*' -o -name 'nudged-*' \) \
    -mtime +2 -delete 2>/dev/null || true
  exit 0
fi

# SubagentStop is intentionally silent.
[[ "$MODE" == "--subagent" ]] && exit 0

# --- Stop gate ---
STOP_ACTIVE="$(_field stop_hook_active)"
[[ "$STOP_ACTIVE" == "true" || "$STOP_ACTIVE" == "True" ]] && exit 0   # loop-guard
[[ -z "$SESSION_ID" ]] && exit 0

STARTED="$MARK_DIR/started-$SESSION_ID"
NUDGED="$MARK_DIR/nudged-$SESSION_ID"
[[ -f "$STARTED" ]] || exit 0     # SessionStart didn't run → fail-open
[[ -f "$NUDGED" ]] && exit 0      # already nudged once this session

# A studio run happened this session iff activity post-dates this session start.
[[ -f "$ACTIVITY" ]] || exit 0
[[ "$ACTIVITY" -nt "$STARTED" ]] || exit 0

# Satisfied if any learning was written/updated after the studio run.
if [[ -d "$LEARNINGS_DIR" ]] && \
   find "$LEARNINGS_DIR" -type f -name '*.md' ! -name 'README.md' -newer "$ACTIVITY" 2>/dev/null \
   | grep -q .; then
  exit 0
fi

: > "$NUDGED"
printf '%s\n' '{"systemMessage":"Studios reflection gate: a studio run happened this session but no learning was logged. Before wrapping up, reflect on how the plugin/studio itself could improve and run `learnings add ...` (or `learnings none ...` if there is genuinely nothing). See skills/reflect/SKILL.md."}'
exit 0
