# agent-skills

Claude Code plugin with personal skills and guard hooks.

## Skills

- `brainstorm` — turn an idea into a design through one-at-a-time questions (for now a copy of [parMaster/claude-dlc brainstorm](https://github.com/parMaster/claude-dlc/tree/main/plugins/brainstorm), MIT)
- `plan` — numbered plan, list of files, stop before implementing
- `helmcheck` — Helm chart rules: workload baseline, values, secrets, migrations and hooks, availability, releases, validation with kubeconform and conftest
- `principles` — KISS/YAGNI, prefer deletion, DRY by the rule of three, fail loudly, test against real dependencies
- `naming` — how to name files, classes, errors, methods and internal methods
- `testing` — test levels, real dependencies, when mocks are allowed, isolation, no sleep, structure
- `go-best-practices` — best practices for writing Go code

## Hooks (PreToolUse)

- `block-comments.py` — blocks Write/Edit that add new code comments (override: `CLAUDE_ALLOW_COMMENTS=1`)
- `block-git-writes.py` — allows only read-only git commands in Bash
- `block-file-writes.py` — blocks file writes from Bash (`sed -i`, `>`, `tee`, heredocs…) outside `/tmp`
- `remind-skills.py` — when a Write/Edit to a code file adds new files, names, abstractions or tests, reminds the agent to load `naming`, `principles` or `testing` (does not block)

## Install

```
/plugin marketplace add amoniacou/agent-skills
/plugin install amoniac@skills
```

Update on other machines:

```
/plugin marketplace update skills
```

## Test

```
python3 hooks/block-file-writes.test.py
python3 hooks/remind-skills.test.py
```
