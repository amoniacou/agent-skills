import json
import os
import subprocess

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "allow-debate-commands.py")
ROOT = "/plugins/amoniac"
SCRIPT = f'python3 "{ROOT}/skills/review/scripts/debate.py"'
DIRECTORY = "/run/user/1000/amoniac/t7/20261112-220531-8vkj7jqe"

ALLOW = "allow"
NONE = "none"

QUESTION = "Round 2. Finding 1 is wrong: `parse()` doesn't read the user's file; $HOME | x > y."

CASES = [
    (ALLOW, "env", f"{SCRIPT} env"),
    (ALLOW, "start a diff", f"{SCRIPT} start diff codex"),
    (ALLOW, "start a plan", f"{SCRIPT} start plan docs/plans/2026-11-12-x.md claude"),
    (ALLOW, "answer", f"{SCRIPT} answer {DIRECTORY} 2"),
    (ALLOW, "answer, script path without quotes", f"python3 {ROOT}/skills/review/scripts/debate.py answer {DIRECTORY} 1"),
    (NONE, "debate.py in the old scripts directory", f'python3 "{ROOT}/scripts/debate.py" answer {DIRECTORY} 1'),
    (ALLOW, "ask with one quoted heredoc", f"{SCRIPT} ask t21 {DIRECTORY} 2 <<'QUESTION'\n{QUESTION}\nQUESTION"),
    (ALLOW, "ask with a final newline", f"{SCRIPT} ask t21 {DIRECTORY} 2 <<'QUESTION'\n{QUESTION}\nQUESTION\n"),
    (ALLOW, "hc wait", "hc wait --children any --json --timeout 1800"),
    (ALLOW, "hc read", "hc read t21"),
    (ALLOW, "hc read with lines", "hc read t21 --lines 50"),
    (ALLOW, "tuios wait for mail", "tuios wait-for agent-message -w 4e2daa02-9c8f-4721-9264-62f3f71d6600 --timeout 1800000"),
    (ALLOW, "tuios read mail", "tuios read-agent-messages -w 4e2daa02-9c8f-4721-9264-62f3f71d6600 --unread --json"),
    (ALLOW, "tuios list agents", "tuios list-agents --json"),
    (ALLOW, "tuios peek prompt", "tuios peek-prompt -w 764af0ce-27e2-42b9-82e7-3e0912900f11"),
    (NONE, "tuios send mail", "tuios send-agent-message -w 764af0ce 'x'"),
    (NONE, "tuios wait chained", "tuios wait-for agent-message -w 4e2daa02 --timeout 1; rm x"),
    (NONE, "tuios read all mail", "tuios read-agent-messages -w 4e2daa02 --json"),
    (NONE, "chained after answer", f"{SCRIPT} answer {DIRECTORY} 2; rm -rf x"),
    (NONE, "and after start", f"{SCRIPT} start diff codex && curl x"),
    (NONE, "substitution in start", f"{SCRIPT} start diff $(rm x)"),
    (NONE, "backtick in answer", f"{SCRIPT} answer `rm x` 2"),
    (NONE, "redirect after env", f"{SCRIPT} env > /etc/x"),
    (NONE, "answer without a round", f"{SCRIPT} answer {DIRECTORY}"),
    (NONE, "unquoted heredoc", f"{SCRIPT} ask t21 {DIRECTORY} 2 <<QUESTION\n$(rm x)\nQUESTION"),
    (NONE, "command after the end marker", f"{SCRIPT} ask t21 {DIRECTORY} 2 <<'QUESTION'\nx\nQUESTION\nrm -rf x"),
    (NONE, "end marker inside the body", f"{SCRIPT} ask t21 {DIRECTORY} 2 <<'QUESTION'\nx\nQUESTION\nrm -rf x\nQUESTION"),
    (NONE, "heredoc not closed", f"{SCRIPT} ask t21 {DIRECTORY} 2 <<'QUESTION'\nx"),
    (NONE, "ask with a chain before the heredoc", f"{SCRIPT} ask t21 {DIRECTORY} 2; rm x <<'QUESTION'\nx\nQUESTION"),
    (NONE, "debate.py in another directory", f'python3 "/tmp/evil/scripts/debate.py" answer {DIRECTORY} 2'),
    (NONE, "other subcommand", f"{SCRIPT} codex-rules"),
    (NONE, "hc send", "hc send t7 'review-1 done'"),
    (NONE, "hc kill", "hc kill t21"),
    (NONE, "hc wait for one terminal", "hc wait t21"),
    (NONE, "hc read chained", "hc read t21; rm x"),
    (NONE, "hc read with an unknown option", "hc read t21 --json"),
    (NONE, "plain command", "ls -la"),
]


def verdict(command, env):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    out = subprocess.run(["python3", HOOK], input=payload, capture_output=True, text=True, env=env).stdout.strip()
    if not out:
        return NONE
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


env = {**os.environ, "CLAUDE_PLUGIN_ROOT": ROOT}
cases = [(expected, label, command, env) for expected, label, command in CASES]
no_root = {key: value for key, value in os.environ.items() if key != "CLAUDE_PLUGIN_ROOT"}
cases.append((NONE, "no plugin root in the environment", f"{SCRIPT} env", no_root))

failures = 0
for expected, label, command, case_env in cases:
    got = verdict(command, case_env)
    ok = got == expected
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} [{expected:5}] {label}")
    if not ok:
        print(f"       got={got}")

print()
print(f"{len(cases) - failures}/{len(cases)} passed")
raise SystemExit(1 if failures else 0)
