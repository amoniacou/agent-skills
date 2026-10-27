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
- `spawn-session` — hand a task off to a new `claude` or `codex` session in a new tmux window or kitty tab (adapted from [parMaster/claude-dlc spawn-session](https://github.com/parMaster/claude-dlc/tree/main/plugins/agterm/skills/spawn-session), MIT)

## Hooks (PreToolUse)

- `block-comments.py` — blocks Write/Edit that add new code comments (override: `CLAUDE_ALLOW_COMMENTS=1`)
- `block-git-writes.py` — allows only read-only git commands in Bash
- `block-file-writes.py` — blocks file writes from Bash (`sed -i`, `>`, `tee`, heredocs…) outside `/tmp`
- `remind-skills.py` — when a Write/Edit to a code file adds new files, names, abstractions or tests, reminds the agent to load `naming`, `principles` or `testing` (does not block)
- `required-skills.py` — blocks Write/Edit until the skills the project requires for that file are loaded in the session. Loads are recorded from the `Skill` tool (PostToolUse) and from typed `/name` commands (UserPromptExpansion). The project lists them in `.agents/required-skills.json`, a map from file glob to skill names:

  ```json
  {
    "*.go": ["amoniac:principles", "amoniac:go-best-practices", "golang-pro"],
    "*_test.go": ["amoniac:testing"],
    "charts/**/*.yaml": ["amoniac:helmcheck"]
  }
  ```

## Install

```
/plugin marketplace add amoniacou/agent-skills
/plugin install amoniac@amoniac-agent-skills
```

Update on other machines:

```
/plugin marketplace update amoniac-agent-skills
```

For development, add the checkout as a marketplace instead of GitHub; it loads in place, and edits apply after `/reload-plugins` or a new session:

```
/plugin marketplace add /path/to/agent-skills
/plugin install amoniac@amoniac-agent-skills
```

## Test

```
python3 hooks/block-file-writes.test.py
python3 hooks/remind-skills.test.py
python3 hooks/required-skills.test.py
```
