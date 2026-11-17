---
name: complete-plan
description: Keep only the title, Goal and Decisions of a finished plan or WBS document in docs/plans/completed/
argument-hint: "[plan file] [--force]"
allowed-tools: Bash(python3:*), AskUserQuestion
---

# Complete a plan

Paths in this skill are relative to the directory of this SKILL.md. In commands, use the absolute path.

1. Find the plan. If `$ARGUMENTS` has a file path, use it. If not, use the most recently changed `.md` file in `docs/plans/`. Do not use files in `completed/`. If there are two or more possible plans, show the list and ask the user.
2. Run `scripts/complete_plan.py` with the absolute path:

   ```bash
   python3 "SCRIPT" PLAN_FILE
   ```

   `SCRIPT` is the absolute path of `scripts/complete_plan.py`. Add `--force` only when `$ARGUMENTS` has `--force`.

3. Use the exit code:
   - **0:** show the two lines of the output. The second line is the command that deletes the plan. Tell the user to run it. Do not delete the plan yourself.
   - **1:** the plan has open boxes. Show them. Ask the user with AskUserQuestion: complete the open boxes first, or complete the plan with `--force`. With `--force`, run the command again.
   - **2:** show the line that starts with `complete_plan:`. Stop.
