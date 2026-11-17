import json
import os
import subprocess
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "block-comments.py")

ALLOW = "allow"
DENY = "deny"

TRIPLE = '"' * 3

CASES = [
    (DENY, "write python comment", "a.py", "x = 1\n# set x\n"),
    (DENY, "write js comment", "a.js", "const x = 1\n// set x\n"),
    (DENY, "write shell comment", "a.sh", "#!/bin/sh\n# run it\necho hi\n"),
    (DENY, "write yaml comment", "a.yaml", "a: 1\n# the a value\n"),
    (ALLOW, "write python without comments", "a.py", "x = 1\n"),
    (ALLOW, "write shebang only", "a.py", "#!/usr/bin/env python3\nx = 1\n"),
    (ALLOW, "write noqa marker", "a.py", "import os  \n# noqa: F401\n"),
    (ALLOW, "write markdown headings", "a.md", "# Title\n\n## Part\n"),
    (ALLOW, "python triple-quoted markdown", "a.py", f"PLAN = {TRIPLE}# Title\n\n## Decisions\n\n- one\n{TRIPLE}\n"),
    (ALLOW, "python single-quote triple string", "a.py", "TEXT = '''\n# not a comment\n'''\n"),
    (DENY, "python comment after a triple string", "a.py", f"TEXT = {TRIPLE}\n## text\n{TRIPLE}\n# real comment\n"),
    (DENY, "python comment in a broken file", "a.py", f"TEXT = {TRIPLE}\nunclosed\n# real comment\n"),
]


def verdict(name, content):
    with tempfile.TemporaryDirectory() as base:
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.path.join(base, name), "content": content}})
        result = subprocess.run(["python3", HOOK], input=payload, capture_output=True, text=True)
    return DENY if result.returncode == 2 else ALLOW


failures = 0
for expected, label, name, content in CASES:
    got = verdict(name, content)
    ok = got == expected
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} [{expected:5}] {label}")

print()
print(f"{len(CASES) - failures}/{len(CASES)} passed")
raise SystemExit(1 if failures else 0)
