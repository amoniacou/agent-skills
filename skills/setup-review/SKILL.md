---
name: setup-review
description: Prepare /amoniac:review in herdr - install the two reviewer templates of herdr-core, and let codex send its notice from its sandbox
allowed-tools: Bash(python3:*), Read, Edit, Write, AskUserQuestion, Skill
---

# Set up the review debate

`/amoniac:review` starts each reviewer from a herdr-core template: `amoniac-review-claude` or `amoniac-review-codex` in `~/.config/herdr-core/templates/`. A codex reviewer replies with `hc send`, and the sandbox of codex refuses the socket of `hc`. A rule in `~/.codex/rules/default.rules` lets only this command run outside the sandbox.

Do the two parts. Ask before each write. Never remove or change other lines or files of the user.

## Part 1: the templates

1. Get the templates: use the `amoniac:review` skill with the argument `templates`. On exit 2, show the `debate:` line. Stop.
2. The output has one block for each template. The block starts with the line `=== PATH (STATE)`. The text of the template follows, up to the next `===` line or the end.
3. For each block with the state `same`, do nothing.
4. For each block with the state `missing` or `different`, show the path and the state. For `different`, show the difference to the file that is there now. Ask with AskUserQuestion if you can write the template. If the user agrees, write the text of the block to PATH. Create the folder if it is missing.

## Part 2: the codex rule

1. Get the two rule lines: use the `amoniac:review` skill with the argument `codex-rules`.

   On exit 3, tell the user to run this skill inside herdr. Stop. On exit 2, show the `debate:` line. Stop.
2. Read `~/.codex/rules/default.rules`. The file can be missing. If the file has the two lines already, go to the end.
3. Show the two lines to the user. Tell the user that the rule applies to all codex sessions, not only to the reviewer, and that `hc send` can type into each terminal of the user. Ask with AskUserQuestion if you can add the lines.
4. If the user agrees, add only the missing lines at the end of the file. Keep all other lines. If the file is missing, create it with the two lines.

## End

- If nothing was written, tell the user that the review is set up.
- If the codex rule changed, tell the user to start again each running codex session, because codex reads the rules when it starts.
- Tell the user to start codex in herdr with `codex --no-daemon`.
