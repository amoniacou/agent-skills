import json
import os
import subprocess
import tempfile
import uuid

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "required-skills.py")

CONFIG = {
    "always": ["amoniac:principles", "amoniac:naming"],
    "files": {
        "*.go": ["amoniac:principles", "amoniac:go-best-practices", "golang-pro"],
        "*_test.go": ["amoniac:testing"],
        "charts/**/*.yaml": ["amoniac:helmcheck"],
    },
}


def run(payload, env):
    out = subprocess.run(["python3", HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env).stdout.strip()
    if not out:
        return []
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    return reason.split("loaded first: ")[1].split(". Load")[0].split(", ")


def call(root, session, env, tool="Edit", tool_input=None):
    return run({
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "session_id": session,
        "cwd": root,
        "tool_input": tool_input or {"file_path": os.path.join(root, "cmd/main.go")},
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

    always = ["amoniac:principles", "amoniac:naming"]

    def edit(session, path, tool="Edit"):
        return call(root, session, env, tool, {"file_path": path if path.startswith("/") else os.path.join(root, path)})

    s1 = str(uuid.uuid4())
    check("read blocked until always skills load", call(root, s1, env, "Read", {"file_path": "x"}), always)
    check("bash blocked too", call(root, s1, env, "Bash", {"command": "make test"}), always)
    check("mcp tool blocked too", call(root, s1, env, "mcp__docs__read", {}), always)
    check("skill tool passes", call(root, s1, env, "Skill", {"skill": "amoniac:principles"}), [])
    check("go edit lists always and file skills once", edit(s1, "cmd/main.go"),
          ["amoniac:principles", "amoniac:naming", "amoniac:go-best-practices", "golang-pro"])

    load_via_tool(s1, "amoniac:principles", env)
    check("one always skill still blocks bash", call(root, s1, env, "Bash", {"command": "ls"}), ["amoniac:naming"])

    load_via_slash(s1, "/amoniac:naming", env)
    check("always loaded passes read", call(root, s1, env, "Read", {"file_path": "x"}), [])
    check("always loaded passes bash", call(root, s1, env, "Bash", {"command": "ls"}), [])
    check("go edit still needs file skills", edit(s1, "cmd/main.go"), ["amoniac:go-best-practices", "golang-pro"])
    check("go test edit adds testing", edit(s1, "pkg/client_test.go"),
          ["amoniac:go-best-practices", "golang-pro", "amoniac:testing"])
    check("nested chart yaml", edit(s1, "charts/app/templates/deployment.yaml", "Write"), ["amoniac:helmcheck"])
    check("unmatched file passes", edit(s1, "README.md", "Write"), [])
    check("file outside the project passes", edit(s1, "/tmp/claude-1000/notes.go", "Write"), [])

    load_via_tool(s1, "amoniac:go-best-practices", env)
    load_via_tool(s1, "golang-pro", env)
    check("go edit passes once file skills load", edit(s1, "cmd/main.go"), [])
    check("test file still needs testing", edit(s1, "pkg/client_test.go"), ["amoniac:testing"])

    s2 = str(uuid.uuid4())
    check("other session starts empty", call(root, s2, env, "Read", {"file_path": "x"}), always)

    with tempfile.TemporaryDirectory() as bare:
        check("project without config passes", call(bare, s2, env, "Bash", {"command": "ls"}), [])

    with tempfile.TemporaryDirectory() as files_only:
        os.makedirs(os.path.join(files_only, ".agents"))
        with open(os.path.join(files_only, ".agents", "required-skills.json"), "w") as handle:
            json.dump({"files": {"*.go": ["golang-pro"]}}, handle)
        check("files-only config does not block bash", call(files_only, s2, env, "Bash", {"command": "ls"}), [])
        check("files-only config blocks go edit",
              call(files_only, s2, env, "Edit", {"file_path": os.path.join(files_only, "main.go")}), ["golang-pro"])

    def session_start(cwd):
        payload = json.dumps({"hook_event_name": "SessionStart", "session_id": s2, "cwd": cwd})
        out = subprocess.run(["python3", HOOK], input=payload, capture_output=True, text=True, env=env).stdout.strip()
        if not out:
            return ""
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]

    context = session_start(root)
    lines = context.split("\n")
    check("session start names always skills and blocks every tool",
          "amoniac:principles, amoniac:naming" in lines[0] and "Every tool except Skill" in lines[0], True)
    check("session start lists file skills per glob",
          [line for line in lines[1:] if "*.go" in line or "*_test.go" in line or "charts/**/*.yaml" in line],
          [
              "Before a Write or Edit of *.go files, load: amoniac:principles, amoniac:go-best-practices, golang-pro.",
              "Before a Write or Edit of *_test.go files, load: amoniac:testing.",
              "Before a Write or Edit of charts/**/*.yaml files, load: amoniac:helmcheck.",
          ])
    with tempfile.TemporaryDirectory() as bare:
        check("session start without config is silent", session_start(bare), "")

print()
print(f"{total - failures}/{total} passed")
raise SystemExit(1 if failures else 0)
