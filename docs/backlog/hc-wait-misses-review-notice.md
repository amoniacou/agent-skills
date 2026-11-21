---
worth: later
where: skills/review/assets/debate-wait-herdr.md:6
added: 2026-11-17
---
# hc wait does not return on the review notice

Step 1 of the debate runs `hc wait --children any --json --timeout 1800` in the background. The result table expects "the notice of round N" from the reviewer. In the plan review of 2026-11-17, three such waits ended only with `reason: timeout`, after 30 minutes. The notice `review-N done` and the `done` status of the reviewers `t42` and `t43` did not end them.

In Claude Code, the notice arrives as a separate input of the author session. Thus the debate worked, and each wait only stayed in the background for 30 minutes.

The unknown fact: does a codex author (`codex --no-daemon`) get the notice as an input too? If yes, remove the wait step, or keep it only for the `blocked`, `error` and exit cases. If no, find a wait that returns on the notice, for example `hc wait REVIEWER`.
