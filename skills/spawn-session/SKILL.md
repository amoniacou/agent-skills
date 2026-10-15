---
name: spawn-session
description: Hand off a task to a new, independent `claude` or `codex` session in a new tmux window or kitty tab — not a background subagent. Activates on "spawn a new session for this", "hand this off to a new session", "start a separate session for this job", "delegate this to a new terminal session", "run this in a separate/parallel session", "spin up a session for this slice", or when the user is slicing a larger job into pieces to hand off one at a time.
argument-hint: "[task description]"
allowed-tools: Bash, AskUserQuestion, ListAgents
---

# Spawn a Task in a Separate Session

Hand a task prompt to a new `claude` or `codex` process in a new tmux window
(when this session runs inside tmux) or a new kitty tab (inside kitty). The
user can switch to it and drive it, and it keeps running after this
conversation ends. Not an `Agent` subagent: those are hidden and die with this
conversation.

The command is typed into the new window's own shell, so it runs exactly as
if the user typed it: their shell (bash, zsh or fish 3.4+), their rc files,
their `PATH`. When the CLI exits, the user is back at that shell.

## Step 1: Resolve the task prompt

The task prompt passed as the argument, if any:

<task-prompt>
$ARGUMENTS
</task-prompt>

- If it isn't empty, use it verbatim, every line of it.
- Otherwise write a self-contained prompt: what to do, which files/areas are
  involved, how to verify it's done. The new session cannot see this
  conversation.
- Line 1 must be the task itself as an imperative ("Fix the parser…"), not a
  description of the hand-off ("Spawn a session to…").

## Step 2: Name the session

A short window/tab title, e.g. `Spawn: <slug>`. Slices sharing a stateful
resource (database, lock, port): spawn one at a time, not back to back.

## Step 3: Choose a runtime

Ask with `AskUserQuestion` — question "Which CLI should the new session run?",
header "Runtime", single-select, options:

- **Claude** (Recommended) — a `claude` process, matching this session
- **Codex** — a `codex` process (Codex CLI)

## Step 4: Choose a model

Check the Step 3 answer first — Codex gets its own question.

**Claude:** ask with `AskUserQuestion` — question "Which model should the new
session use?", header "Model", single-select, options:

- **Inherit** — whatever `claude` launches with by default
- **Opus** — most capable; complex or subtle work
- **Sonnet** — faster and cheaper; straightforward tasks
- **Haiku** — fastest and cheapest; simple mechanical changes

**Codex:** ask with `AskUserQuestion` — question "Which model should the new
Codex session use?", header "Model", single-select, options:

- **Inherit** (Recommended) — Codex uses its configured default model
- **Enter a model name** — the exact Codex model name, typed via "Other"

`CLI_FLAGS` is `--model <lower-cased label>` for a Claude tier,
`--model <exact text the user typed>` for Codex, or nothing for **Inherit**.
Never guess a Codex model name.

## Step 5: Spawn

**Claude runtime only:** call `ListAgents` first. Its first line reads
"This session is <name> [<ref>]"; `PARENT_NAME` is the bare `<name>`. End the
prompt with this footer. It carries no instruction on purpose: "report back"
wording makes spawned sessions message this one unasked. Codex gets no
footer, nor does a Claude spawn when `ListAgents` gives no name.

```
---
Spawned from Claude session PARENT_NAME.
```

Run one Bash call. The prompt goes in on stdin through a **quoted** heredoc
(`<<'PROMPT_EOF'`) so it isn't shell-expanded. Don't pre-check tmux or kitty;
the script does that and exits non-zero with a reason.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/spawn-session.sh" RUNTIME "$PWD" "SESSION_NAME" "CLI_FLAGS" <<'PROMPT_EOF'
<task prompt from Step 1>
<footer, Claude runtime with a PARENT_NAME only>
PROMPT_EOF
```

`RUNTIME` is `claude` or `codex`. Drop the `"CLI_FLAGS"` argument for
**Inherit**.

If the script rejects line 1, it names the saved prompt file. `Edit` just
line 1 of that file into an imperative and rerun the same command with
`< <that file>` in place of the heredoc.

## Step 6: Report the outcome

Exit 0: the stdout line says where it opened (`tmux window: <name>` or
`kitty tab: <name>`). Report that, the runtime, and the model unless Inherit.
Non-zero: quote stderr. If it says "not available", ask whether they want a
background subagent instead of silently falling back to one. If it says the
kitty socket is not set, relay the `kitty.conf` lines from the message and
that kitty needs a full restart.

Either way, stop — do not implement the task in this session.
