# Move the commands into skills for Claude Code and Codex

**Goal:** Each plugin feature is a skill in the Agent Skills layout that Claude Code and Codex both run, and the debate is the only review.

**Kind of change:** refactor

**Deployed:** not deployed — change in place, no migration. The user installs the plugin again from the folder in Claude Code and in Codex.

**Skills:** `amoniac:principles`, `amoniac:naming`, `amoniac:testing`

## Intent

Codex does not substitute `${CLAUDE_PLUGIN_ROOT}` in skill text. Codex skips a plugin command that contains `$ARGUMENTS`. Thus `/amoniac:review` and `/amoniac:complete-plan` do not exist in Codex, and skills cannot find their scripts. The Agent Skills layout keeps each skill with its `scripts/`, `references/` and `assets/`. Skill text refers to these files by a path relative to the skill directory.

The one-pass review runs `codex exec` or `claude -p` with no window and takes one report. The author session does not argue with the reviewer, so it accepts the report too easily. The debate stays as the only review, and the one-pass review goes.

The user already moved the files:

```
commands/review.md         → skills/review/SKILL.md
commands/complete-plan.md  → skills/complete-plan/SKILL.md
commands/setup-codex.md    → skills/setup-codex/SKILL.md
scripts/review.py, debate.py (+ tests)  → skills/review/scripts/
templates/*                → skills/review/assets/
agents/plan-review.md      → skills/review/assets/plan-review.md (checklist, no frontmatter)
scripts/complete_plan.py (+ test, fixtures) → skills/complete-plan/scripts/
scripts/spawn-session.sh   → skills/spawn-session/scripts/
```

Already done: the asset paths in `review.py` and `debate.py`, the script path in `allow-debate-commands.py`, and the test glob in `Makefile`.

## Decisions

- **Paths in skill text are relative to the skill directory** — the Agent Skills spec and its client guide say this. The skill tells the agent to use the absolute path in commands. Rejected: `${CLAUDE_PLUGIN_ROOT}` (Claude Code only) and a "PLUGIN_ROOT" placeholder (not documented anywhere).
- **The debate is the only review** — the user selected this. Remove the one-pass review: the CLI of `review.py`, `run_agent`, `AGENT_COMMANDS`, `gemini`, and the `agents` and `timeout` keys of `.agents/review.json`. The `exclude` key stays.
- **Move the prompt code of `review.py` into `debate.py`, and delete `review.py`** — after the removal, only `debate.py` uses the prompt code. One script is simpler than a module with one user.
- **Outside tuios and herdr, `review` stops** — it tells the user that the review needs tuios or herdr. `debate.py start` keeps exit 3 for this case.
- **`review` asks for the agent when the arguments name no agent** — the agent is `claude` or `codex`. One single-select question: OTHER (recommended), the agent that this session is not; SELF, the agent of this session.
- **No skill text refers to a script or an asset of another skill** — the docs do not describe it. `review-plan` and `setup-codex` call the `amoniac:review` skill. Rejected: `../review/…` paths, and merging all into one skill. The prompt code in `debate.py` keeps its reads of the `SKILL.md` files of other skills, because it puts their rules in the prompt (`build_rules`).
- **`review-plan` hands the review to `amoniac:review`** — it calls `amoniac:review` with `plan PLAN_FILE`. Then `review-plan` applies the findings in its own Step 3. Its own reviewer question goes.
- **Remove the Opus and Sonnet reviewers from `review-plan`** — they need a Claude subagent, and Codex has none. The user selected this.
- **`review` gets the mode `codex-rules`** — it runs `scripts/debate.py codex-rules` and prints the two rule lines. `setup-codex` keeps its steps and gets the lines from this mode.
- **Keep `$ARGUMENTS` in skill text** — Claude Code substitutes it in skills. Codex shows it as text, and the arguments are in the user message. Codex skips `$ARGUMENTS` only in commands, not in skills.
- **The `name` of each skill is the name of its directory** — the Agent Skills spec requires this.

## Constraints / out of scope

- The command names stay: `/amoniac:review`, `/amoniac:complete-plan`, `/amoniac:setup-codex`, `/amoniac:review-plan`, `/amoniac:spawn-session`.
- The debate flow, the prompt text and the hooks do not change, except the script path.
- A debate without a window is a separate plan, if the user wants it.
- Do not change `docs/plans/` files of other plans.

## Traps

- `review.test.py` checks the prompt through the stdin of a fake agent. Move the prompt checks to `debate.test.py`: it can read `review-prompt.md` in the debate directory. Delete only the checks of the one-pass review.
- `allow-debate-commands.py` allows only `python3 "<plugin root>/skills/review/scripts/debate.py" …` with an absolute path. A relative path or `cd` into the skill directory gets a permission prompt in each round (`strip_script`).
- `debate.py` prints the debate steps with `{{script}}`, the absolute path of `debate.py` (`start`). These steps need no change.
- `debate.py codex-rules` exits 3 outside tuios and herdr. `setup-codex` must keep that branch.
- `skills/plan/SKILL.md` says "The `plan-review` agent checks the same items". No agent exists after this change.
- Codex runs the plugin from a cache copy, `~/.codex/plugins/cache/…/0.5.0/`. It shows old text until the user installs the plugin again.

## Definition of Done

- [x] The current prompt checks pass before the edits and again after them — proof: `make -k test` both times; the prompt checks of `review.test.py` pass in `debate.test.py` with the same expected text.
- [x] `review.py` and the one-pass review do not exist — proof: no `review.py`; `grep -rn "codex exec\|claude -p\|gemini"` over `skills/` and `README.md` finds no review use.
- [x] No `SKILL.md` and no README line refers to an old plugin path: `${CLAUDE_PLUGIN_ROOT}`, "PLUGIN_ROOT", `commands/`, `agents/plan-review.md`, the plugin `templates/` or `scripts/` at the plugin root — proof: read the matches of `grep -rn` over `skills/*/SKILL.md` and `README.md`. Project paths such as `.agents/` and Helm `templates/` stay.
- [x] Each `SKILL.md` has a `name` equal to its directory — proof: compare `name:` lines with directory names.
- [x] `review-plan` reads no file of `review` and offers no Opus or Sonnet — proof: read `skills/review-plan/SKILL.md`.
- [ ] In a new Claude Code session in herdr, `/amoniac:review` with no arguments asks for the agent and runs a codex debate with no permission prompt for `debate.py` — proof: one debate run.
- [ ] Outside tuios and herdr, `/amoniac:review` stops and names tuios and herdr — proof: one run in plain kitty.
- [ ] In a new Claude Code session, `/amoniac:review-plan` runs a debate on a plan and applies the findings — proof: one run.
- [ ] In Codex, after the user installs the plugin again, `review`, `complete-plan` and `setup-codex` exist as skills — proof: the `/skills` list in Codex.
- [ ] In Codex in herdr, `setup-codex` reports that codex is set up — proof: one run.
- [ ] In Codex in herdr, `review` runs a debate with `claude` — proof: one run.
- [ ] In Codex, `review-plan` runs a debate on a plan and applies the findings — proof: one run.
- [ ] `complete-plan` writes the completed plan in Claude Code and in Codex — proof: one run in each, on a test plan.
- [x] `spawn-session` opens a new herdr tab with the prompt in Claude Code — proof: `spawn-make-test-2` (`t3q`) in the tab `agent-skills / 2`.
- [ ] `spawn-session` opens a new herdr tab with the prompt in Codex — proof: one run.
- [x] ➕ `spawn-session` starts the herdr terminal through `hc run` with the `herdr.space` label of this session, not through `herdr-app` — proof: the run above; the script does not call `herdr-app`.

## Work order

1. Run `make -k test` and record the result.
2. Move the prompt checks to `debate.test.py`, then the prompt code to `debate.py`. Ask the user to delete `review.py` and its test.
3. Change the text of `review`, `complete-plan`, `setup-codex` and `spawn-session`.
4. Change `review-plan` and the line in `skills/plan/SKILL.md`.
5. Change the README.
6. Run `make -k test` again, then the manual checks in Claude Code and in Codex.

## Wrap-up

- [x] all tests pass: `make -k test`
- [x] README.md shows the new layout, the paths and the debate as the only review
- After all boxes: run `/amoniac:complete-plan`. It keeps the title, Goal and Decisions in `docs/plans/completed/`. The user deletes the plan with `! rm`.

## Post-Completion

- The user deletes the empty directories: `! rmdir commands scripts agents`.
- The user installs the plugin again in Claude Code and in Codex.
