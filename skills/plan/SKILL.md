---
name: plan
description: Write an implementation plan to docs/plans/. Use on "make a plan", "create a plan", "plan this feature", "write a plan", or when the user wants the steps written down before coding.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion, EnterPlanMode
---

# Plan

Write a plan to `docs/plans/yyyy-mm-dd-<task-name>.md`. The plan tells:

- **what** the change is and **why**;
- which **decisions** you made;
- which **traps** an implementer can fall into;
- how to **prove** that the change is done.

The plan does not tell which code to write. The implementer reads the code and selects the files, code and test names. The compiler, the tests and the linter check that work.

The plan has two readers:

- **The user.** The user reads all of the plan and thinks about it, for up to ten minutes.
- **The implementer.** Usually a new session. It knows how to code and can read the code. It did not see this conversation.

A small bug fix can need 20 lines. If a plan becomes longer than approximately 150 lines, the change is too large for one plan. Tell the user and recommend two or more plans. If the change is a large epic, recommend `/amoniac:oversight`.

## Step 0: Find the intent and the context

1. **Find the kind of change** from the words of the user: bug fix, refactor, feature or migration. The kind sets the tests in the Definition of Done (see Step 2).

2. **Load the skills of the project before you read code.** The rules in the skills tell what is a trap, a wrong decision or a missing test. Thus, load them before the analysis. Use the Skill tool. Load each skill that this session did not load yet:
   - If `.agents/required-skills.json` exists, load all skills in `always`. Also load the skills in `files` whose glob matches the area of the change.
   - If the file does not exist, load the skills for the area:
     - Go code: `amoniac:go-best-practices`.
     - Tests: `amoniac:testing`.
     - Helm charts or values: `amoniac:helmcheck`.
     - Other languages or frameworks: the skill for them from the list of available skills.
   - Always load `amoniac:principles`. You use it to examine the decisions and the scope.
   - Always load `amoniac:naming`. You use it for each new name in the plan.

   The change can go into a new area while you read. For example, a Go package in a YAML change, or a chart in a Go change. Then load the skills for that area before you continue.

3. **Read the context.** Use Read, Glob and Grep directly. Do not use an Agent.
   - Feature: find the files of the area with Glob. Read the 1–3 most important files. Use `ls` on the main directories.
   - Bug fix: find the error or the function with Grep. Read the files that contain them. Run `git log --oneline -5`.
   - Refactor or migration: read the main files of the area. Find with Grep the code that imports them.
   - Kubernetes or Helm: also find the dashboards, Alloy configs, RBAC and ConfigMaps that the change can affect.
   - Not clear: run `git status` and `git log --oneline -5`. Read README.md and CLAUDE.md.

   Read approximately 5 files. Read more in these conditions:
   - `docs/plans/` or `docs/plans/completed/` has a plan for the same feature.
   - A `docs/plans/wbs-*.md` file shows this work as an iteration.
   - The user says that this change is one part of a larger task.

   Then read until you know the call chains that the change uses.

4. **Find what can already be in use.** Make a list of what the change modifies in these items:
   - a database schema or stored data;
   - a config format or a file format;
   - an API or a message contract;
   - a public interface that other code imports;
   - a CRD or Helm values.

   Step 1 asks about these items.

5. **Find the test command.** Use the `test` target in the `Makefile`. If there is no target, use the test step of the CI workflow. If there is no step, use the default of the language, for example `go test ./...`. The Wrap-up section of the plan uses this command.

6. **Show the result** in 3–5 bullets. Also give the names of the skills that you loaded in item 2.

## Step 1: Ask the questions

Show the result of Step 0. Then ask the questions **one at a time**. Use one AskUserQuestion call for each question. Do not ask a question that the conversation already answered.

1. **Goal.** Give choices. Recommend the goal that you found in Step 0.
2. **Scope.** Ask which components the change includes. If you found only one component, use free text.
3. **Constraints.** Ask about requirements, limits, and what must not change.
4. **Migration.** Ask only if Step 0, item 4 found an item. Give the names of the items that the change modifies. Then ask if these items are in production, or if other systems use them. Other systems are, for example, a different service, a client, a shared environment, or stored data that somebody keeps. Give these choices:
   - **Not deployed.** Nobody uses the items. Change them in place. Do not write a migration. Do not keep backward compatibility. Do not add a deprecation period or a staged rollout. You can delete local data and dev data.
   - **In production or used by other systems.** The plan must include a migration. The old and the new version must work together during the rollout.
   - **Partly.** Free text: which items are in use, and where.

   Do not think that a migration is necessary because the code looks complete. Do not think that it is not necessary because the code looks new. Only the user knows the answer. Write the answer in the **Deployed** line of the plan.

Make the title of the plan from the goal. Use it for the H1 and for `<task-name>` in the file name. Do not ask the user for the title.

## Step 1.5: Compare the approaches

Do not do this step in these conditions:
- There is only one clear approach.
- The user already selected an approach.
- The change is a clear bug fix.

Always do this step when a simple approach and a more complex approach both work. Do not select the complex approach yourself. For example:
- The simple approach does the work in two passes: a requeue, a second reconcile, a second run.
- The complex approach adds state to do the work in one pass: a status field, a flag, a phase, a cache, ordering logic.

Show the two approaches. Recommend the simple approach. Then ask the user. Only the user can accept the extra complexity.

In other conditions, give 2–3 approaches. Put the recommended approach first. For each approach, tell how it works, its advantages and its disadvantages. Ask the user to select one with AskUserQuestion. Write the selected approach and the rejected approaches in **Decisions**.

## Step 2: Examine the code, then write the plan

### Examine the code that the change uses

Read the code that the change calls or builds on. Read the function bodies, not only the names. Find what a new implementer can do incorrectly:

- A function does something different from its name. For example, `GrantAccess` gives USAGE but not CREATE.
- The code wraps an error again, or changes it to an unexpected status.
- An earlier phase or migration already leaves some state.
- A test checks behavior that the change modifies.
- An API or a test setup requires an order of calls.
- The easy approach breaks a rule of a loaded skill.

Write each of these facts in **Traps**. Give its location: `path/to/file.go` and the function name. If a fact changed the approach, write it in **Decisions**. Do not write code for these facts.

### Migration

Use the answer to Step 1, question 4:

- **Not deployed.** The change modifies schemas, formats and interfaces in place. Do not plan migration files, compatibility code, double reads or writes, or feature flags for the rollout. Write one line in **Decisions** that says this. Then the implementer does not add them "for safety".
- **In production or used by other systems.** The kind of change is migration, or the change includes a migration. The Definition of Done must prove three things:
  - The migration runs on the existing data.
  - The old and the new version work together during the rollout.
  - The rollback steps are known.
- **Partly.** In **Decisions**, tell which components need a migration and which do not.

### Backlog items

Do this only if `docs/backlog/` exists. Compare the `where` paths of the items with the area of the change. For each match with `worth: yes`, ask with AskUserQuestion if the plan must include it. An included item gets its own Definition of Done line. That line includes the deletion of `docs/backlog/<slug>.md` in the same change. See the lifecycle in `/amoniac:backlog`. Items with `later` or `no` are only context. Do not ask about them.

### Tests for each kind of change

The Definition of Done contains the test approach. Do not ask a separate question about tests.

- **Bug fix.** The first item: a test shows the bug. The test fails before the fix and passes after the fix.
- **Refactor.** The first item: tests lock the current behavior before the change. Use unit, integration or other tests, as necessary. The same tests pass without changes after the refactor.
- **Feature or migration.** The Definition of Done tells what to prove. The implementer selects the order and the type of tests.

### Plan template

```markdown
# [Title]

**Goal:** [one sentence]

**Kind of change:** [bug fix / refactor / feature / migration]

**Deployed:** [not deployed — change in place, no migration / in production — migration necessary / partly: … / n/a — nothing is stored or shared]

**Skills:** [the skills the implementer loads before writing code, for example `amoniac:go-best-practices`, `amoniac:testing`]

## Intent

[What changes and why, in a short paragraph. What is wrong or missing now. What the change does.]

## Decisions

- **[decision]** — [why; which alternatives you rejected, and why]

## Constraints / out of scope

- [what must not break; what this plan does not do]

## Traps

*Remove this section if there are no traps.*

- [a fact about the code that is not easy to see] (`path/to/file`, `FuncName`)

## Definition of Done

- [ ] [result that you can check] — proof: [the test that shows it / a command and its expected output / what to look at]

## Work order

*Remove this section if the order is not important. One line for each step.*

1. [step]

## Wrap-up

- [ ] all tests pass: `<command from Step 0>`
- [ ] the linter passes: `<project linter>`
- [ ] README.md and CLAUDE.md show the new behavior or patterns, if they changed
- After all boxes: run `/amoniac:complete-plan`. It keeps the title, Goal and Decisions in `docs/plans/completed/`. The user deletes the plan with `! rm`.

## Post-Completion

*Remove this section if it is empty. Manual steps or external systems.*
```

### Writing rules

- **Use Simplified Technical English (ASD-STE100).** Write the plan in English:
  - Write short sentences. An instruction has a maximum of 20 words: Definition of Done, Work order, Wrap-up. A description has a maximum of 25 words: Intent, Decisions, Traps.
  - Write one instruction in each sentence.
  - Use the active voice. Use the imperative for instructions. Write "Return 401 for an expired token". Do not write "An expired token should be rejected with a 401".
  - Use one word for one meaning. Use the simple, usual word: `use`, not `utilize`; `start`, not `commence`; `show`, not `render` when nothing renders.
  - When you select a term, keep it. Use the same word for the same thing in all sections. Use the same name as the code.
  - Do not use idioms, slang or metaphors. Do not use filler words, for example "in order to", "basically", "it should be noted that".
  - Do not write "it" or "this" when the sentence before names two or more things. Write the name, for example "the handler".
  - Use only the abbreviations that are standard in the field: `ID`, `URL`, `API`, `DB`, `CRD`.
  - Write code names, paths and commands as they are, in backticks.
- **Do not write code.** Do not write code for each task, test bodies or line numbers. There is one exception: a short example for one difficult item, when text is not clear. For example, a query, a migration step or a regex. A new interface, public signature or endpoint shape that other code uses is a decision. Write it in **Decisions**. A signature line is permitted. A body is not.
- **Write results, not steps, in the Definition of Done.** "Expired tokens get 401" is a result. "Add a check in middleware.go" is a step. Each item tells its proof.
- **Check each new name.** A decision can add a name that other code or users see: a type, an error, a status field, a CRD field, a Helm value, an endpoint, a file, a package. Write the name in **Decisions**. Before you write it:
  - Find the names of the same kind next to it in the code, and use the same pattern.
  - Check the name against the `amoniac:naming` rules.
  - If two names are possible, give both and ask the user.
- **Give file and function names only when they are important:** in **Traps**, or in a decision about a specific location. Do not use them as a to-do list.
- **Do not tell the history of the plan.** Do not refer to line numbers in old plans. If the plan reverses an earlier decision, write one line about it in **Decisions**.
- **Draw the flow.** If the change modifies a flow, a sequence, a state machine or a structure, draw a small text diagram. Use boxes and arrows. Do not use mermaid, because the user reads plans in the terminal. For a change to an existing flow, show "before" and "after". Use a table for data in rows and columns: options and their advantages, inputs and results, a mapping. The text tells why. The text does not tell again what the diagram shows.
- **Progress.** The implementer marks the Definition of Done and Wrap-up boxes when each item is complete. The implementer adds new work as new items with the prefix ➕. The implementer marks blockers with ⚠️.
- **No commits.** The plan does not tell the implementer to commit, to push, or to move files with the shell. The user does these steps.

## Step 2.5: Check the plan yourself

Do the check and do not show it. Tell the user only what you corrected.

1. Each point in **Intent** has a minimum of one Definition of Done item that proves it.
2. Each Definition of Done item tells its proof.
3. You checked each trap in the source code. You did not guess it from a name.
4. A bug fix plan or a refactor plan starts the Definition of Done with the test-first item.
5. No decision breaks a rule of a loaded skill without a reason in **Decisions**.
6. Each new name in **Decisions** obeys `amoniac:naming` and uses the same pattern as the names next to it in the code.
7. The migration work agrees with the **Deployed** line: no migration if not deployed; a migration and rollback steps if in production.
8. Each sentence obeys the STE rules. Read each sentence again. Divide or write again a sentence that is too long, uses the passive voice, or uses an unclear or a different term.
9. The plan has no code, except the permitted example and signatures. The plan has no text that is there only to look complete. If the plan is longer than approximately 150 lines, recommend two or more plans. Do not only make it shorter.

The reviewer of `/amoniac:review-plan` checks the same items. Thus, a good self-check usually gives a short review.

## Step 3: Tell the user that the plan is ready

Write: "created plan: `docs/plans/yyyy-mm-dd-<task-name>.md`". Then stop. Do not start the implementation. Do not ask what to do next. The user starts `/amoniac:review-plan`, `/revdiff:revdiff` or `/amoniac:spawn-session`, or writes "go".

## Main rules

- **Skills before code.** Load the skills of the project first. Then read the code.
- **Ask before you plan a migration.** A migration is for data or users that already exist. Ask the user if they exist.
- **Simple technical English.** Short sentences and one word for one meaning. Then a new session understands the plan as the author did.
- **Intent, not instructions.** Tell what and why. The implementer decides how.
- **One question at a time.** Give choices when possible.
- **Recommend first.** Give your opinion. The user decides.
- **YAGNI.** Keep the scope small. Do not add anything "for the future".
