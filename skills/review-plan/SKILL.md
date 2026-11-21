---
name: review-plan
description: Review an implementation plan with the full cycle of amoniac:review - two reviewers, the debate, approval by the user, the fix of the plan and a fix check. Checks that the Definition of Done proves the intent, that the decisions agree with the code, that no trap is missing, that the scope is correct, and that new names are correct. Use on "review plan", "check the plan", "critique this plan", or after amoniac:plan.
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion, Edit, Skill
---

# Plan Review

Find the plan. Then the `amoniac:review` skill does the review and fixes the plan. The tests, the compiler and the linter find code problems during the implementation.

## Step 0: Find the plan file

1. If `$ARGUMENTS` contains a file path, use it.
2. If not, use the most recently changed `.md` file in `docs/plans/`. Do not use files in `completed/` or `wbs-*.md` files.
3. If there are two or more possible plans, show the list and ask the user.

## Step 1: Review the plan

Use the `amoniac:review` skill with the arguments `plan PLAN_FILE`. If `$ARGUMENTS` names `claude` or `codex`, add that agent. Then only that agent reviews.

When `amoniac:review` ends, give the user a short list: each change of the plan, and each finding that the user did not approve.

Do not start the implementation from this skill. The user starts `/amoniac:spawn-session` or `/revdiff:revdiff`, or writes "go".
