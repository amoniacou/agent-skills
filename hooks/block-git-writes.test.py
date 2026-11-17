import json
import os
import subprocess

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "block-git-writes.py")

ALLOW = "allow"
DENY = "deny"

CASES = [
    (DENY, "git push origin main"),
    (DENY, "git commit -m 'fix'"),
    (DENY, "git add ."),
    (DENY, "git reset --hard HEAD~1"),
    (DENY, "git checkout -b feature"),
    (DENY, "git config user.name x"),
    (DENY, "git branch -d old"),
    (DENY, "git tag v1.0"),
    (DENY, "git remote add upstream https://example.com/x.git"),
    (DENY, "git stash pop"),
    (DENY, "git -C ../other add file"),
    (DENY, "sudo git push"),
    (DENY, "echo $(git push)"),
    (DENY, "git status && git commit -m x"),
    (DENY, "bash -c 'git push'"),
    (DENY, "printf %s \\\"; git config user.name example"),
    (DENY, "bash --noprofile -c 'git config user.name example'"),
    (DENY, "true # don't change files\ngit config user.name example"),
    (DENY, "echo \"$( (true); git config user.name example)\""),
    (DENY, "cat <<'EOF'\nIt's text.\nEOF\ngit config user.name example"),
    (DENY, "cat <<-\"EOF\"\n\tIt's text.\n\tEOF\ngit config user.name example"),
    (DENY, "cat <<EOF\nIt's `git push`\nEOF"),
    (ALLOW, "git log --format=\"$(cat <<'EOF'\nIt's %h\nEOF\n)\""),
    (ALLOW, "git status # don't push"),
    (ALLOW, "echo a#b && git status"),
    (ALLOW, "git status"),
    (ALLOW, "git log --oneline -5"),
    (ALLOW, "git log --oneline | head -5"),
    (ALLOW, "git diff HEAD"),
    (ALLOW, "git show HEAD:README.md"),
    (ALLOW, "git config --get user.name"),
    (ALLOW, "git branch -a"),
    (ALLOW, "git tag -l"),
    (ALLOW, "git remote -v"),
    (ALLOW, "git stash list"),
    (ALLOW, "git -C ../other status"),
    (ALLOW, "ls -la"),
]


def verdict(command):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    out = subprocess.run(["python3", HOOK], input=payload, capture_output=True, text=True).stdout.strip()
    if not out:
        return ALLOW, ""
    parsed = json.loads(out)["hookSpecificOutput"]
    return parsed["permissionDecision"], parsed["permissionDecisionReason"]


failures = 0
for expected, command in CASES:
    got, reason = verdict(command)
    ok = got == expected
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} [{expected:5}] {command[:72]}")
    if not ok:
        print(f"       got={got} {reason[:80]}")

print()
print(f"{len(CASES) - failures}/{len(CASES)} passed")
raise SystemExit(1 if failures else 0)
