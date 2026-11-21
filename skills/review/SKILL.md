---
name: review
description: Review the uncommitted diff, or a plan, in herdr with two reviewers in sequence, claude and codex. For each reviewer - a debate, approval of the findings by the user, the fix, and a fix check by the same reviewer
argument-hint: "[diff | plan <file>] [claude | codex] | codex-rules | templates"
allowed-tools: Bash(python3:*), Bash(hc:*), Read, Edit, Write, Glob, Grep, AskUserQuestion, Skill
---

# Review

Each reviewer, `claude` or `codex`, runs in a new pane beside this session, in herdr. This session argues with it about each wrong finding. The user approves the findings. This session fixes the approved findings, and the same reviewer checks the fix.

Paths in this skill are relative to the directory of this SKILL.md. In commands, use the absolute path. `DEBATE` is the absolute path of `scripts/debate.py`.

The arguments are: $ARGUMENTS

## Modes for setup-review

- If the arguments are `codex-rules`, run `python3 "DEBATE" codex-rules`. Show the output and the exit code. Stop.
- If the arguments are `templates`, run `python3 "DEBATE" templates`. Show the output and the exit code. Stop.

## Select the reviewers

Run `python3 "DEBATE" env`. If it prints `none`, tell the user that the review needs herdr. Stop.

`SUBJECT` is the arguments without the agent: `diff`, or `plan PLAN_FILE`. With no subject, `SUBJECT` is `diff`.

- If the arguments name one agent, `claude` or `codex`, only that agent reviews.
- If not, two reviewers review, one after the other. First the agent that this session is not: `codex` in a claude session, `claude` in a codex session. Then the agent of this session.

## The cycle for each reviewer

Run:

```bash
python3 "DEBATE" start SUBJECT AGENT
```

The script checks the conditions, saves the prompt, starts the reviewer and sends round 1. Then it prints the steps of the cycle.

| exit | do |
|---|---|
| 0 | do the printed steps |
| 4 | do the printed steps, from Step 0 |
| 1 | tell the user that there are no changes to review; go to the next reviewer |
| 2 | show the lines that start with `debate:`; stop |
| 3 | tell the user that the review needs herdr; stop |

When the printed steps end, start the cycle for the next reviewer. The second reviewer gets the diff or the plan with the fixes of the first reviewer. If the user stops the review in a step, stop.

## Fix the approved findings

The printed steps refer to this section. Fix only the findings that the user approved.

**Diff.** Load the skills of the project first. Change the code for each approved finding. Then run the tests of the project, for example `make test`.

**Plan.** Change the plan at its own level: **Intent**, **Decisions**, **Traps**, the Definition of Done, the **Deployed** line or the **Skills** line. Do not add code or file-by-file steps. Write the changed text in Simplified Technical English (ASD-STE100), as the `amoniac:plan` skill tells.

A finding can be real but outside the scope. For example, an old defect that the change does not cause and does not need to fix. Do not fix it. Recommend to add it with `/amoniac:backlog`.

Do not start the implementation of a plan from this skill.
