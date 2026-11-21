import json
import os
import pathlib
import subprocess
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debate.py")

FAKE_TOOL = """#!/usr/bin/env python3
import json, os, pathlib, sys
name = os.path.basename(sys.argv[0])
fake = pathlib.Path(os.environ["FAKE_DIR"])
with open(fake / "calls.jsonl", "a") as handle:
    handle.write(json.dumps([name, *sys.argv[1:]]) + "\\n")
args = sys.argv[1:]
if name == "hc" and args[0] == "get":
    if (fake / "hc.get-error").exists():
        sys.stderr.write("cannot open core lock\\n")
        sys.exit(5)
    taken = (fake / "hc.taken").read_text().split() if (fake / "hc.taken").exists() else []
    finished = (fake / "hc.finished").read_text().split() if (fake / "hc.finished").exists() else []
    if args[1] in taken:
        print(json.dumps({"address": "t50", "state": "live"}))
        sys.exit(0)
    if args[1] in finished:
        print(json.dumps({"address": "t51", "state": "finished"}))
        sys.exit(0)
    if args[1].startswith("review-"):
        sys.exit(3)
    labels = {} if (fake / "hc.no-labels").exists() else {"herdr.space": "sp1", "herdr.tab": "tb1"}
    print(json.dumps({"address": args[1], "state": "live", "labels": labels}))
    sys.exit(0)
if name == "hc" and args[0] == "run":
    if (fake / "hc.fail").exists():
        sys.stderr.write("no core\\n")
        sys.exit(5)
    sent = not (fake / "hc.not-sent").exists()
    print(json.dumps({"address": "t99", "state": "live", "first_message": {"sent": sent}}))
if name == "herdr-app":
    misses_file = fake / "herdr-app.misses"
    misses = int(misses_file.read_text()) if misses_file.exists() else 0
    if misses:
        misses_file.write_text(str(misses - 1))
        print(json.dumps({"error": "no running terminal"}))
        sys.exit(1)
    print(json.dumps({"pending": True}))
"""

OTHER_RULE = 'prefix_rule(pattern=["git", "status"], decision="allow")'
HC_RULE = 'prefix_rule(pattern=["hc", "send"], decision="allow")'

failures = 0
total = 0


def check(label, got, expected):
    global failures, total
    total += 1
    ok = got == expected
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       expected={expected!r} got={got!r}")


def write_file(root, path, text):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as handle:
        handle.write(text)


def run_git(root, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root, check=True, capture_output=True)


def create_repository(base, changed=True):
    root = tempfile.mkdtemp(dir=base)
    run_git(root, "init", "-q")
    write_file(root, "main.go", "package main\n")
    run_git(root, "add", ".")
    run_git(root, "commit", "-q", "-m", "init")
    if changed:
        write_file(root, "main.go", "package main\n\nfunc main() {}\n")
    return root


with tempfile.TemporaryDirectory() as base:
    bin_dir = os.path.join(base, "bin")
    fake_dir = os.path.join(base, "fake")
    runtime_dir = os.path.join(base, "run")
    codex_home = os.path.join(base, "codex")
    home = os.path.join(base, "home")
    installed_templates = os.path.join(home, ".config", "herdr-core", "templates")
    shipped_templates = os.path.join(os.path.dirname(os.path.dirname(SCRIPT)), "assets", "templates")
    os.makedirs(fake_dir)
    os.makedirs(runtime_dir)
    for tool in ("hc", "herdr-app"):
        write_file(bin_dir, tool, FAKE_TOOL)
        os.chmod(os.path.join(bin_dir, tool), 0o755)
    clean_env = {key: value for key, value in os.environ.items() if key != "HC_TERMINAL_ID"}
    base_env = {**clean_env, "FAKE_DIR": fake_dir, "PATH": bin_dir + os.pathsep + os.environ["PATH"], "XDG_RUNTIME_DIR": runtime_dir, "CODEX_HOME": codex_home, "HOME": home}
    herdr_env = {**base_env, "HC_TERMINAL_ID": "t7"}
    repository = create_repository(base)
    seen_directories = set()

    def install_templates(states):
        for agent, state in states.items():
            name = f"amoniac-review-{agent}.md"
            target = os.path.join(installed_templates, name)
            if state == "missing":
                if os.path.exists(target):
                    os.remove(target)
                continue
            text = pathlib.Path(shipped_templates, name).read_text()
            write_file(installed_templates, name, text if state == "same" else text + "old line\n")

    def reset_fakes(rules=(), taken=(), finished=(), fail=False, pane_misses=0, get_error=False, no_labels=False, not_sent=False, templates=None):
        install_templates(templates or {"claude": "same", "codex": "same"})
        for name in ("calls.jsonl", "hc.taken", "hc.finished", "hc.fail", "hc.get-error", "hc.no-labels", "hc.not-sent", "herdr-app.misses"):
            path = os.path.join(fake_dir, name)
            if os.path.exists(path):
                os.remove(path)
        if taken:
            write_file(fake_dir, "hc.taken", "\n".join(taken))
        if finished:
            write_file(fake_dir, "hc.finished", "\n".join(finished))
        if fail:
            write_file(fake_dir, "hc.fail", "")
        if pane_misses:
            write_file(fake_dir, "herdr-app.misses", str(pane_misses))
        if get_error:
            write_file(fake_dir, "hc.get-error", "")
        if no_labels:
            write_file(fake_dir, "hc.no-labels", "")
        if not_sent:
            write_file(fake_dir, "hc.not-sent", "")
        write_file(codex_home, "rules/default.rules", "\n".join(rules) + "\n")

    def read_calls():
        path = os.path.join(fake_dir, "calls.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [json.loads(line) for line in handle]

    def find_call(calls, *prefix):
        return next((call for call in calls if call[:len(prefix)] == list(prefix)), None)

    def find_new_directories(author_id):
        parent = os.path.join(runtime_dir, "amoniac", "reviews", author_id)
        found = {os.path.join(parent, name) for name in os.listdir(parent)} if os.path.isdir(parent) else set()
        new = found - seen_directories
        seen_directories.update(found)
        return sorted(new)

    def run(args, env, cwd=repository, stdin=""):
        return subprocess.run(["python3", SCRIPT, *args], cwd=cwd, env=env, input=stdin, capture_output=True, text=True)

    for label, env, expected in [
        ("env: none", base_env, "none"),
        ("env: herdr", herdr_env, "herdr"),
        ("env: tuios variables without herdr", {**base_env, "TUIOS_ENV": "1", "TUIOS_PANE_ID": "abcdef12"}, "none"),
    ]:
        check(label, run(["env"], env).stdout.strip(), expected)

    result = run(["codex-rules"], herdr_env)
    check("codex rules in herdr", result.stdout.splitlines(), [f'host_executable(name="hc", paths=["{os.path.join(bin_dir, "hc")}"])', HC_RULE])
    check("codex rules without herdr: exit 3", run(["codex-rules"], base_env).returncode, 3)

    reset_fakes()
    result = run(["start", "diff", "claude"], base_env)
    check("no mux: exit 3", result.returncode, 3)
    check("no mux: no tool runs", read_calls(), [])

    for label, args in [
        ("gemini", ["start", "diff", "gemini"]),
        ("two agents", ["start", "diff", "claude,codex"]),
        ("no agent", ["start", "diff"]),
    ]:
        reset_fakes()
        result = run(args, herdr_env)
        check(f"{label}: exit 2", result.returncode, 2)
        check(f"{label}: tells one reviewer", "exactly one reviewer" in result.stderr, True)
        check(f"{label}: no tool runs", read_calls(), [])

    reset_fakes(rules=[OTHER_RULE])
    result = run(["start", "diff", "codex"], herdr_env)
    check("codex without the hc rule: exit 2", result.returncode, 2)
    check("codex without the hc rule: tells setup-review", "/amoniac:setup-review" in result.stderr, True)
    check("codex without the hc rule: no tool runs", read_calls(), [])

    reset_fakes()
    clean = create_repository(base, changed=False)
    result = run(["start", "diff", "claude"], herdr_env, cwd=clean)
    check("clean tree: exit 1", result.returncode, 1)
    check("clean tree: says no changes", result.stdout.strip(), "No changes to review.")
    check("clean tree: no reviewer starts", read_calls(), [])

    reset_fakes()
    result = run(["start", "plan", "docs/plans/missing.md", "claude"], herdr_env)
    check("missing plan: exit 2", result.returncode, 2)
    check("missing plan: no reviewer starts", read_calls(), [])
    find_new_directories("t7")

    def start_prompt(cwd, *args):
        reset_fakes()
        result = run(["start", *args, "claude"], herdr_env, cwd=cwd)
        found = find_new_directories("t7")
        prompt = pathlib.Path(found[0], "review-prompt.md").read_text() if found else ""
        return result, prompt

    prompts = tempfile.mkdtemp(dir=base)
    run_git(prompts, "init", "-q")
    write_file(prompts, "main.go", "package main\n")
    write_file(prompts, "main_test.go", "package main\n")
    write_file(prompts, "app.rb", "puts 1\n")
    run_git(prompts, "add", ".")
    run_git(prompts, "commit", "-q", "-m", "init")
    write_file(prompts, "main.go", "package main\n\nfunc Run() {}\n")
    write_file(prompts, "main_test.go", "package main\n\nfunc TestRun() {}\n")
    write_file(prompts, "tools/gen.py", "print(1)\n")
    write_file(prompts, "vendor/lib/lib.go", "package lib\n")
    write_file(prompts, "go.lock", "x\n")
    result, sent = start_prompt(prompts, "diff")
    check("diff prompt: exit 0", result.returncode, 0)
    check("default skills: principles and naming", ('<rules name="amoniac:principles">' in sent, '<rules name="amoniac:naming">' in sent), (True, True))
    check("go file adds go-best-practices", '<rules name="amoniac:go-best-practices">' in sent, True)
    check("go test adds testing", '<rules name="amoniac:testing">' in sent, True)
    check("untracked python adds python rules", '<rules name="python">' in sent, True)
    check("unchanged ruby file adds no ruby rules", '<rules name="ruby">' in sent, False)
    check("no chart: no helmcheck", '<rules name="amoniac:helmcheck">' in sent, False)
    check("skill frontmatter stripped", "when_to_use:" in sent, False)
    check("tracked files in the git diff command", "git diff HEAD -- main.go main_test.go\n" in sent, True)
    check("untracked file listed as new", "Read each file fully:\n\n- tools/gen.py" in sent, True)
    check("diff text not in the prompt", ("+func Run() {}" in sent, "+print(1)" in sent), (False, False))
    check("vendor excluded", "vendor/lib/lib.go" in sent, False)
    check("lock file excluded", "go.lock" in sent, False)
    check("changed files listed", "- tools/gen.py" in sent, True)

    write_file(prompts, ".agents/required-skills.json", json.dumps({
        "always": ["amoniac:testing", "golang-pro"],
        "files": {"*.py": ["amoniac:helmcheck"], "*.rb": ["amoniac:principles"]},
    }))
    result, sent = start_prompt(prompts, "diff")
    check("project skills replace defaults", '<rules name="amoniac:naming">' in sent, False)
    check("project always skill inlined", '<rules name="amoniac:testing">' in sent, True)
    check("project file glob matched", '<rules name="amoniac:helmcheck">' in sent, True)
    check("project file glob not matched", '<rules name="amoniac:principles">' in sent, False)
    check("non-amoniac skill named for the reviewer", "before you read the code, and apply them: golang-pro." in sent, True)
    os.remove(os.path.join(prompts, ".agents/required-skills.json"))

    write_file(prompts, ".agents/review.json", "{broken")
    result, sent = start_prompt(prompts, "diff")
    check("broken config fails loudly", (result.returncode, "review.json is not valid JSON" in result.stderr), (2, True))
    os.chmod(os.path.join(prompts, ".agents/review.json"), 0)
    result, sent = start_prompt(prompts, "diff")
    os.chmod(os.path.join(prompts, ".agents/review.json"), 0o644)
    check("unreadable config fails loudly", (result.returncode, "cannot read" in result.stderr and "review.json" in result.stderr), (2, True))
    write_file(prompts, ".agents/review.json", json.dumps({"exclude": ["tools/*"]}))
    result, sent = start_prompt(prompts, "diff")
    check("config exclude replaces the default", ("tools/gen.py" in sent, "go.lock" in sent), (False, True))
    os.remove(os.path.join(prompts, ".agents/review.json"))

    write_file(prompts, "docs/plans/2026-11-10-retry.md", "# Retry\n\n**Skills:** `amoniac:helmcheck`, `golang-pro`\n\n## Intent\n\nRetry the sync.\n")
    result, sent = start_prompt(prompts, "plan", "docs/plans/2026-11-10-retry.md")
    check("plan prompt: exit 0", result.returncode, 0)
    check("plan prompt has the plan-review checklist", "Does the Definition of Done prove the intent?" in sent, True)
    check("plan prompt has the plan text", "Retry the sync." in sent, True)
    check("plan Skills line inlined", '<rules name="amoniac:helmcheck">' in sent, True)
    check("plan always gets principles and naming", ('<rules name="amoniac:principles">' in sent, '<rules name="amoniac:naming">' in sent), (True, True))
    check("plan non-amoniac skill named", "before you read the code, and apply them: golang-pro." in sent, True)
    check("plan prompt has no diff", "<diff>" in sent, False)

    result = run(["start", "plan"], herdr_env, cwd=prompts)
    check("plan without a file is a usage error", (result.returncode, "plan needs the path" in result.stderr), (2, True))

    unicode_names = create_repository(base, changed=False)
    run_git(unicode_names, "config", "core.quotePath", "true")
    write_file(unicode_names, "конфіг.txt", "a\n")
    run_git(unicode_names, "add", ".")
    run_git(unicode_names, "commit", "-q", "-m", "add config")
    write_file(unicode_names, "конфіг.txt", "a\nb\n")
    write_file(unicode_names, "тест.py", "print(2)\n")
    result, sent = start_prompt(unicode_names, "diff")
    check("non-ascii names: debate starts", result.returncode, 0)
    check("non-ascii names: quoted in the git diff command, new file listed", ("git diff HEAD -- 'конфіг.txt'\n" in sent, "- тест.py" in sent), (True, True))
    check("non-ascii names: listed as plain paths", ("- конфіг.txt" in sent, "- тест.py" in sent), (True, True))

    reset_fakes()
    result = run(["start", "diff", "claude"], herdr_env)
    calls = read_calls()
    check("herdr claude: exit 0", result.returncode, 0)
    directories = find_new_directories("t7")
    check("herdr claude: one new directory under the author", len(directories), 1)
    directory = directories[0]
    prompt_file = os.path.join(directory, "review-prompt.md")
    check("herdr claude: prompt has the git diff command", "git diff HEAD --" in pathlib.Path(prompt_file).read_text(), True)
    started = find_call(calls, "hc", "run")
    agent = started[started.index("--") + 1:]
    check(
        "herdr claude: hc options before --, with the tab labels of the author",
        started[:started.index("--")],
        ["hc", "run", "--bg", "--json", "--name", "review-claude-t7", "--label", "herdr.space=sp1", "--label", "herdr.tab=tb1", "--cwd", os.path.realpath(repository)],
    )
    check("herdr claude: directory in the reviews folder", directory.startswith(os.path.join(runtime_dir, "amoniac", "reviews", "t7") + os.sep), True)
    check("herdr claude: runs the template with round 1 as its task", (agent[0], len(agent)), ("amoniac-review-claude", 2))
    check("herdr claude: round 1 names the prompt", agent[-1].startswith(f"Read the file {prompt_file} and do the review"), True)
    check("herdr claude: round 1 asks for the answer file", f"{directory}/review-1.md" in agent[-1], True)
    check("herdr claude: round 1 asks for the notice", agent[-1].endswith("hc send t7 'review-1 done'"), True)
    check("herdr claude: labels place the pane, no herdr-app call", find_call(calls, "herdr-app"), None)
    check("herdr claude: instructions have no placeholder", "{{" in result.stdout, False)
    check("herdr claude: instructions name the reviewer", "# Debate with review-claude-t7" in result.stdout and "hc read t99" in result.stdout, True)
    check("herdr claude: instructions give the ask command", f'debate.py" ask t99 {directory} N' in result.stdout, True)
    check("herdr claude: instructions keep the rounds and summary", "Stop the debate after round 3" in result.stdout and "**Disputed:**" in result.stdout, True)
    check("herdr claude: instructions ask the user to approve before the fix", "## Step 3: The user approves the findings" in result.stdout, True)
    check("herdr claude: instructions send the fix check as round 4", f'debate.py" ask t99 {directory} 4' in result.stdout, True)
    check("herdr claude: instructions mark a failed fix check as blocked", "this reviewer is **blocked**" in result.stdout, True)
    run_herdr_instructions = result.stdout

    reset_fakes(rules=[HC_RULE], taken=["review-codex-t7"])
    result = run(["start", "diff", "codex"], herdr_env)
    started = find_call(read_calls(), "hc", "run")
    agent = started[started.index("--") + 1:]
    codex_directory = find_new_directories("t7")[0]
    check("herdr codex: exit 0", result.returncode, 0)
    check("herdr codex: free name", started[started.index("--name") + 1], "review-codex-t7-2")
    check("herdr codex: new directory", codex_directory != directory, True)
    check("herdr codex: runs the codex template", agent[0], "amoniac-review-codex")

    for label, rules, templates, agent_name, expected in [
        ("claude template missing", [], {"claude": "missing", "codex": "same"}, "claude", "amoniac-review-claude is missing"),
        ("claude template changed", [], {"claude": "different", "codex": "same"}, "claude", "amoniac-review-claude is different"),
        ("codex template missing", [HC_RULE], {"claude": "same", "codex": "missing"}, "codex", "amoniac-review-codex is missing"),
    ]:
        reset_fakes(rules=rules, templates=templates)
        result = run(["start", "diff", agent_name], herdr_env)
        check(f"{label}: exit 2", result.returncode, 2)
        check(f"{label}: tells the state and the setup", expected in result.stderr and "/amoniac:setup-review" in result.stderr, True)
        check(f"{label}: no reviewer starts", find_call(read_calls(), "hc", "run"), None)

    reset_fakes(rules=[HC_RULE], templates={"claude": "missing", "codex": "same"})
    result = run(["start", "diff", "codex"], herdr_env)
    find_new_directories("t7")
    check("missing claude template does not stop a codex review", (result.returncode, find_call(read_calls(), "hc", "run") is not None), (0, True))

    reset_fakes(templates={"claude": "same", "codex": "different"})
    result = run(["templates"], herdr_env)
    lines = result.stdout.splitlines()
    check("templates: exit 0", result.returncode, 0)
    check("templates: the state of each installed file", [line for line in lines if line.startswith("=== ")], [
        f"=== {installed_templates}/amoniac-review-claude.md (same)",
        f"=== {installed_templates}/amoniac-review-codex.md (different)",
    ])
    check("templates: the shipped text of each file", result.stdout.count("name: amoniac-review-"), 2)

    reset_fakes(not_sent=True)
    result = run(["start", "diff", "claude"], herdr_env)
    blocked_directory = find_new_directories("t7")[0]
    check("first message not sent: exit 4", result.returncode, 4)
    check("first message not sent: instructions start with step 0", result.stdout.startswith("## Step 0: Send round 1 after the user"), True)
    check("first message not sent: step 0 sends round 1 later", f'debate.py" ask t99 {blocked_directory} 1' in result.stdout, True)

    reset_fakes(finished=["review-claude-t7"])
    result = run(["start", "diff", "claude"], herdr_env)
    find_new_directories("t7")
    started = find_call(read_calls(), "hc", "run")
    check("finished reviewer with the same name: name is reused", started[started.index("--name") + 1], "review-claude-t7")

    reset_fakes(pane_misses=2, no_labels=True)
    result = run(["start", "diff", "claude"], herdr_env)
    find_new_directories("t7")
    calls = read_calls()
    keeps = [call for call in calls if call[:3] == ["herdr-app", "do", "terminal.keep"]]
    started = find_call(calls, "hc", "run")
    check("author without tab labels: no labels for the reviewer", "--label" in started, False)
    check("author without tab labels: pane to the right", keeps[-1], ["herdr-app", "do", "terminal.keep", "--terminal", "t99", "--place", "right"])
    check("pane not known yet: exit 0", result.returncode, 0)
    check("pane not known yet: shown on the third try", len(keeps), 3)
    check("pane not known yet: no warning", "did not show its pane" in result.stderr, False)

    reset_fakes(get_error=True)
    result = run(["start", "diff", "claude"], herdr_env)
    find_new_directories("t7")
    check("hc get fails: exit 2", result.returncode, 2)
    check("hc get fails: shows the error", "cannot open core lock" in result.stderr, True)
    check("hc get fails: no reviewer starts", find_call(read_calls(), "hc", "run"), None)

    reset_fakes(fail=True)
    result = run(["start", "diff", "claude"], herdr_env)
    find_new_directories("t7")
    check("hc run fails: exit 2", result.returncode, 2)
    check("hc run fails: shows the error", "no core" in result.stderr, True)

    reset_fakes()
    result = run(["ask", "t99", directory, "1"], herdr_env)
    sent = find_call(read_calls(), "hc", "send")
    check("ask round 1: exit 0", result.returncode, 0)
    check("ask round 1: sends the review question", sent[3].startswith(f"Read the file {directory}/review-prompt.md"), True)

    question = "Round 2. Finding 1 is wrong: `parse()` doesn't read the user's file, and $HOME stays."
    reset_fakes()
    result = run(["ask", "t99", "/run/x/d1", "2"], herdr_env, stdin=question)
    sent = find_call(read_calls(), "hc", "send")
    check("herdr ask: exit 0", result.returncode, 0)
    check("herdr ask: sent to the reviewer", sent[:3], ["hc", "send", "t99"])
    check("herdr ask: question kept as it is", sent[3].startswith(question + " "), True)
    check("herdr ask: round 2 answer file", "/run/x/d1/review-2.md" in sent[3], True)
    check("herdr ask: round 2 notice", sent[3].endswith("hc send t7 'review-2 done'"), True)

    write_file(directory, "review-2.md", "KEEP 1: it's right.\n")
    result = run(["answer", directory, "2"], herdr_env)
    check("answer: exit 0", result.returncode, 0)
    check("answer: prints the file", result.stdout, "KEEP 1: it's right.\n\n")
    result = run(["answer", directory, "3"], herdr_env)
    check("answer not written yet: exit 1", result.returncode, 1)
    check("answer not written yet: says so", "no answer file" in result.stderr, True)
    check("herdr instructions print the answer with the script", f'debate.py" answer {directory} N' in run_herdr_instructions, True)

    reset_fakes()
    result = run(["ask", "t99", "/run/x/d1", "2"], herdr_env, stdin="  \n")
    check("ask without a question: exit 2", result.returncode, 2)
    check("ask without a question: nothing sent", read_calls(), [])

print()
print(f"{total - failures}/{total} passed")
raise SystemExit(1 if failures else 0)
