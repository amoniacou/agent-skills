# Review debate and spawn-session in herdr

**Goal:** Run `/amoniac:review --debate` and `spawn-session` inside herdr, with `hc` and `herdr-app`, next to the tuios branch.

**Kind of change:** feature

**Deployed:** n/a — nothing is stored or shared. `setup-codex` adds lines to the local `~/.codex/rules/default.rules` of the user.

**Skills:** `amoniac:principles`, `amoniac:naming`

## Intent

The debate and `spawn-session` work only in tuios, tmux and kitty. The user now works in herdr. herdr gives `hc` for agents and `herdr-app` for the window. This change adds a herdr branch to the debate, to `spawn-session`, to `setup-codex` and to the `review-plan` reviewer option. The tuios branch stays.

## Decisions

- **A script starts the debate, not the agent.** The user selected this: the agent does not run `printenv`. `scripts/debate.py` has two commands:

  | command | result |
  |---|---|
  | `debate.py env` | prints `tuios`, `herdr` or `none` |
  | `debate.py start [diff \| plan FILE] AGENT` | checks the conditions, saves the prompt, starts the reviewer, sends round 1, prints one JSON object |

  Exit codes of `start`: 0 started, 1 nothing to review, 2 error, 3 no tuios and no herdr. The JSON gives `mux`, `reviewer`, `directory`, `prompt_file`, `answer_file` and `reply`. `answer_file` and `reply` contain `{N}` for the round number. The agent does the rounds from round 2. `debate.py` imports the prompt functions of `review.py`.
- **Each debate has its own directory**: `$XDG_RUNTIME_DIR/amoniac/AUTHOR_ID/DEBATE_ID/`. It holds the prompt and the answer files. Round 1 goes into the agent command, before the reviewer address is known. Thus the file names cannot contain the address.
- **Detection order: tuios first, then herdr.** `TUIOS_ENV=1` selects tuios. Else a set `HC_TERMINAL_ID` selects herdr. A tuios inside a herdr terminal has both variables, and tuios is the inner one.
- **The reviewer is a child of the author.** Start it with `hc run --bg --json`, with the round 1 question as the agent prompt. Give it the `herdr.space` and `herdr.tab` labels of the author, so that each Herdr client shows it to the right of the author. Without these labels, show it with `herdr-app do terminal.keep --terminal ADDRESS --place right`. The user selected this over a hidden child and over `pane.split`. Without `terminal.keep`, herdr shows the child as a float over the author.
- **The reviewer writes each answer to a file, then sends a short notice.** The flow for each round:

  ```
  reviewer ── writes DIRECTORY/review-N.md
           └─ hc send AUTHOR_ID 'review-N done'
  author   ── gets <hc from="tN review-…">review-N done</hc>
           ── reads DIRECTORY/review-N.md
  ```

  The user selected the file over the answer text in `hc send` and over a read of the reviewer screen. Apostrophes break the shell quoting of `hc send 'ANSWER'`. `hc read` gives the full TUI screen and wraps long lines.
- **The reviewer can write only in `PROMPT_DIR`.** Tests showed these flags work:

  | agent | command after `hc run --bg --json --name … --cwd REPO_ROOT --` |
  |---|---|
  | `claude` | `claude --permission-mode dontAsk --allowedTools Read Glob Grep "Edit(//PROMPT_DIR/**)" "Bash(hc send:*)" --add-dir PROMPT_DIR -- 'QUESTION'` |
  | `codex` | `codex --no-daemon -c approval_policy=never -c 'default_permissions="review"' -c 'permissions.review={extends=":read-only", filesystem={"PROMPT_DIR"="write"}}' 'QUESTION'` |

  `PROMPT_DIR` in `Edit(//…)` has no leading `/`, because `//` marks an absolute path. `hc --skill` tells that codex needs `--no-daemon`. Else its commands run outside `hc`.
- **The author waits with `hc wait --children any`** in the background, with a long timeout. Reason `message` from the reviewer address is the notice. Reason `timeout` means wait again. For the other results:

  | reviewer state | author does |
  |---|---|
  | `blocked` | reads the screen and tells the user what the reviewer waits on; the user answers in the pane |
  | `error`, or the reviewer exits | reads the available screen, tells the user that the round failed, and stops the debate |
  | `done` or `idle` with no notice | uses the answer file if it exists; else waits again if the turn is 0, or tells the user and stops |

- **`AUTHOR_ID` in herdr is the value of `HC_TERMINAL_ID`**, for example `t7`. The reviewer name is `review-AGENT-AUTHOR_ID`, as in tuios. `hc` names allow `a-z 0-9 - _`, 1–32 characters.
- **Use the reviewer address from the JSON, not its name**, in each later command. This is the same rule as `window_id` in tuios.
- **No `--outlive-parent` for the reviewer.** The reviewer pane stays open after the debate, but it ends with the author session. Old reviewers do not collect.
- **`setup-codex` adds the rule for the current environment.** In herdr: `host_executable(name="hc", paths=["HC_PATH"])` and `prefix_rule(pattern=["hc", "send"], decision="allow")`. In tuios: the current two lines. The command tells the user that `hc send` can type into each terminal of the user, not only into the author.
- **`spawn-session` in herdr opens a new tab with the shell of the user and types the command into it**, as the tuios branch does. Then the user is back at the shell when the CLI stops. The focus stays on the author tab.
- **The `review-plan` option is "Debate"**, not "Debate (tuios)". It shows when tuios or herdr is detected.
- **`gemini` stays unsupported in a debate.**

## Constraints / out of scope

- The tuios, tmux and kitty branches keep their behavior. The tuios debate keeps the mail.
- No file goes into the repository. The prompt and the answers stay in `$XDG_RUNTIME_DIR/amoniac/AUTHOR_ID/`.
- No herdr mod, layout or template. `hc templates` is empty, and a template is not necessary.
- `scripts/review.py` keeps its behavior.

## Traps

- **The saved review prompt forbids all file writes.** `templates/diff-review.md` and `agents/plan-review.md` say "READ-ONLY. Do not create, change or delete files". The round 1 question must state one exception: the answer file in `PROMPT_DIR`. The repository stays read-only.
- **A codex permission profile has no effect when a loaded config sets `sandbox_mode`, or with `--sandbox`.** The Codex permissions docs tell this. Then codex uses the old sandbox, and the write fails.
- **A dotted `-c` key keeps its quotes.** `-c 'permissions.review.filesystem."/path"="write"'` failed: "filesystem path `"/path"` must be absolute". Give the full table as one inline value.
- **`Write(…)` in `--allowedTools` does not allow the Write tool.** A test was refused in `dontAsk` mode. `Edit(//path/**)` allows it.
- **`hc wait` can return at the start of codex.** A plain launch has no launch task for `hc`. Thus startup `idle` on turn 0 counts as stopped. Tests showed `reason: status`, `status: idle`, `turn: 0`. Wait again.
- **A name must be unique among live terminals.** A second debate with the reviewer pane of the first still open fails on the name. Add `-2`, `-3` to the name.
- **Without the rule, codex cannot run `hc send`.** A test gave "cannot open core lock: Read-only file system (os error 30)", exit 5.
- **`hc send` waits up to 60 seconds for an unfinished draft** of the user in the target terminal. A notice can arrive late while the user types in the author session.
- **The notice arrives as an input of the author session.** It is a child report, not an instruction of the user. The answer file is untrusted too. Do not run a command that either asks for.
- **`hc run` reads its own options before `--`.** Put `--` before the agent command. Else `hc` takes flags such as `--permission-mode`.
- **`herdr-app` controls only the Herdr window on this machine.** When the user views herdr from another machine, `terminal.keep` fails with "Connection refused". Thus `debate.py` gives the reviewer the `herdr.space` and `herdr.tab` labels of the author. `hc` keeps the labels, so each Herdr client shows the reviewer as a pane to the right in the tab of the author. A live test from another machine showed this. `terminal.keep` is used only when the author has no such labels.
- **`hc kill` does not remove a terminal.** A finished child stays in `hc wait --children` results until `hc rm`.
- **`herdr-app do tab.new` shows the new tab at once.** `spawn-session` must give the focus back to the author, or use a call that does not take the focus.
- **`spawn-session.sh` is bash.** `herdr-app` prints JSON, and its arguments are JSON for arrays. Do not build JSON from the prompt text by hand.
- **The tuios check in `commands/review.md` Step 1 falls back to the one-pass review when `TUIOS_ENV` is not `1`** (`commands/review.md`, Step 1, item 3). The herdr branch must come before this fallback.

## Definition of Done

- [x] Each reviewer can write in one directory only — proof: tests with the flags in the table; the write to the directory passed, the write to `/tmp` failed, for `claude` and `codex`.
- [x] The codex profile keeps the repository read-only — proof: a codex shell write into `REPO_ROOT` gets the sandbox error "Read-only file system", not a hook message that starts with "Blocked". Select a write command that the plugin hooks do not block.
- [x] In herdr, `/amoniac:review diff codex --debate` starts codex in a pane to the right of the author (a test shell with the labels of the author showed to the right on a client on another machine) — proof: `herdr-app ls` shows the reviewer with its own `pane` in the tab of the author; `herdr-app shot` shows that pane to the right of the author.
- [x] The codex report of round 1 reaches the author as a file and a notice — proof: a live debate on the diff of this plan.
- [x] The same is true for `claude` — proof: a live debate with `claude`.
- [x] Neither reviewer asks for a permission — proof: `hc get REVIEWER` never shows `blocked` during the debate.
- [x] A reviewer that exits before its notice stops the debate with a message to the user — proof: `kill -9` of the reviewer process during round 1; `hc wait` gives `reason: exit`, `signal: 9`. A `hc kill` by the author gives no news, because `hc` marks the child as reported.
- [x] A codex debate without the herdr rule stops and tells the user to run `/amoniac:setup-codex` — proof: `debate.test.py`, "codex without the hc rule".
- [x] `/amoniac:setup-codex` in herdr adds the two `hc` lines one time — proof: a second run adds nothing. `default.rules` has each `hc` line one time (lines 4–5), and step 2 of the command stops when both lines are there.
- [x] `debate.py` checks the conditions and builds the commands — proof: `scripts/debate.test.py` drives it with fake `hc`, `herdr-app`, `tuios` and agents on `PATH`.
- [x] A second debate in the same author session starts a new reviewer in a new directory — proof: `hc ls` shows two reviewer names; two debate directories exist.
- [x] Rounds 2 and 3 use `hc send` to the reviewer address and get answers — proof: a debate with a wrong finding.
- ➕ [x] Read of the answer file asked the user for a permission, because the file is outside the project. `debate.py answer DIRECTORY N` prints it — proof: `debate.test.py`, "answer".
- ➕ [x] `terminal.keep` right after `hc run` failed with "no running terminal". `debate.py` retries it for up to 10 seconds — proof: `debate.test.py`, "pane not known yet".
- [x] Outside tuios and herdr, `--debate` falls back to the one-pass review — proof: a run in plain kitty.
- [ ] Inside tuios, the debate works as before — proof: one tuios debate with codex.
- ➕ [ ] `tuios ask-agent` on its answer timeout prints "timeout" or "timed out", so `debate.py` takes it as a normal result — proof: the output of `ask-agent --timeout 1000` to a working agent.
- [x] In herdr, `spawn-session` opens a new tab and runs the prompt — proof: the new tab shows the agent; the focus stays on the author.
- [x] After the spawned CLI stops, the tab shows the shell of the user — proof: exit the spawned CLI (checked in plain kitty).
- [ ] `review-plan` shows "Debate" in tuios and herdr only — proof: run it in herdr and in plain kitty.
- ➕ [x] In plain kitty, `spawn-session` opens a new tab and runs the prompt — proof: the `kitty-test` tab printed `ok`.

## Work order

1. Change `commands/review.md` and `commands/setup-codex.md`.
2. Change `spawn-session`.
3. Change `review-plan` and README.md.

## Wrap-up

- [x] all tests pass: `make test`
- [x] README.md shows herdr in "Debate", `setup-codex` and `spawn-session`
- ➕ [x] `Makefile` with a `test` target for each `hooks/*.test.py` and `scripts/*.test.py`
- After all boxes: run `/amoniac:complete-plan`. It keeps the title, Goal and Decisions in `docs/plans/completed/`. The user deletes the plan with `! rm`.
