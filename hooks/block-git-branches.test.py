import json
import os
import subprocess

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "block-git-branches.py")

DENY, PASS = "deny", "pass"

CASES = [
    ("branch -r", "git -C /home/user/other branch -r", DENY),
    ("branch --show-current", "git branch --show-current", DENY),
    ("branch -a", "git branch -a", DENY),
    ("symbolic-ref origin HEAD", "git -C /home/user/other symbolic-ref refs/remotes/origin/HEAD", DENY),
    ("rev-parse --abbrev-ref", "git rev-parse --abbrev-ref origin/HEAD", DENY),
    ("rev-parse HEAD passes", "git rev-parse HEAD", PASS),
    ("rev-parse --show-toplevel passes", "git rev-parse --show-toplevel", PASS),
    ("for-each-ref", "git for-each-ref refs/heads", DENY),
    ("show-ref", "git show-ref --heads", DENY),
    ("ls-remote", "git ls-remote origin", DENY),
    ("describe", "git describe --tags", DENY),
    ("log --all", "git log --oneline --all", DENY),
    ("log --branches", "git log --branches=feature/*", DENY),
    ("log origin/main", "git log --oneline origin/main -5", DENY),
    ("show origin file", "git show origin/main:README.md", DENY),
    ("diff against origin", "git diff origin/main...HEAD --stat", DENY),
    ("log passes", "git log --oneline -5", PASS),
    ("log with path passes", "git log --oneline -3 -- .yarn yarn.lock", PASS),
    ("show hash passes", "git show 62a74ba --stat", PASS),
    ("show HEAD file passes", "git show HEAD:chart/values.yaml", PASS),
    ("diff passes", "git diff --stat", PASS),
    ("status -sb passes", "git status -sb", PASS),
    ("tag list passes", "git tag --sort=-creatordate", PASS),
    ("remote -v passes", "git remote -v", PASS),
    ("in a pipe", "git branch -r | head", DENY),
    ("after &&", "cd /home/user/other && git branch --show-current", DENY),
    ("no git passes", "ls -la", PASS),
    ("word git in grep passes", "grep -rn 'git' README.md", PASS),
]


def outcome(out):
    if not out:
        return PASS
    output = json.loads(out)["hookSpecificOutput"]
    return DENY if output.get("permissionDecision") == "deny" else PASS


failures = 0
for label, command, expected in CASES:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    out = subprocess.run(["python3", HOOK], input=payload, capture_output=True, text=True).stdout.strip()
    got = outcome(out)
    ok = got == expected
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       expected={expected} got={got}")

print()
print(f"{len(CASES) - failures}/{len(CASES)} passed")
raise SystemExit(1 if failures else 0)
