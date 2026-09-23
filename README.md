# agent-skills

Claude Code plugin with personal skills and guard hooks.

## Skills

- `brainstorm` — turn an idea into a design through one-at-a-time questions
- `plan` — numbered plan, list of files, stop before implementing
- `helmcheck` — validate Helm charts with `helm template`, report all errors at once

## Hooks (PreToolUse)

- `block-comments.py` — blocks Write/Edit that add new code comments (override: `CLAUDE_ALLOW_COMMENTS=1`)
- `block-git-writes.py` — allows only read-only git commands in Bash
- `block-file-writes.py` — blocks file writes from Bash (`sed -i`, `>`, `tee`, heredocs…) outside `/tmp`

## Install

```
/plugin marketplace add amoniacou/agent-skills
/plugin install agent-skills@amoniac
```

Update on other machines:

```
/plugin marketplace update amoniac
```

## Test

```
python3 hooks/block-file-writes.test.py
```
