---
name: oversight
description: Set the scope, the Definition of Done and the iterations of an epic that needs many plans, before somebody plans an iteration. Use on "let's scope this epic", "start an oversight session", "oversight session for X", "break this epic into iterations", "how should we chunk this epic", or when the user decides how to group tickets into parts of work before a plan for any of them.
argument-hint: "[epic or scope description]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion
---

# Oversight: scope, Definition of Done and iterations

This session stays open for all of the epic. It does these tasks:

- sets the scope;
- sets the Definition of Done of the epic;
- divides the scope into iterations;
- keeps the status of each iteration in `docs/plans/wbs-<slug>.md`.

When this session starts again in the middle of the epic, it reads that document. It does not find the scope and the iterations again.

This skill is not `amoniac:plan`, which plans one iteration in detail after the scope is set. It is not `amoniac:brainstorm`, which designs one idea. It is above the two: it decides *what* the iterations are before somebody plans one of them.

Write the WBS document and all prompts in Simplified Technical English (ASD-STE100): short sentences, the active voice, one word for one meaning.

## Step 0: New scope or continue?

Find the WBS documents: `ls -t docs/plans/wbs-*.md 2>/dev/null`.

- **No WBS document:** this is a new scope. Go to Step 1.
- **One WBS document:** read it completely.
  - If `$ARGUMENTS` names a *different* epic than this document, this is a new scope. Go to Step 1. Do not put the request into a document for a different epic.
  - If not, continue the epic. Go to Step 5 with the current state of the document.
- **Two or more WBS documents:**
  - If `$ARGUMENTS` selects one of them by its slug or title, read that document and go to Step 5.
  - If not, show each document: the title and a status of one line. Ask which document, or "start a new epic".

## Step 1: Get the scope

Ask one question at a time:

1. The reference of the epic, if there is one: a Jira key, the name of the epic, or a description.
2. A list of the tickets or tasks in the epic.

Free text is correct. A ticket system is not necessary. A simple list of "things to do" is sufficient.

This skill does not connect to Jira or Confluence. If the user has a Jira epic, the user pastes the list of tickets.

## Step 2: Group the tickets into iterations

First, tell the user the rule for groups:

> Put tickets into one iteration when separate plans for each ticket make work that you discard soon. For example, stubs, fake code or temporary code that the next ticket replaces. In all other conditions, each ticket is its own iteration. Some scopes need no groups. Each ticket is large enough, or the tickets are already independent.

Then give a grouping. For each group, tell which tickets are in it and why. Give the real reason: a dependency, or a stub that the group prevents. "These tickets look related" is not a reason. If no ticket needs a group, recommend no groups.

Do not pick a grouping that is more complex than necessary. If the tickets also work as separate iterations, recommend separate iterations.

Go to Step 3. Check the grouping against INVEST before you ask the user to accept it.

## Step 3: INVEST check of the iterations

Check each iteration, not each ticket, against INVEST. The iteration goes to `amoniac:plan` and is delivered. Thus, the iteration must obey INVEST. A ticket alone can fail INVEST, because it is part of a group.

- **Independent** — can you deliver this iteration without a different iteration of this scope?
- **Negotiable** — is it a general agreement, not a full specification?
- **Valuable** — does it give a result that a user or stakeholder wants, alone?
- **Estimable** — can you estimate its size with confidence?
- **Small** — does one `amoniac:plan` run cover it? It must not be a small epic.
- **Testable** — is there a clear condition that shows the iteration is done?

Tell the user each failure and discuss it. Usually, you change the grouping (go back to Step 2). Do not accept an iteration with a failure.

When each iteration passes, ask for the Definition of Done of the epic: one clear sentence that tells when all of the scope is done.

Then ask the user to accept the grouping with AskUserQuestion, before you write anything. This is a real decision:

```json
{
  "questions": [{
    "question": "Proposed iteration grouping — does this look right?",
    "header": "Grouping",
    "options": [
      {"label": "Yes, use this grouping", "description": "Write the WBS document with these iterations"},
      {"label": "No, let me adjust", "description": "Discuss changes before anything is written"}
    ],
    "multiSelect": false
  }]
}
```

## Step 4: Write the WBS document

Create `docs/plans/wbs-<epic-slug>.md`. Make the slug from the name or the reference of the epic, in kebab-case.

```markdown
# WBS: [Epic title]

**Scope source:** [ticket or epic reference, or "ad hoc — no ticket system"]
**Definition of Done (epic):** [one sentence]

---

## Scope

| Ticket | Title |
|--------|-------|
| [ID or n/a] | [title] |

## Grouping decision

[The reason for the grouping from Step 2, complete: which tickets are in a group and why, or why there are no groups.]

## Iterations

### Iteration 1: [name]
**Tickets:** [IDs or titles of the tickets in this iteration]
**Status:** not started
**Group reason:** [why these tickets are together, or "no group — independent"]
**INVEST notes:** [the problems from Step 3, or "none"]

### Iteration 2: [name]
**Tickets:** [...]
**Status:** not started
**Group reason:** [...]
**INVEST notes:** [...]

## Progress log
- [today's date]: WBS created. [N] iterations.
```

There are only two statuses: `not started` and `done`. Each iteration starts as `not started`.

## Step 5: Iteration menu

All paths come to this step: a new WBS document from Step 4, or a document from Step 0. If each iteration in the document is `done`, do not show the menu. Go to Step 6.

Show the list of iterations and their status. Then ask:

```json
{
  "questions": [{
    "question": "What would you like to do?",
    "header": "Next step",
    "options": [
      {"label": "Start an iteration", "description": "Start a new session that plans one iteration, with amoniac:spawn-session"},
      {"label": "Mark an iteration done", "description": "Change the status when an iteration is complete"},
      {"label": "Add or change tickets", "description": "Add tickets to this epic, or change the grouping"},
      {"label": "Stop for now", "description": "Stop here. You can continue this session later."}
    ],
    "multiSelect": false
  }]
}
```

- **Start an iteration.** Ask which iteration. With only two statuses, there is no "next" iteration. The user usually knows which one. Make a complete task prompt from the WBS document: the tickets of the iteration, its group reason, and an instruction to run `/amoniac:plan`. The new session does not read the WBS document. The prompt has all that it needs. Thus, the new session does not think about the other iterations.

  ```
  Plan [iteration name]: [tickets, separated by commas].

  [the group reason of this iteration, copied without changes from the WBS document, so that the new session knows why these tickets are together]

  Run /amoniac:plan for this scope.
  ```

  Start the `amoniac:spawn-session` skill with the Skill tool, and give the prompt as its argument. That skill asks about the CLI and the model, gives a name to the session and starts it in herdr, tmux or kitty. Do not ask these questions in this skill.

  - If `spawn-session` starts the session, add a line to the progress log: the date and the name of the iteration.
  - If `spawn-session` tells that herdr, tmux and kitty are not available, show the full prompt in a code block. Tell the user in one line to paste it into a new session. Add a line to the progress log: the date, the name of the iteration and "prompt given for manual start".

  Then go back to Step 5. The status stays `not started` until the user tells that the iteration is done. This session never plans the iteration itself. That puts the detail of one iteration into the session of the epic.

- **Mark an iteration done.** Ask which iteration. Change its status to `done` in the WBS document. Add a line to the progress log: the date and what changed. Go back to Step 5.

- **Add or change tickets.** Do Step 1 for the new tickets. Then do Step 2 and Step 3 again. A new ticket can go into an existing iteration or into a new iteration. Do not move tickets between `done` iterations without telling the user. Update the WBS document: the scope table, the grouping decision and the iterations. Add a line to the progress log. Go back to Step 5.

- **Stop for now.** Stop. The WBS document is saved. The next run of this skill for the same epic continues from Step 0.

## Step 6: End of the epic

You come to this step when each iteration is `done`. First, ask if other work is necessary before the end of the epic. For example, a README update, a changelog, or other work that the iterations did not cover:

```json
{
  "questions": [{
    "question": "All iterations are done. Is other work necessary before the epic ends?",
    "header": "Final work",
    "options": [
      {"label": "No, end the epic now", "description": "Nothing else to do"},
      {"label": "Yes, there is more work", "description": "Tell what is necessary before the end"}
    ],
    "multiSelect": false
  }]
}
```

- If there is more work, let the user tell what it is. Do the work. If the work is large, start a session for it, as Step 5 starts an iteration. Then ask the question again. One round is not always sufficient.
- When the work is done, or if there was no work, end the epic. Add a last line to the progress log: the date, "Epic complete — all iterations done", and one line about the final work. Then run `/amoniac:complete-plan docs/plans/wbs-<slug>.md`. It keeps the title and the grouping decision in `docs/plans/completed/`. The user deletes the WBS document. Stop. The oversight session of this epic is complete.

## Main rules

- **One question at a time.**
- **This session stays open.** `amoniac:plan` and `amoniac:review-plan` report and stop. The job of this skill is the Step 5 menu. The user comes back to it during all of the epic.
- **Save, do not find again.** Each decision (scope, Definition of Done, grouping, status) is in the WBS document, not only in this conversation.
- **Use `amoniac:spawn-session` to start sessions.** That skill asks about the CLI and the model and starts the session. This skill only makes the task prompt.
- **Group only to prevent discarded work.** The only reason for a group is "separate plans make stubs that the next ticket discards". A general relation is not a reason.
- **Keep the context small.** This session often starts again after a long break. Keep the prompts short. Do not load or write anything "for the future".
