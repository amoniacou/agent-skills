# Shared parsing module for the Bash hooks

**Goal:** Move the shell command parsing that five Bash hooks copy into one module, `hooks/bash_hook.py`, and use it in all five.

## Decisions

- **One module, five separate hooks.** Each hook keeps its own file, its own reason and its own tests. The user rejected one large hook file.
- **The module name is `bash_hook.py`.** It holds what each Bash hook shares: the parsing of `tool_input.command` and the deny answer. The user selected the name over `shell_command.py`. It uses `snake_case`, because Python imports it.
- **Public functions of `bash_hook.py`:**

  | function | result |
  |---|---|
  | `split_commands(command) -> list[list[str]]` | the commands, each as a list of its pipe stages |
  | `split_words(stage) -> list[str]` | the words of one stage, with `shlex`; plain split when `shlex` fails |
  | `strip_prefix_words(words) -> list[str]` | the words without `sudo`, `env`, `time`, `nice`, `ionice`, `command`, `xargs`, `then`, `else`, `do`, `!` and `NAME=value` |
  | `mask_quoted_text(command) -> str` | the command with quoted text replaced, as `block-file-writes.py` does now |
  | `deny(reason)` | prints the deny JSON and exits 0 |

- **`split_commands` rules:**
  - A new command starts at `;`, `&&`, `||` and a newline. A new stage starts at `|`.
  - `$(`, a backtick, `(` and `)` also start a new command, as `SEGMENT_SPLIT` does now. This is true also inside double quotes, because the shell runs a command substitution there.
  - No split happens inside single quotes, and no split happens at `|` inside double quotes.
  - The code after `sh -c`, `bash -lc`, `/bin/zsh -lc` and the other shells is split again and added as its own commands.
- **The shared parser changes some behavior on purpose.** Each change below gets a test:

  | command | now | after |
  |---|---|---|
  | `zsh -lc "git branch -a"` | passes `block-git-branches` | blocked |
  | `/bin/zsh -lc "gh api x \| jq ."` | passes `block-output-filters` | blocked |
  | `time gh api x \| jq .` | passes `block-output-filters`, because `find_words` does not remove `time` | blocked |
  | `echo "x; git branch -a"` | blocked by `block-git-branches`, because `SEGMENT_SPLIT` splits quoted text | passes |

  All other commands keep their current result.
- **`go-lookups.py` uses the module only for the Bash check of `go doc | grep`.** The user selected this. The module cache check, the Read and Grep checks and the grep reminder stay as they are.
- **`strip_global_opts` stays in the two git hooks.** It parses git options, not shell. There are two copies. `amoniac:principles` says to wait for the third copy of existing code.
- **No separate test file for `bash_hook.py`.** The hooks are the entry points. Each hook test drives its hook through stdin, as now. `amoniac:principles` rule 7 tells this.
