---
name: backlog
description: Read, work and keep the deferred-work items of a Git repo in docs/backlog/, one file for each item. Use on "backlog", "check backlog", "what's on my backlog", "work the backlog", "add to backlog", "clean up backlog", or when a review or a task found real problems that nobody fixes now. Owns the item format and the lifecycle.
argument-hint: "[slug | --all]"
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, Skill, AskUserQuestion
---

# Backlog

`docs/backlog/` in the root of a repo keeps work that is real but that nobody does now. For example:

- a defect that a change did not cause;
- a drift with no symptom for users;
- a fix whose risk was larger than its value;
- an idea to keep.

Each item is one file. The backlog is the list of the maintainer. It does not block anything. It does not go to a contributor.

The path is always `docs/backlog/`. Thus, each run in a repo reads and writes the same location.

**Git only.** Outside a Git repository, tell the user and stop. Do not use a different VCS.

**You do not change Git.** The hooks of this plugin block `git add`, `git rm`, `git commit` and the commands that read branches. When an item must go out of Git, tell the user the command to run with `!`. For example: `! git rm docs/backlog/<slug>.md`.

## Item format

The file is `docs/backlog/<slug>.md`. The slug is the name of the defect, not the name of the file that contains it. For example, `reopen-fallback-ignores-frontmost.md`. Then a commit can refer to it, and you find duplicates by the file name.

```markdown
---
worth: later
where: internal/window/library.go:537
added: 2026-08-05
---
# reopen fallback ignores the last-frontmost window

The `reopen` fallback does not use the last frontmost window when `frontmost` is nil. Thus, a user with many windows gets the last-window capture only when the closed window was `windows.first`. Found in the review of PR #370. The fix changes the restore order. Thus, it was not done in that PR.
```

The frontmatter has three fields and one optional field. Write them one time. Change them only as **Add items** tells.

- **`worth: yes | no | later`** — the triage decision. The list uses this field for the order.
  - **`yes`** — the value is agreed, and somebody must fix it. It tells nothing about the time. An item that waits for an upstream release is still `yes`.
  - **`later`** — the value is not decided yet. The body must give the unknown fact or the condition that decides it. Without it, the item is a `yes` or a `no`.
  - **`no`** — a decision not to fix. Keep it so that the next review does not find and discuss the same problem again. When the reason is not useful any more, delete the file.
- **`where: path:line`** — remove it when the item has no single location. The path helps to find duplicates. The line is only a help, because it moves.
- **`added: YYYY-MM-DD`** — do not change it. It shows the age of the item. Use two digits for the month and the day, so that the values sort correctly.
- **`ticket: PROJ-123`** — optional. The ticket in the tracker for a large item. You can add it at any time when the user asks. Two items with the same ticket are the same item.

The H1 is the title. The body has no required sections. Use the shape that fits: steps to repeat the problem, what you tried, the review that found it, links, an example. Two items need one sentence each:

- A `later` item tells the unknown fact that decides its value.
- A `no` item tells why nobody fixes it.

Write the items in Simplified Technical English (ASD-STE100): short sentences, the active voice, one word for one meaning.

## Lifecycle

Create the file. When the fix is done, delete the file in the same change as the fix, not in a separate change. There is no checkbox and no "in progress" mark. The deletion is the state. A dropped item goes out the same way, with a different reason.

You delete the file. The user runs `! git rm` or stages the deletion.

## Briefing of an item

The two argument forms below show the same four lines before a question about an item. Show them as usual text, not inside AskUserQuestion. The question covers approximately five lines above it. Thus, the question text also gives the name of the item and a reason of one line for the recommendation.

- **Summary** — what the item is and why somebody wrote it. One or two sentences in your own words. Do not copy the H1 or the body.
- **Effort** — the cost of the fix: the files and the call sites, if a test covers the path, and if the fix is mechanical or needs a design decision.
- **Risk** — what else the change can affect: callers, generated files, other code on the same path, and if it is easy to revert. Check the callers before you write "contained".
- **Impact** — who has the problem now, how bad it is, and the cost to leave it. Most items have no symptom for users. If so, tell it.

Effort, risk and impact are each ONE line with a word and the fact behind it. With only the word, the user must trust you. The fact lets the user disagree. Examine all four against the current repo, not against the text of the item. The text of an item becomes old, like its `where`.

## Argument `--all`

`/amoniac:backlog --all` gives a decision for each item. Check this argument before you look for a slug. An argument that starts with `-` is an option. Thus, a file whose name starts with `-` cannot be a slug.

1. Find `docs/backlog/*.md` from the root of the repo. Read each file completely. Keep the `worth: no` items: `worth` changes the recommendation, not the list.
2. Before you ask, check each `where`. Examine the value, the effort and the blockers of each item. Find the items that block other items. Ask about a blocker before the items that it blocks. Tell the relation in the briefing of each item that it affects. For a blocker outside the backlog, recommend to leave the item, and give the name of the blocker.
3. Do the items ONE AT A TIME. Show the briefing of the item. Ask about that item only, with AskUserQuestion. Put the recommendation first. Do the answer. Then go to the next item. Do not show many briefings and ask after them. Give each item a number, `item N of M`.
   Use these answers:
   - **fix the item now** — give the name of the item in the label;
   - **drop the item** — for a `no` whose reason is not useful any more;
   - **leave it** — nothing changes.
4. Do each answer before you ask about the next item. Before a fix or a drop, read the item again and check its `where` again, because an earlier fix can change it. If that changes the recommendation or the briefing, show the new briefing and ask again.
   For a fix, run the tests, the formatters and the linters. Delete the item file, as the lifecycle tells.
5. Continue until each item has a decision. Do not commit. At the end, give the user the list of changed and deleted files.

## A slug as the argument

`/amoniac:backlog <slug>` names one item: `docs/backlog/<slug>.md`. Read that file only. If it has a `where`, check it. Show the briefing. Then ask the fix-or-drop question. Do not show the list.

If no file has that slug, tell the user. Show the list of items. Do not guess the nearest name.

## Read and work the list

1. Find `docs/backlog/*.md` from the root of the repo. Read the frontmatter and the H1 of each file. If the directory does not exist, tell the user and offer to start one. Do not create an empty directory.
2. **Check before you report.** A `where` becomes old when somebody renames a file or moves a line. For each item with a `where`, check that the location exists and still shows what the item tells. Report an old item as old, not as work. An item without `where` has nothing to check.
3. Report each item in one line. First `yes`, then `later`, then `no`. In each group, the oldest `added` first. Give `where` and `ticket` when the item has them. Do not add your opinion. The item already has its reason.
4. Give actions with AskUserQuestion, not as text. Put the recommendation first. Use the answers from `--all`, step 3. If there are more than four items, use more than one question. Do not cut the list.
5. On "fix the item now": do the work. Run the tests, the formatters and the linters. Delete the item file. Do not commit.

## Add items

When a run finds deferred items, offer to add them. Do not write them without a question.

**Ask before you write in the current checkout.** You cannot read the branch name, because the hooks block it. Thus:

- If the `where` path of the item is in `git diff --name-only HEAD` or in `git status --porcelain`, the current change contains that code. Write the item here without a question.
- In all other conditions, ask the user if this checkout is the correct location for the item. If the answer is no, change nothing. Do not create a branch, a worktree or a temporary checkout.

**Find duplicates before you write.** The `where` path and the slug give the possible duplicates. The defect itself decides. One file can have many different defects, and the line moves with each edit. An old defect comes back in each review that touches its file. If the item already exists, tell the user and do not change it. If the new finding makes the description better or changes the `worth`, edit that file. Do not add a second file.

The Write tool creates `docs/backlog/` if it does not exist. Do this only after the checkout question.

When the files are written, give the user the list of the files that you created or changed. Recommend a separate commit that contains only these files, and give the command. For example: `! git add docs/backlog/<slug>.md && git commit -m "backlog: <title>"`. A backlog item is only notes. If nobody pushes it, nobody sees it from a different machine. Thus, also recommend a push.

## Rules

- **Do not post a backlog item to a PR, MR or issue** unless the user asks. These are the notes of the maintainer. On the change of a contributor, they look like pressure to do more.
- **Do not commit.** The user commits item files, and never together with other work.
- **Do not fix an item without a request.** To read the backlog is not permission to work on it.
- **Delete, do not demote.** If nobody will do an item and nobody needs its reason, tell the user and offer to drop it. This rule does not apply to a `no` that still stops a repeated finding. Keep that `no`.
