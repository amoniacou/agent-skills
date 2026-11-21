# Review in herdr: approval, fix check and two reviewers

**Goal:** `/amoniac:review` runs a full cycle in herdr: debate, approval by the user, fix, and a fix check by the same reviewer, for two reviewers in sequence.

**Kind of change:** feature

**Deployed:** not deployed — change in place, no migration. Only the user uses the plugin.

**Skills:** `amoniac:principles`, `amoniac:naming`, `amoniac:testing`

## Intent

Now the debate stops with a summary to the user. Nobody approves the findings before the fix. The reviewer never sees the fix. The user starts the second reviewer by hand. The user works only in herdr, so tuios support is dead code.

The change gives one cycle for each reviewer. The other agent reviews first. Then the agent of this session reviews the fixed code.

Before:

```
review ─► reviewer (asked) ─► debate ─► summary ─► stop
```

After:

```
review ─► reviewer 1 = other agent ─► debate ─► user approves findings
              ─► this session fixes ─► same reviewer: fix check (1 round)
              ─► agreed: next │ not agreed: blocked, the user decides
          reviewer 2 = same agent ─► the same cycle on the fixed code
```

## Decisions

- **herdr only** — the user selected this. Remove tuios from `debate.py`, its assets, `allow-debate-commands.py`, the tests, `review`, `spawn-session` and README. `spawn-session` keeps tmux and kitty.
- **Reviewer roles are herdr-core templates** — the user selected this. This reverses the "no template" decision of the 2026-11-12 herdr plan. Names: `amoniac-review-claude` and `amoniac-review-codex`. The prefix keeps them apart from the templates of the user in `~/.config/herdr-core/templates/`.
- **One fixed folder for all debates** — a template `command` is a fixed string, so it cannot name the folder of one debate. The writable folder is `$XDG_RUNTIME_DIR/amoniac/reviews`, with one subfolder for each debate. herdr-core runs `command` through a shell: quotes work, and `$XDG_RUNTIME_DIR` expands outside single quotes (a test template showed this). Thus the templates are static files with `$XDG_RUNTIME_DIR` in them. The user selected this. Rejected: answers through `hc send` (long text in the terminal input); no template command (templates then add nothing).
- **The template body holds the role**: read-only review, the output format, write the answer to the given file, then `hc send` the notice. The first message holds the author address and the debate folder.
- **`setup-codex` becomes `setup-review`** — the user selected this name. It adds the codex rule as now, and it installs the two templates. It asks before each write. It reports "set up" when the files are already the same.
- **`debate.py templates` prints the two templates from `assets/`** — the same pattern as `codex-rules`. `review` gets the mode `templates`. `setup-review` uses the modes `codex-rules` and `templates`, and reads no file of `review`.
- **`debate.py start` refuses when a template is missing or different** — it tells the user to run `/amoniac:setup-review`. The same pattern as the check of the codex rule.
- **Two reviewers without a question** — the user selected this. The other agent goes first, then the agent of this session. If the arguments name one agent, only that agent reviews. The question OTHER/SELF goes.
- **The user approves each finding before the fix** — one multi-select question with the accepted findings, plus one question for each disputed finding. Only approved findings are fixed.
- **The fix check is round 4 of the same reviewer** — `debate.py ask` sends it as now. The question names the fixed findings. The reviewer replies FIXED X or NOT FIXED X with a reason. No second fix round.
- **"blocked" when the fix check does not agree** — this session shows both views and asks the user. Then the next reviewer starts, or the cycle stops, as the user tells.
- **`review` fixes plans too** — for `plan`, the fix changes the plan at its level, in ASD-STE100, as `review-plan` Step 2 tells now. That text moves into `review`. `review-plan` keeps Step 0 (find the plan) and calls `review` with `plan PLAN_FILE`.

## Constraints / out of scope

- The prompt text, the skill rules in the prompt and `.agents/review.json` do not change.
- Codex in herdr runs with `--no-daemon` (README says this). Finding the terminal of a codex session that runs with the daemon is out of scope.
- No implementation agents and no worktrees, as in the herdr article. Only review.
- Do not change `docs/plans/` files of other plans.

## Traps

- The codex reviewer needs `--no-daemon` in the template `command`. Without it, its `hc send` runs outside hc (`build_herdr_agent`).
- ➕ Do not give `--add-dir` to the claude template. claude then shows a trust dialog for the folder at each start. The `Edit(//…)` rule is enough for the answer files (a `claude -p` test showed this).
- The claude template must keep `--permission-mode dontAsk`, and the codex template `approval_policy=never`. Else the reviewer waits for a permission in a pane that nobody watches (`build_claude_options`, `build_codex_options`).
- A template run sends its first message only when the agent is ready. `hc run` returns `first_message.sent`. When it is false, round 1 is not sent. `start` returns `NOT_READY` (exit 4) with `debate-start-blocked.md`, as tuios does now (`start`). Keep this path when you remove tuios: the user answers the question in the pane, then `ask … 1` sends round 1.
- The `review-plan` text that moves into `review` says "Do not do a second review", and its description says "in one debate". Remove both. Reviewer 2 reviews the changed plan.
- `review-prompt.md` holds a copy of the diff or the plan from the time of `start` (`build_diff_prompt`, `build_plan_prompt`). The fix check question must tell the reviewer to read the current files, not this copy.
- ➕ A large diff made `review-prompt.md` larger than the Read limit of claude (256KB). Now the diff prompt holds no diff: it gives the `git diff HEAD -- <files>` command and the list of new files. The claude template allows `Bash(git diff:*)`.
- `find_pane_labels` copies `herdr.space` and `herdr.tab` from the author. Keep the labels on the template run, else the pane is not shown (`start_herdr`).
- `hc wait --children any` returns news of any child. The first reviewer stays open, and a finished child stays in the results until `hc rm` (`debate-wait-herdr.md`). Check this with two reviewers. Then make the author wait only for the current reviewer.
- A codex author has no AskUserQuestion and no `run_in_background`. Codex asks a question as plain text. The approval and the blocked question must then stop the turn until the user answers. `hc wait` must use a timeout that the codex shell tool accepts (`debate-author.md`, `debate-wait-herdr.md`).
- `allow-debate-commands.py` allows only exact command shapes. A new command shape of the author steps gets a permission prompt in each round.
- `~/.codex/rules/default.rules` can keep the old tuios line. `setup-review` does not remove lines of the user.
- `~/.config/herdr-core/` does not exist on this machine yet. The setup must create `templates/`.
- `block-file-writes.test.py` has tuios cases that test quoting, not tuios. Keep them, or change them to `hc send` with the same quotes.

## Definition of Done

- [x] No tuios code, asset or test is left — proof: `grep -rn tuios skills hooks README.md` finds only the quoting cases in `block-file-writes.test.py`, if they stay.
  ➕ Also two negative cases stay: `env` gives `none` with tuios variables, and the hook does not allow a tuios wait.
- [x] `debate.py templates` prints both templates — proof: a test reads the output.
- [x] `start` refuses a missing or changed template, and names `/amoniac:setup-review` — proof: a test with a fake `hc`.
- [x] `start` returns 4 and prints Step 0 when `first_message.sent` is false — proof: a test with a fake `hc`.
- [x] `/amoniac:setup-review` installs the templates and the codex rule, and reports "set up" on the second run — proof: two runs in Claude Code in herdr.
- [ ] In a claude session, `/amoniac:review` with no arguments runs codex, then claude, each with approval, fix and fix check — proof: one run on a small diff.
- [ ] In a codex session (`codex --no-daemon`), `/amoniac:review` with no arguments runs claude, then codex, with the same cycle — proof: one run on a small diff.
- [ ] A rejected finding is not fixed — proof: the same run, with one finding rejected.
- [ ] A fix that the reviewer does not accept shows "blocked" and asks the user — proof: one run with a wrong fix.
- [x] `/amoniac:review-plan` runs the same cycle on a plan and changes only the plan — proof: one run (codex READY; claude: one finding approved, fixed, FIXED in round 4).
- [x] `spawn-session` still opens a herdr tab — proof: one run (`spawn-make-test`, `t4c`).

## Work order

1. Remove tuios, and run `make -k test`.
2. Add the templates, `templates` and the template check.
3. Rename `setup-codex` to `setup-review`; the user moves the folder with `! mv`.
4. Change the author steps and `review` for approval, fix, fix check and two reviewers.
5. Move the fix rules of `review-plan` into `review`.

## Wrap-up

- [x] all tests pass: `make -k test`
- [x] README.md shows herdr only, the templates, `setup-review` and the full cycle
- After all boxes: run `/amoniac:complete-plan`. It keeps the title, Goal and Decisions in `docs/plans/completed/`. The user deletes the plan with `! rm`.

## Post-Completion

- The user runs `/amoniac:setup-review` once.
- The user installs the plugin again in Codex.
