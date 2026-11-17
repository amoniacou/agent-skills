import json
import os
import subprocess

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "block-output-filters.py")

ALLOW = "allow"
DENY = "deny"

CASES = [
    (DENY, "make test-pkg PKG=./internal/controller/projects 2>&1 | sed 's/\\x1b\\[[0-9;]*m//g' | grep -E \"^\\s+\\[FAIL\\]|^ok|^FAIL|Ran \" | head -20"),
    (DENY, "go test ./... | grep -v ok | head"),
    (DENY, "kubectl logs pod/x | awk '{print $2}'"),
    (DENY, "helm template chart | perl -ne 'print if /kind/'"),
    (DENY, "make lint 2>&1 | grep error | sort | uniq -c"),
    (DENY, "git status && go test ./... 2>&1 | tail -50 | grep FAIL"),
    (DENY, "gh pr view 12 --json files | grep path"),
    (DENY, "gh run view 123 --log | grep -i error"),
    (DENY, "gh api repos/x/y/releases | jq '.[0].tag_name'"),
    (DENY, "curl -s https://example.com/x.json | jq .version"),
    (DENY, "wget -qO- https://example.com | head"),
    (DENY, "npm view react versions | tail -5"),
    (DENY, "/bin/zsh -lc \"gh api x | jq .\""),
    (DENY, "time gh api x | jq ."),
    (ALLOW, "/bin/zsh -lc 'make test 2>&1 | tail -30'"),
    (ALLOW, "make test 2>&1 | tail -30"),
    (ALLOW, "go test ./... | grep FAIL"),
    (ALLOW, "ls | wc -l"),
    (ALLOW, "gh api repos/x/y --jq .name"),
    (ALLOW, "gh api repos/x/y/releases > /tmp/claude-1000/x/scratchpad/gh-releases.json"),
    (ALLOW, "make test > /tmp/claude-1000/x/scratchpad/test.log 2>&1"),
    (ALLOW, "git log --oneline -5"),
    (ALLOW, "grep -rn 'gh x | sed b | head' src/"),
    (ALLOW, "python3 -c \"print('x | awk | sed')\""),
    (ALLOW, "make test || make clean"),
    (ALLOW, "echo gh | grep g"),
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
