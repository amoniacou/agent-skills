import json
import os
import subprocess

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "block-file-writes.py")
ROOT = "/home/user/project"

ALLOW = "allow"
DENY = "deny"

CASES = [
    (DENY, "sed -i 's/a/b/' file.yaml"),
    (DENY, "sed --in-place 's/a/b/' file.yaml"),
    (DENY, "perl -i -pe 's/a/b/' file.yaml"),
    (DENY, "python3 -c \"open('f','w').write('x')\""),
    (DENY, "python3 - <<'PY'\nopen('skaffold.yaml','w').write('x')\nPY"),
    (DENY, "node -e \"require('fs').writeFileSync('a.json','{}')\""),
    (DENY, "grep -o 'x' images.json > images.txt"),
    (DENY, "printf 'x\\n' >> /home/user/project/chart/.gitignore"),
    (DENY, "echo hi | tee chart/values.yaml"),
    (DENY, "cat > Dockerfile <<'EOF'\nFROM alpine\nEOF"),
    (DENY, "curl -fsSL -o vendor/tool.tar.gz https://example.com/x"),
    (DENY, "yq -i '.a = 1' values.yaml"),
    (DENY, "mv a.yaml config/"),
    (DENY, "mkdir -p config && mv a.yaml config/"),
    (DENY, "rm -rf /tmp/claude-1000/x"),
    (DENY, "find . -name '*.bak' | xargs rm"),
    (DENY, "find . -print0 | xargs -0 -I {} rm {}"),
    (DENY, "echo x > \"out file.txt\""),
    (DENY, "echo \"$(date > stamp.txt)\""),
    (DENY, "echo \"`date > stamp.txt`\""),
    (DENY, "echo hi | tee -a 'notes.md'"),
    (DENY, "sh -c 'echo x > tracked.txt'"),
    (DENY, "bash -lc \"echo x > tracked.txt\""),
    (DENY, "bash --noprofile -c 'echo x > tracked.txt'"),
    (DENY, "bash -o pipefail -c 'printf x > tracked.txt'"),
    (DENY, "true # it's 'fine'\necho x > tracked.txt"),
    (DENY, "echo \"$(echo \" #\")\"; printf x > tracked.txt"),
    (DENY, "echo \"$( (echo \" #\") )\"; printf x > tracked.txt"),
    (DENY, "echo \"$(printf \"x\"; printf x > tracked.txt)\""),
    (DENY, "echo \"$(printf ')'; printf x > tracked.txt)\""),
    (DENY, "cat <<'EOF'\nIt's text.\nEOF\nprintf x > tracked.txt"),
    (DENY, "cat <<EOF\nIt's $(printf x > tracked.txt)\nEOF"),
    (ALLOW, "cat <<'EOF'\nprintf x > tracked.txt\nEOF"),
    (DENY, "bash --rcfile /tmp/rc -c 'printf x > tracked.txt'"),
    (DENY, "printf %s \\\"; echo x > tracked.txt"),
    (DENY, "find . | xargs sh -c 'cat a > b.txt'"),
    (DENY, "eval \"echo x\""),
    (DENY, "eval ls"),
    (DENY, "true && eval \"$cmd\""),
    (DENY, "sh -c 'eval x'"),
    (DENY, "/bin/zsh -lc 'rm -rf build'"),
    (ALLOW, "git commit -m \"remove eval from the parser\""),
    (DENY, "/bin/zsh -lc 'echo x > tracked.txt'"),
    (DENY, "/bin/zsh -lc \"cat a > \\\"b.txt\\\"\""),
    (ALLOW, "/bin/zsh -lc \"tuios send-agent-message -w abc 'Fix: a > b'\""),
    (ALLOW, "/bin/zsh -lc 'cat scripts/review.py'"),
    (ALLOW, "sh -c 'ls > /tmp/claude-1000/list.txt'"),
    (ALLOW, "grep -rn eval src/"),
    (ALLOW, "tuios send-agent-message -w abc --subject a \"<answer>\""),
    (ALLOW, "tuios send-agent-message -w abc 'Reply with KEEP N > DROP N'"),
    (ALLOW, "tuios send-agent-message -w abc 'Reply with: tuios x --reply-to <id> \"<answer>\". Do not'"),
    (ALLOW, "git commit -m \"map a > b in config.yaml\""),
    (ALLOW, "git log --oneline -3"),
    (ALLOW, "kubectl cp ns/pod:/data ./data"),
    (ALLOW, "helm template test chart > /tmp/claude-1000/x/rendered.yaml"),
    (ALLOW, "echo hi | tee /tmp/claude-1000/probe.txt"),
    (ALLOW, "curl -fsSL -o /tmp/skaffold https://example.com/x"),
    (ALLOW, "docker run --rm alpine id 2>/dev/null | tail -3"),
    (ALLOW, "helm lint chart 2>&1 | tail -3"),
    (ALLOW, "cat Dockerfile | head -20"),
    (ALLOW, "python3 -c \"import yaml;yaml.safe_load(open('skaffold.yaml'));print('ok')\""),
    (ALLOW, "python3 -c \"print(open('f').read())\""),
    (ALLOW, "gh api repos/x/y --jq .name"),
    (ALLOW, 'gh run view 1 --json jobs --jq \'.jobs[]|(.steps[]|"\\(.name) -> \\(.conclusion)")\''),
    (ALLOW, 'echo "a -> b"'),
    (ALLOW, "test $x -gt 5 && echo ok"),
    (ALLOW, "awk '{if ($1 >= 2) print}' file"),
    (ALLOW, "gh pr list --json number --jq '.[]|select(.number>=3)'"),
    (ALLOW, "grep -rn 'a=>b' src/"),
    (ALLOW, "gofmt -r 'a.Spec.Target.Channel -> &a.Spec.Channel' -w api internal tests"),
    (ALLOW, "gofmt -l ./internal"),
]


def verdict(command):
    payload = json.dumps({"tool_name": "Bash", "cwd": ROOT, "tool_input": {"command": command}})
    out = subprocess.run(
        ["python3", HOOK], input=payload, capture_output=True, text=True
    ).stdout.strip()
    if not out:
        return ALLOW, ""
    parsed = json.loads(out)["hookSpecificOutput"]
    return parsed["permissionDecision"], parsed["permissionDecisionReason"]


failures = 0
for expected, command in CASES:
    got, reason = verdict(command)
    ok = got == expected
    failures += 0 if ok else 1
    label = "ok  " if ok else "FAIL"
    first_line = command.splitlines()[0]
    print(f"{label} [{expected:5}] {first_line[:72]}")
    if not ok:
        print(f"       got={got} {reason[:80]}")

print()
print(f"{len(CASES) - failures}/{len(CASES)} passed")
raise SystemExit(1 if failures else 0)
