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
