# agent-skills

Claude Code and Codex plugin with personal skills and guard hooks.

## Skills

Each skill uses the [Agent Skills](https://agentskills.io/specification) layout: `skills/<name>/SKILL.md` with its own `scripts/`, `references/` and `assets/`. A skill refers to its files by a path relative to its directory, so Claude Code and Codex both find them.

- `brainstorm` — turn an idea into a design through one-at-a-time questions (for now a copy of [parMaster/claude-dlc brainstorm](https://github.com/parMaster/claude-dlc/tree/main/plugins/brainstorm), MIT)
- `plan` — intent-level plan in `docs/plans/`: loads the project's skills first, asks whether a migration is needed, never picks the more complex option without asking, checks new names, written in ASD-STE100
- `/amoniac:complete-plan` — for a finished plan or WBS document, writes only its title, Goal and Decisions to `docs/plans/completed/` (`skills/complete-plan/scripts/complete_plan.py`). It refuses a plan with open boxes unless `--force`. You delete the plan yourself
- `review-plan` — finds the plan and runs the full `/amoniac:review` cycle on it
- `backlog` — deferred work in `docs/backlog/`, one file per item, with a `worth: yes | later | no` triage
- `oversight` — scope, Definition of Done and iterations of a multi-plan epic in `docs/plans/wbs-<slug>.md`; starts each iteration with `spawn-session`

`plan`, `review-plan`, the plan checklist, `backlog` and `oversight` are adapted from [parMaster/claude-dlc planning](https://github.com/parMaster/claude-dlc/tree/main/plugins/planning) (MIT): rewritten in ASD-STE100, no commits or `git rm` by the agent, no agterm dependency, no backlog dashboard.
- `helmcheck` — Helm chart rules: workload baseline, values, secrets, migrations and hooks, availability, releases, validation with kubeconform and conftest
- `principles` — KISS/YAGNI, prefer deletion, DRY by the rule of three, fail loudly, test against real dependencies through the public entry point
- `naming` — how to name files, classes, errors, methods and internal methods
- `testing` — test levels, real dependencies, when mocks are allowed, isolation, no sleep, structure
- `go-best-practices` — best practices for writing Go code
- `spawn-session` — hand a task off to a new `claude` or `codex` session in a new herdr terminal, tmux window or kitty tab (adapted from [parMaster/claude-dlc spawn-session](https://github.com/parMaster/claude-dlc/tree/main/plugins/agterm/skills/spawn-session), MIT)

## Review in herdr

```
/amoniac:review                          the diff; two reviewers
/amoniac:review diff codex               the diff; only codex
/amoniac:review plan docs/plans/x.md     a plan; two reviewers
```

Inside a [herdr](https://herdr.dev) terminal, `/amoniac:review` runs a cycle for each reviewer, in a new pane beside you:

```
reviewer 1 = the other agent ─► debate (rounds 1–3) ─► you approve findings
              ─► this session fixes ─► the same reviewer checks the fix (round 4)
              ─► fixed: next │ not fixed: blocked, you decide
reviewer 2 = the agent of this session ─► the same cycle on the fixed code
```

With an agent in the arguments, only that agent reviews. Nothing is fixed before you approve it. Outside herdr, `/amoniac:review` stops.

`skills/review/scripts/debate.py start` builds the prompt, checks the conditions, starts the reviewer from its herdr-core template, sends round 1 and prints the steps for this session. The texts are in `skills/review/assets/`: `debate-*.md`, `diff-review.md`, the plan checklist `plan-review.md` and the templates in `templates/`. `debate.py ask` sends rounds 2 to 4.

The prompt carries the rules, so a reviewer that cannot load skills still gets them:

- skills from `.agents/required-skills.json` (`always`, plus `files` globs that match the changed files); without that file, `principles` and `naming`, plus `go-best-practices`, `testing` or `helmcheck` by file type. `amoniac:` skills are put into the prompt in full; other skills are named for the reviewer to load;
- for a diff, language rules from `skills/review/assets/languages/` (Ruby, JavaScript/TypeScript, Python, shell) by file type;
- for a plan, the plan checklist and the skills in the plan's `**Skills:**` line.

`.agents/review.json` in the project (optional) sets the files that the diff leaves out:

```json
{
  "exclude": ["*.lock", "*.min.js", "vendor/**"]
}
```

`/amoniac:review-plan` finds the plan and runs the same cycle on it.

- Each reviewer starts from a herdr-core template in `~/.config/herdr-core/templates/`: `amoniac-review-claude` or `amoniac-review-codex`.
- The reviewer writes each answer to a file. It can write only in `$XDG_RUNTIME_DIR/amoniac/reviews`: `claude` through `Edit(...)` in `--allowedTools`, `codex` through a read-only permission profile with that one writable folder.
- Then it sends the notice `review-N done` with `hc send`.
- Both run with no permission prompts: `claude` with `--permission-mode dontAsk`, `codex` with `approval_policy=never`. A forbidden action is refused, not asked.
- The prompt and the answers are in `$XDG_RUNTIME_DIR/amoniac/reviews/<author>/<debate>/`, not in the repository.
- The reviewer pane stays open after the cycle. It closes when your session ends.

Run `/amoniac:setup-review` once. It installs the two templates, and adds a rule to `~/.codex/rules/default.rules` that lets only `hc send` run outside the codex sandbox. It asks before each write. `hc send` can type into each of your terminals. `/amoniac:review` refuses to start when a template is missing or old, and names `setup-review`.

In herdr, start codex with `codex --no-daemon`. Without the flag, codex runs commands through its background server, which keeps the environment of the terminal it started in. Then `HC_TERMINAL_ID` is missing, and `/amoniac:review` and `spawn-session` cannot find the terminal of this session.

## Hooks (PreToolUse)

- `block-comments.py` — blocks Write/Edit that add new code comments (override: `CLAUDE_ALLOW_COMMENTS=1`)
- `block-git-writes.py` — allows only read-only git commands in Bash
- `block-git-branches.py` — blocks reading branches and refs from Bash (`git branch`, `symbolic-ref`, `ls-remote`, `describe`, `rev-parse --abbrev-ref`, `log/show/diff --all` or against `origin/...`); the agent works on the checked-out tree and asks when it needs a branch name
- `block-file-writes.py` — blocks file writes from Bash (`sed -i`, `>`, `tee`, heredocs…) outside `/tmp`, and every `eval`. Text in quotes is not taken for a redirect; the code after `sh -c` / `bash -lc` is checked as a command
- `block-output-filters.py` — blocks a pipe that filters command output with `sed`, `awk` or `perl`, or with two or more filters (`grep`, `head`, `tail`, `sort`, `jq`…), and any filter after `gh`, `curl`, `wget` or `npm view`. The agent saves the output to a file in the scratchpad and searches it with Grep or Read. One filter after a local command (`make test 2>&1 | tail -30`) passes
- `go-lookups.py` — blocks Bash, Read and Grep that touch the Go module cache (`pkg/mod`) and `go doc … | grep`; library APIs are read with `go doc <pkg>` and `go doc <pkg>.<Symbol>` (after `go get` when the module is not a dependency yet) or through the LSP tool (gopls). When grep/rg targets Go files, reminds that LSP definition/references are exact for symbols (does not block)
- `allow-debate-commands.py` — lets the review debate run without a permission prompt in each round. It allows only `skills/review/scripts/debate.py` of this plugin, with its absolute path (`env`, `start`, `answer`, and `ask` with one quoted heredoc), `hc wait --children any --json --timeout N` and `hc read ADDRESS [--lines N]`. It never denies: a command in another shape gets the normal permission flow, and a deny from another hook wins
- `remind-skills.py` — when a Write/Edit to a code file adds new files, names, abstractions or tests, reminds the agent to load `naming`, `principles` or `testing` (does not block)
- `required-skills.py` — at session start tells the agent which skills the project requires. Skills under `always` block every tool except `Skill` until they are loaded; skills under `files` block Write/Edit of a file matching the glob until they are loaded. Loads are recorded from the `Skill` tool (PostToolUse) and from typed `/name` commands (UserPromptExpansion). The project lists them in `.agents/required-skills.json`:

  ```json
  {
    "always": ["amoniac:principles", "amoniac:naming"],
    "files": {
      "*.go": ["amoniac:go-best-practices", "golang-pro"],
      "*_test.go": ["amoniac:testing"],
      "charts/**/*.yaml": ["amoniac:helmcheck"]
    }
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
make test
```

It runs each `hooks/*.test.py` and `skills/*/scripts/*.test.py`. One file: `make hooks/block-file-writes.test.py`. `make -k test` shows all failures, not only the first.
