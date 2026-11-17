import os
import pathlib
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "complete_plan.py")
FIXTURES = os.path.join(HERE, "fixtures", "complete_plan")

failures = 0
total = 0


def check(label, got, expected):
    global failures, total
    total += 1
    ok = got == expected
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       expected={expected!r} got={got!r}")


def read_file(path):
    return pathlib.Path(path).read_text() if os.path.exists(path) else None


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(text)


def run_script(*args):
    result = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


plan_text = read_file(os.path.join(FIXTURES, "plan.md"))
wbs_text = read_file(os.path.join(FIXTURES, "wbs.md"))

with tempfile.TemporaryDirectory() as base:
    plans = os.path.join(base, "docs", "plans")
    plan = os.path.join(plans, "2026-11-10-retry.md")
    completed = os.path.join(plans, "completed", "2026-11-10-retry.md")

    write_file(plan, plan_text)
    code, out = run_script(plan)
    kept = read_file(completed) or ""
    check("done plan: exit 0", code, 0)
    check("done plan: title, goal and decisions kept", ("# Retry the sync" in kept, "**Goal:** Retry a failed sync one time." in kept, "- **No backoff state**" in kept), (True, True, True))
    check("done plan: other sections dropped", ("Intent" in kept, "Traps" in kept, "Definition of Done" in kept, "Wrap-up" in kept, "Kind of change" in kept), (False, False, False, False, False))
    check("done plan: original stays for the user to delete", read_file(plan), plan_text)
    check("done plan: tells the user to delete it", "! rm -- " + plan in out, True)

    code, out = run_script(plan)
    check("existing completed file is not overwritten", (code, read_file(completed) == kept, "already exists" in out), (2, True, True))

    open_plan = os.path.join(plans, "2026-11-11-open.md")
    open_completed = os.path.join(plans, "completed", "2026-11-11-open.md")
    write_file(open_plan, plan_text.replace("- [x] A failed sync", "- [ ] A failed sync"))
    code, out = run_script(open_plan)
    check("open box: exit 1 and nothing written", (code, os.path.exists(open_completed)), (1, False))
    check("open box: the box is listed", "- [ ] A failed sync runs again" in out, True)

    code, out = run_script(open_plan, "--force")
    check("open box with --force: written", (code, os.path.exists(open_completed)), (0, True))

    added_plan = os.path.join(plans, "2026-11-11-added.md")
    added_completed = os.path.join(plans, "completed", "2026-11-11-added.md")
    write_file(added_plan, plan_text + "\n- ➕ [ ] Retry the webhook too\n")
    code, out = run_script(added_plan)
    check("open added box: exit 1 and nothing written", (code, os.path.exists(added_completed)), (1, False))
    check("open added box: the box is listed", "- ➕ [ ] Retry the webhook too" in out, True)

    wbs = os.path.join(plans, "wbs-billing.md")
    write_file(wbs, wbs_text)
    code, out = run_script(wbs)
    kept = read_file(os.path.join(plans, "completed", "wbs-billing.md")) or ""
    check("wbs: title and grouping decision kept", ("# WBS: Billing epic" in kept, "Group by service" in kept), (True, True))
    check("wbs: scope, iterations and log dropped", ("Scope" in kept, "Iterations" in kept, "Progress log" in kept), (False, False, False))

    open_wbs = os.path.join(plans, "wbs-open.md")
    open_wbs_completed = os.path.join(plans, "completed", "wbs-open.md")
    write_file(open_wbs, wbs_text.replace("**Status:** done\n**Group reason:** no group — independent\n**INVEST notes:** none\n\n## Progress", "**Status:** not started\n**Group reason:** no group — independent\n**INVEST notes:** none\n\n## Progress"))
    code, out = run_script(open_wbs)
    check("wbs with an iteration not done: exit 1 and nothing written", (code, os.path.exists(open_wbs_completed)), (1, False))
    check("wbs with an iteration not done: the iteration is listed", "Iteration 2: payments: not started" in out, True)

    no_decisions = os.path.join(plans, "2026-11-12-empty.md")
    write_file(no_decisions, plan_text.split("\n\n")[0] + "\n")
    code, out = run_script(no_decisions)
    check("no decisions section fails loudly", (code, "no Decisions section" in out), (2, True))

    code, out = run_script(os.path.join(plans, "missing.md"))
    check("missing plan fails loudly", (code, "cannot read" in out), (2, True))

    repository = os.path.join(base, "repository")
    tracked = os.path.join(repository, "docs", "plans", "2026-11-13-tracked.md")
    write_file(tracked, plan_text)
    git = ["git", "-C", repository, "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "plan"], check=True)
    code, out = run_script(tracked)
    check("tracked plan: tells the user to git rm it", (code, "! git rm -- " + tracked in out), (0, True))

    spaced = os.path.join(plans, "my plan; x.md")
    write_file(spaced, plan_text)
    code, out = run_script(spaced)
    check("plan path with a space and ;: quoted in the delete hint", (code, "! rm -- " + shlex.quote(spaced) in out), (0, True))

print(f"\n{total - failures}/{total} passed")
sys.exit(1 if failures else 0)
