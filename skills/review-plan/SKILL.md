---
name: review-plan
description: Review an implementation plan in one debate. Checks that the Definition of Done proves the intent, that the decisions agree with the code, that no trap is missing, that the scope is correct, and that new names are correct. Use on "review plan", "check the plan", "critique this plan", or after amoniac:plan.
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion, Edit, Skill
---

# Plan Review

One reviewer examines the plan in a debate, through the `amoniac:review` skill. This session applies the correct findings. Do not do a second review. The plan is short. The tests, the compiler and the linter find code problems during the implementation.

## Step 0: Find the plan file

1. If `$ARGUMENTS` contains a file path, use it.
2. If not, use the most recently changed `.md` file in `docs/plans/`. Do not use files in `completed/` or `wbs-*.md` files.
3. If there are two or more possible plans, show the list and ask the user.

## Step 1: Start the debate

Use the `amoniac:review` skill with the arguments `plan PLAN_FILE`. If `$ARGUMENTS` names `claude` or `codex`, add that agent. The `amoniac:review` skill selects the reviewer and starts the debate.

Do the debate. In its last step, ask the user about the disputed findings. Then go to Step 2 of this skill. The findings that you and the reviewer agree on, and the answers of the user, are the findings for Step 2.

If `amoniac:review` stops before the debate, stop.

## Step 2: Apply the findings and stop

**No findings:** tell the user that the plan is ready. Then stop.

**All other results:** examine each finding.

1. If a finding is about the code, check the source. First load the same skills as the reviewer, so that you use the same rules. If the code does not agree with the finding, reject the finding.
2. A finding can recommend a simpler approach than the plan uses, or a different name. Do not select between the two yourself. Show the two options, recommend one, and ask the user with AskUserQuestion. Apply the answer.
3. Apply the other correct findings without a question. The user reads the plan before the implementation. Thus, it is easy to undo a wrong change. Change the plan at its own level: **Intent**, **Decisions**, **Traps**, the Definition of Done, the **Deployed** line or the **Skills** line. Do not add code or file-by-file steps.
4. Write the changed text in Simplified Technical English (ASD-STE100), as the `amoniac:plan` skill tells.
5. Give a short list to the user:
   - each applied finding and what changed;
   - each rejected finding and a reason of one line.

   With the list of rejected findings, the user can cancel a rejection in one message.

Then stop. Do not do a second review.

A finding can be real but outside the scope of the plan. For example, an old defect that the plan does not cause and does not need to fix. Do not change the plan for it. Recommend to add it with `/amoniac:backlog`.

Do not start the implementation from this skill. The user starts `/amoniac:spawn-session` or `/revdiff:revdiff`, or writes "go".
