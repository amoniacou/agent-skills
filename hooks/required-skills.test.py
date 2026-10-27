import json
import os
import subprocess
import tempfile
import uuid

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "required-skills.py")

CONFIG = {
    "*.go": ["amoniac:principles", "amoniac:go-best-practices", "golang-pro"],
    "*_test.go": ["amoniac:testing"],
    "charts/**/*.yaml": ["amoniac:helmcheck"],
}


def run(payload, env):
    out = subprocess.run(["python3", HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env).stdout.strip()
    if not out:
        return []
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    return reason.split("loaded first: ")[1].split(". Load")[0].split(", ")


def edit(root, session, path, env, tool="Edit"):
    return run({
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "session_id": session,
        "cwd": root,
        "tool_input": {"file_path": path if path.startswith("/") else os.path.join(root, path)},
    }, env)


def load_via_tool(session, skill, env):
    run({"hook_event_name": "PostToolUse", "tool_name": "Skill", "session_id": session, "tool_input": {"skill": skill}}, env)


def load_via_slash(session, skill, env):
    run({"hook_event_name": "UserPromptExpansion", "expansion_type": "slash_command", "session_id": session, "command_name": skill}, env)


failures = 0
total = 0


def check(label, got, expected):
    global failures, total
    total += 1
    ok = got == expected
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       expected={expected} got={got}")


with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as runtime:
    env = {**os.environ, "XDG_RUNTIME_DIR": runtime}
    os.makedirs(os.path.join(root, ".agents"))
    with open(os.path.join(root, ".agents", "required-skills.json"), "w") as handle:
        json.dump(CONFIG, handle)

    s1 = str(uuid.uuid4())
    check("go file, nothing loaded", edit(root, s1, "cmd/main.go", env),
          ["amoniac:principles", "amoniac:go-best-practices", "golang-pro"])
    check("go test file adds testing", edit(root, s1, "pkg/client_test.go", env),
          ["amoniac:principles", "amoniac:go-best-practices", "golang-pro", "amoniac:testing"])
    check("nested chart yaml", edit(root, s1, "charts/app/templates/deployment.yaml", env, "Write"), ["amoniac:helmcheck"])
    check("unmatched file passes", edit(root, s1, "README.md", env, "Write"), [])
    check("file outside the project passes", edit(root, s1, "/tmp/claude-1000/notes.go", env, "Write"), [])
    check("bash tool passes", edit(root, s1, "cmd/main.go", env, "Bash"), [])

    load_via_tool(s1, "amoniac:principles", env)
    load_via_slash(s1, "/amoniac:go-best-practices", env)
    check("two loaded, one missing", edit(root, s1, "cmd/main.go", env), ["golang-pro"])

    load_via_tool(s1, "golang-pro", env)
    check("all loaded passes", edit(root, s1, "cmd/main.go", env), [])
    check("test file still needs testing", edit(root, s1, "pkg/client_test.go", env), ["amoniac:testing"])

    s2 = str(uuid.uuid4())
    check("other session starts empty", edit(root, s2, "cmd/main.go", env),
          ["amoniac:principles", "amoniac:go-best-practices", "golang-pro"])

    with tempfile.TemporaryDirectory() as bare:
        check("project without config passes", edit(bare, s2, "main.go", env), [])

print()
print(f"{total - failures}/{total} passed")
raise SystemExit(1 if failures else 0)
