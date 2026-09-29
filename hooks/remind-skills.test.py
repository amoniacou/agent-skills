import json
import os
import subprocess
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "remind-skills.py")
ROOT = "/home/user/project"

NAMING = "agent-skills:naming"
PRINCIPLES = "agent-skills:principles"
TESTING = "agent-skills:testing"

EXISTING_RUBY = "class Consumer\n  def run\n  end\nend\n"

CASES = [
    ("new ruby class", "Write", "app/publisher.rb", {"content": "class Publisher\n  def publish\n  end\nend\n"}, {NAMING}),
    ("go struct and func", "Write", "cmd/main.go", {"content": "type Client struct{}\n\nfunc NewClient() *Client {}\n"}, {NAMING}),
    ("ts interface", "Write", "src/store.ts", {"content": "export interface Store {\n  get(): string\n}\n"}, {NAMING, PRINCIPLES}),
    ("ruby base class", "Write", "lib/base_type.rb", {"content": "class BaseType\n  def validate!\n    raise NotImplementedError\n  end\nend\n"}, {NAMING, PRINCIPLES}),
    ("subclass of base", "Edit", "lib/email.rb", {"old_string": "", "new_string": "class EmailType < BaseType\nend\n"}, {NAMING, PRINCIPLES}),
    ("python factory", "Write", "app/x.py", {"content": "def build():\n    return ClientFactory()\n"}, {NAMING, PRINCIPLES}),
    ("edit body only", "Edit", "app/consumer.rb", {"old_string": "  def run\n  end", "new_string": "  def run\n    start\n  end"}, set()),
    ("rename method", "Edit", "app/consumer.rb", {"old_string": "  def run", "new_string": "  def start"}, {NAMING}),
    ("rewrite existing file unchanged names", "Write", "EXISTING", {"content": EXISTING_RUBY.replace("end\nend", "  run\n  end\nend")}, set()),
    ("rewrite existing file new method", "Write", "EXISTING", {"content": EXISTING_RUBY.replace("end\nend", "end\n  def stop\n  end\nend")}, {NAMING}),
    ("new markdown file: only file name", "Write", "README.md", {"content": "class Foo\ninterface Bar\n"}, {NAMING}),
    ("new yaml file: only file name", "Write", "values.yaml", {"content": "type: service\n"}, {NAMING}),
    ("yaml edit ignored", "Edit", "values.yaml", {"old_string": "a: 1", "new_string": "type: service"}, set()),
    ("scratch file in /tmp ignored", "Write", "/tmp/claude-1000/notes.md", {"content": "notes\n"}, set()),
    ("bash tool ignored", "Bash", "", {"command": "echo class Foo"}, set()),
    ("new go test file", "Write", "pkg/client_test.go", {"content": "package pkg\n\nfunc TestClient(t *testing.T) {}\n"}, {NAMING, TESTING}),
    ("new rspec file", "Write", "spec/consumer_spec.rb", {"content": "RSpec.describe Consumer do\n  it \"starts\" do\n  end\nend\n"}, {NAMING, TESTING}),
    ("new pytest file", "Write", "tests/test_client.py", {"content": "def test_client():\n    pass\n"}, {NAMING, TESTING}),
    ("new ts spec file", "Write", "src/store.spec.ts", {"content": "it('works', () => {})\n"}, {NAMING, TESTING}),
    ("rspec edit adds example", "Edit", "spec/consumer_spec.rb", {"old_string": "end\nend", "new_string": "end\n  it \"stops\" do\n  end\nend"}, {TESTING}),
    ("go test edit adds sleep", "Edit", "pkg/client_test.go", {"old_string": "\tstart()", "new_string": "\tstart()\n\ttime.Sleep(time.Second)"}, {TESTING}),
    ("rspec edit adds double", "Edit", "spec/consumer_spec.rb", {"old_string": "let(:x) { 1 }", "new_string": "let(:x) { instance_double(Channel) }"}, {TESTING}),
    ("test edit of an assertion only", "Edit", "spec/consumer_spec.rb", {"old_string": "eq(1)", "new_string": "eq(2)"}, set()),
    ("sleep outside tests ignored", "Edit", "app/worker.rb", {"old_string": "work", "new_string": "sleep 1\n    work"}, set()),
]


def reminded(tool, path, data):
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": path, **data}})
    out = subprocess.run(["python3", HOOK], input=payload, capture_output=True, text=True).stdout.strip()
    if not out:
        return set(), ""
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    return {skill for skill in (NAMING, PRINCIPLES, TESTING) if skill in context}, context


with tempfile.NamedTemporaryFile("w", suffix=".rb", delete=False) as handle:
    handle.write(EXISTING_RUBY)
    existing = handle.name

failures = 0
for label, tool, path, data, expected in CASES:
    if path == "EXISTING":
        path = existing
    elif path and not path.startswith("/"):
        path = os.path.join(ROOT, path)
    got, context = reminded(tool, path, data)
    ok = got == expected
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       expected={sorted(expected)} got={sorted(got)}\n{context}")

os.unlink(existing)

print()
print(f"{len(CASES) - failures}/{len(CASES)} passed")
raise SystemExit(1 if failures else 0)
