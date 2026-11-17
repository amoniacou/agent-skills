---
name: setup-codex
description: Let codex send its notice from its sandbox, so that it can be a reviewer in /amoniac:review (tuios or herdr)
allowed-tools: Bash(python3:*), Read, Edit, Write, AskUserQuestion, Skill
---

# Set up codex for the review debate

A codex reviewer replies with `tuios send-agent-message` in tuios, or with `hc send` in herdr. The sandbox of codex refuses the socket of these tools. A rule in `~/.codex/rules/default.rules` lets only this command run outside the sandbox.

1. Get the two rule lines for this terminal: use the `amoniac:review` skill with the argument `codex-rules`.

   On exit 3, tell the user to run this skill inside tuios or herdr. Stop. On exit 2, show the `debate:` line. Stop.
2. Read `~/.codex/rules/default.rules`. The file can be missing. If the file has the two lines already, tell the user that codex is set up. Stop.
3. Show the two lines to the user. Tell the user that the rule applies to all codex sessions, not only to the reviewer. In herdr, also tell the user that `hc send` can type into each terminal of the user, not only into this session. Ask with AskUserQuestion if you can add the lines.
4. If the user agrees, add only the missing lines at the end of the file. Keep all other lines. If the file is missing, create it with the two lines.
5. Tell the user to start again each running codex session, because codex reads the rules when it starts.
