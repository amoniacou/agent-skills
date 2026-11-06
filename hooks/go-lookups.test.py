import json
import os
import subprocess

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "go-lookups.py")

DENY, REMIND, PASS = "deny", "remind", "pass"

CASES = [
    ("grep in module cache", "Bash", {"command": "grep -n 'func ' /home/user/go/pkg/mod/github.com/gin-contrib/sessions@v1.1.2/sessions.go"}, DENY),
    ("rg in module cache", "Bash", {"command": "rg MaxAge /home/user/go/pkg/mod/github.com/x/y@v1.0.0"}, DENY),
    ("cat .mod from download cache", "Bash", {"command": "cat /home/user/go/pkg/mod/cache/download/github.com/x/y/@v/v1.0.0.mod"}, DENY),
    ("go -C into module cache", "Bash", {"command": "go -C /home/user/go/pkg/mod/github.com/x/y@v1.0.0 doc -all ."}, DENY),
    ("go doc piped to grep", "Bash", {"command": "go doc github.com/mxschmitt/playwright-go.Page | grep -n 'GetByRole\\|WaitForURL'"}, DENY),
    ("go doc -all piped to rg", "Bash", {"command": "go doc -all github.com/x/y | rg AriaRoleLink"}, DENY),
    ("go doc passes", "Bash", {"command": "go doc -all github.com/gin-contrib/sessions"}, PASS),
    ("go doc symbol passes", "Bash", {"command": "go doc github.com/mxschmitt/playwright-go.Page.Screenshot"}, PASS),
    ("go doc piped to head passes", "Bash", {"command": "go doc -all github.com/x/y | head -50"}, PASS),
    ("go get passes", "Bash", {"command": "go get github.com/gin-contrib/sessions@v1.1.2"}, PASS),
    ("grep with --include=*.go reminds", "Bash", {"command": "grep -rn 'startServer(\\|signedIn()' internal/api --include=*_test.go -c"}, REMIND),
    ("grep of a go file reminds", "Bash", {"command": "grep -n 'func channelChanged' -A 25 internal/controller/projects/watches.go"}, REMIND),
    ("rg -t go reminds", "Bash", {"command": "rg -t go 'ConvoyName' internal"}, REMIND),
    ("rg -g '*.go' reminds", "Bash", {"command": "rg -g '*.go' ConvoyName internal"}, REMIND),
    ("grep of yaml passes", "Bash", {"command": "grep -rn 'type: release' internal/project/testdata --include=*.yaml"}, PASS),
    ("grep of docs passes", "Bash", {"command": "grep -n '^## ' docs/design/ui-api.md"}, PASS),
    ("grep of test output passes", "Bash", {"command": "make test-pkg PKG=./internal/api 2>&1 | grep -E 'FAIL|ok'"}, PASS),
    ("read module cache file", "Read", {"file_path": "/home/user/go/pkg/mod/github.com/x/y@v1.0.0/y.go"}, DENY),
    ("read repo go file passes", "Read", {"file_path": "/home/user/project/internal/api/server.go"}, PASS),
    ("grep tool in module cache", "Grep", {"pattern": "MaxAge", "path": "/home/user/go/pkg/mod/github.com/x/y@v1.0.0"}, DENY),
    ("grep tool with go glob reminds", "Grep", {"pattern": "ConvoyName", "path": "/home/user/project", "glob": "*.go"}, REMIND),
    ("grep tool with go type reminds", "Grep", {"pattern": "ConvoyName", "path": "/home/user/project", "type": "go"}, REMIND),
    ("grep tool on a go file reminds", "Grep", {"pattern": "ConvoyName", "path": "/home/user/project/internal/names.go"}, REMIND),
    ("grep tool in repo passes", "Grep", {"pattern": "MaxAge", "path": "/home/user/project"}, PASS),
    ("edit tool ignored", "Edit", {"file_path": "/home/user/go/pkg/mod/github.com/x/y@v1.0.0/y.go", "old_string": "a", "new_string": "b"}, PASS),
]


def outcome(out):
    if not out:
        return PASS
    output = json.loads(out)["hookSpecificOutput"]
    if output.get("permissionDecision") == "deny":
        return DENY
    if output.get("additionalContext"):
        return REMIND
    return PASS


failures = 0
for label, tool, data, expected in CASES:
    payload = json.dumps({"tool_name": tool, "tool_input": data})
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
