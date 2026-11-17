---
name: review
description: Review the uncommitted diff, or a plan, in a debate with one reviewer, claude or codex, in a pane beside this session (tuios or herdr)
argument-hint: "[diff | plan <file>] [claude | codex] | codex-rules"
allowed-tools: Bash(python3:*), Bash(tuios:*), Bash(hc:*), Read, AskUserQuestion
---

# Review

One agent, `claude` or `codex`, reviews in a new pane beside this session, in tuios or herdr. This session argues with it about each wrong finding.

Paths in this skill are relative to the directory of this SKILL.md. In commands, use the absolute path. `DEBATE` is the absolute path of `scripts/debate.py`.

The arguments are: $ARGUMENTS

## Rule lines for codex

If the arguments are `codex-rules`, run `python3 "DEBATE" codex-rules`. Show the output and the exit code. Stop.

## Select the reviewer

Run `python3 "DEBATE" env`. If it prints `none`, tell the user that the review needs tuios or herdr. Stop.

If the arguments name no agent, `claude` or `codex`, ask with AskUserQuestion, header "Reviewer", single-select:

- **OTHER** (Recommended) — the agent that this session is not: `codex` in a claude session, `claude` in a codex session.
- **SELF** — the agent of this session.

`ARGS` is the arguments with the selected agent at the end. With no subject in the arguments, `ARGS` starts with `diff`.

## Start the debate

Run:

```bash
python3 "DEBATE" start ARGS
```

The script checks the conditions, saves the prompt, starts the reviewer and sends round 1. Then it prints the steps of the debate.

| exit | do |
|---|---|
| 0 | do the printed steps |
| 4 | do the printed steps, from Step 0 |
| 1 | tell the user that there are no changes to review; stop |
| 2 | show the lines that start with `debate:`; stop |
| 3 | tell the user that the review needs tuios or herdr; stop |
