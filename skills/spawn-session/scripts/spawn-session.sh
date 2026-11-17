#!/usr/bin/env bash
set -euo pipefail

USAGE="usage: spawn-session.sh <claude|codex> <cwd> <session-name> [cli-flags] < prompt"
RUNTIME="${1:?$USAGE}"
CWD="${2:?$USAGE}"
SESSION_NAME="${3:?$USAGE}"
CLI_FLAGS="${4:-}"

case "$RUNTIME" in
  claude | codex) ;;
  *)
    echo "spawn-session: unknown runtime: $RUNTIME" >&2
    exit 1
    ;;
esac

PROMPT_FILE=$(mktemp "${TMPDIR:-/tmp}/spawn-session.XXXXXX")
cat >"$PROMPT_FILE"

if [ ! -s "$PROMPT_FILE" ]; then
  echo "spawn-session: empty prompt on stdin" >&2
  exit 1
fi

FIRST_LINE=$(head -n1 "$PROMPT_FILE" | tr '[:upper:]' '[:lower:]')
case "$FIRST_LINE" in
  spawn*session* | spawn*agent* | start*session* | start*agent* | "kick off"*session* | "kick off"*agent* | delegate*session* | delegate*agent* | "hand this off"* | "hand it off"*)
    echo "spawn-session: line 1 of $PROMPT_FILE reads as a hand-off description, not a task. Rewrite it as an imperative and rerun with < $PROMPT_FILE" >&2
    exit 1
    ;;
esac

case "$PROMPT_FILE" in
  *"'"*)
    echo "spawn-session: prompt file path contains a single quote: $PROMPT_FILE" >&2
    exit 1
    ;;
esac

COMMAND="$RUNTIME${CLI_FLAGS:+ $CLI_FLAGS} \"\$(cat '$PROMPT_FILE')\""

if [ "${TUIOS_ENV:-}" = 1 ] && command -v tuios >/dev/null 2>&1; then
  WINDOW=$(tuios new-window "$SESSION_NAME" -s "$TUIOS_SESSION" --cwd "$CWD" --no-focus --print-id)
  tuios send-text -s "$TUIOS_SESSION" -w "$WINDOW" "$COMMAND"
  tuios send-keys -s "$TUIOS_SESSION" -w "$WINDOW" Enter
  echo "tuios window: $SESSION_NAME"
elif [ -n "${HC_TERMINAL_ID:-}" ] && command -v hc >/dev/null 2>&1; then
  NAME=$(printf '%s' "$SESSION_NAME" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9_-' '-' | sed 's/^-*//; s/-*$//' | cut -c1-32)
  SPACE=$(hc get "$HC_TERMINAL_ID" --json | python3 -c 'import json, sys; print(json.load(sys.stdin).get("labels", {}).get("herdr.space", ""))')
  STARTED=$(hc run --bg --json --no-parent --outlive-parent --name "${NAME:-spawn}" ${SPACE:+--label "herdr.space=$SPACE"} --cwd "$CWD")
  TERMINAL=$(printf '%s' "$STARTED" | python3 -c 'import json, sys; print(json.load(sys.stdin)["address"])')
  hc send "$TERMINAL" "$COMMAND" >/dev/null
  echo "herdr terminal: ${NAME:-spawn} ($TERMINAL)"
elif [ -n "${TMUX:-}" ] && command -v tmux >/dev/null 2>&1; then
  PANE=$(tmux new-window -d -c "$CWD" -n "$SESSION_NAME" -P -F '#{pane_id}')
  tmux send-keys -t "$PANE" -l "$COMMAND"
  tmux send-keys -t "$PANE" Enter
  echo "tmux window: $SESSION_NAME"
elif [ -n "${KITTY_WINDOW_ID:-}" ] && command -v kitty >/dev/null 2>&1; then
  if [ -z "${KITTY_LISTEN_ON:-}" ]; then
    echo "spawn-session: kitty remote control socket not set — add 'allow_remote_control socket-only' and 'listen_on unix:/tmp/kitty' to kitty.conf and restart kitty" >&2
    exit 1
  fi
  WINDOW=$(kitty @ launch --type=tab --keep-focus --cwd "$CWD" --tab-title "$SESSION_NAME")
  printf '%s\r' "$COMMAND" | kitty @ send-text --match "id:$WINDOW" --stdin
  echo "kitty tab: $SESSION_NAME"
else
  echo "spawn-session: not available — not running inside tuios, herdr, tmux or kitty" >&2
  exit 1
fi
