# Allow the debate commands without a permission prompt

**Goal:** Let the author session run the commands of a review debate without a permission prompt, and allow nothing else.

**Kind of change:** feature

**Deployed:** n/a — nothing is stored or shared

**Skills:** `amoniac:principles`, `amoniac:naming`, `amoniac:testing`

## Intent

`allowed-tools` in `commands/review.md` applies only in the turn of the command. The notice `review-N done` starts a new turn. Thus `debate.py answer`, `debate.py ask`, `hc wait` and `hc read` ask the user for a permission in each round. A new PreToolUse hook allows only these commands in their exact shapes. Every other command gets no decision, and the normal permission flow applies.

## Decisions

- **A plugin hook, not rules in `~/.claude/settings.json`.** The user selected the hook. A settings rule needs the plugin path, and that path is different for a marketplace install.
- **The hook is `hooks/allow-debate-commands.py`.** The user selected the name over `approve-debate.py`. It runs in the Bash matcher of `hooks/hooks.json`. It uses `hooks/bash_hook.py` where that module helps.
- **The pattern is `approve-overlay.sh` of agterm** (parMaster/claude-dlc, `plugins/agterm/scripts/approve-overlay.sh`). The hook never denies. A command that does not match gets no output.
- **Allowed shapes:**

  | command | allowed when |
  |---|---|
  | `python3 SCRIPT env` | nothing follows `env` |
  | `python3 SCRIPT start ARGS` | `ARGS` has no shell metacharacter: `; & \| < > $` backtick, newline |
  | `python3 SCRIPT answer DIRECTORY N` | `N` is a number; `DIRECTORY` has no metacharacter |
  | `python3 SCRIPT ask REVIEWER DIRECTORY N <<'TAG'` + body + `TAG` | one quoted heredoc; the end marker is the last line; no line of the body equals the marker |
  | `hc wait --children any --json --timeout N` | `N` is a number |
  | `hc read ADDRESS` or `hc read ADDRESS --lines N` | `ADDRESS` matches `[a-z0-9/_-]+`; `N` is a number |

  `SCRIPT` is `$CLAUDE_PLUGIN_ROOT/scripts/debate.py`, quoted or not, or the literal `${CLAUDE_PLUGIN_ROOT}` spelling. A script with the same name in another directory is not allowed.
- **A deny from a blocking hook wins.** The Claude Code hooks reference (PreToolUse decision control) says: "When multiple PreToolUse hooks return different decisions, precedence is `deny` > `defer` > `ask` > `allow`." Deny and ask rules in settings stay in effect too.
- **A quoted heredoc is safe.** The shell expands nothing in it. The body is plain text for `debate.py ask`.

## Constraints / out of scope

- The five blocking Bash hooks keep their results. A command that a blocking hook denies stays denied.
- No allow for `codex-rules`, `hc send`, `hc kill` or any other `hc` command.
- No `asyncRewake` hook. That is a later plan.

## Traps

- **Allow and deny from two hooks.** Check in the Claude Code hook docs which decision wins. The blocking hooks must win. If allow wins, stop and tell the user.
- **`block-file-writes` can deny an `ask` heredoc.** It denies `python3` with `<<` when the text has `.write`, `open(…'w'` and similar (`hooks/block-file-writes.py`, `INTERPRETER_WRITE`). A finding that quotes such code is denied. Tell the user in the debate steps: put code in the question as a file and line, not as text.
- **`CLAUDE_PLUGIN_ROOT` must be set** in the hook environment. Without it, allow nothing.
- **The command the author runs uses the resolved path in double quotes.** `templates/debate-author.md` and `templates/debate-wait-herdr.md` write `python3 "{{script}}"`. The hook must match this form.
- **`hc wait` runs with `run_in_background`.** The command text is the same. Do not depend on the background flag.

## Definition of Done

- [x] Each allowed shape gets `permissionDecision: allow` — proof: `hooks/allow-debate-commands.test.py`, one case for each row of the table.
- [x] Changed shapes get no output — proof: test cases for:
  - `; rm x` or `&& x` after an allowed command;
  - `$(…)` or a backtick in an argument;
  - an unquoted heredoc;
  - a command after the end marker;
  - a body line equal to the end marker;
  - `debate.py` in another directory;
  - other `hc` subcommands and options.
- [x] A command that a blocking hook denies stays denied — proof: the hook docs, written in Decisions.
- ➕ [x] The debate steps tell the author to name code by file and line, not to quote it — proof: `templates/debate-author.md`.
- [ ] A live herdr debate runs rounds 1–2 with no permission prompt — proof: `/amoniac:review diff codex --debate` with a wrong finding.

## Wrap-up

- [ ] all tests pass: `make test`
- [ ] README.md lists the hook in "Hooks (PreToolUse)"
- After all boxes: run `/amoniac:complete-plan`. It keeps the title, Goal and Decisions in `docs/plans/completed/`. The user deletes the plan with `! rm`.
