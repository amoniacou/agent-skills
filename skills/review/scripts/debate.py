#!/usr/bin/env python3
import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable

AGENTS = ("claude", "codex")
SCRIPT = os.path.abspath(__file__)
SKILL_ROOT = os.path.dirname(os.path.dirname(SCRIPT))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
ASSETS = os.path.join(SKILL_ROOT, "assets")
TEMPLATES = os.path.join(ASSETS, "templates")
PROMPT_NAME = "review-prompt.md"
REQUIRED_SKILLS = os.path.join(".agents", "required-skills.json")
REVIEW_CONFIG = os.path.join(".agents", "review.json")

DEFAULT_EXCLUDE = ["*.lock", "*.min.js", "vendor/**"]

DEFAULT_ALWAYS = ["amoniac:principles", "amoniac:naming"]

DEFAULT_FILES = {
    "*.go": ["amoniac:go-best-practices"],
    "*_test.go": ["amoniac:testing"],
    "*_spec.rb": ["amoniac:testing"],
    "*_test.rb": ["amoniac:testing"],
    "test_*.py": ["amoniac:testing"],
    "*_test.py": ["amoniac:testing"],
    "*.test.*": ["amoniac:testing"],
    "*.spec.*": ["amoniac:testing"],
    "spec/*": ["amoniac:testing"],
    "test/*": ["amoniac:testing"],
    "tests/*": ["amoniac:testing"],
    "Chart.yaml": ["amoniac:helmcheck"],
    "values*.yaml": ["amoniac:helmcheck"],
    "charts/*.yaml": ["amoniac:helmcheck"],
    "*/templates/*.yaml": ["amoniac:helmcheck"],
    "*/templates/*.tpl": ["amoniac:helmcheck"],
}

LANGUAGES = {
    "ruby": ["*.rb", "*.rake", "Gemfile"],
    "javascript": ["*.js", "*.mjs", "*.cjs", "*.jsx", "*.ts", "*.tsx", "*.vue"],
    "python": ["*.py"],
    "shell": ["*.sh", "*.bash", "*.zsh"],
}

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
SKILLS_LINE = re.compile(r"^\*\*Skills:\*\*(.*)$", re.M)

CODEX_RULE = 'prefix_rule(pattern=["hc", "send"], decision="allow")'

PANE_LABELS = ("herdr.space", "herdr.tab")

HC_NOT_FOUND = 3
MUX_MISSING = 3
NOT_READY = 4
PANE_TIMEOUT = 10
PANE_RETRY_DELAY = 0.5


class DebateError(Exception):
    pass


def unique(items: Iterable[str]) -> list[str]:
    result = []
    result.extend(item for item in items if item not in result)
    return result


def matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def read_json(path: str) -> dict | None:
    try:
        loaded = json.loads(read_text(path))
    except FileNotFoundError:
        return None
    except OSError as error:
        raise DebateError(f"cannot read {path}: {error.strerror}")
    except ValueError as error:
        raise DebateError(f"{path} is not valid JSON: {error}")
    if not isinstance(loaded, dict):
        raise DebateError(f"{path} must hold a JSON object")
    return loaded


def load_exclude(root: str) -> list[str]:
    return (read_json(os.path.join(root, REVIEW_CONFIG)) or {}).get("exclude", DEFAULT_EXCLUDE)


def load_skill_rules(root: str) -> tuple[list[str], dict[str, list[str]]]:
    loaded = read_json(os.path.join(root, REQUIRED_SKILLS))
    if loaded is None:
        return DEFAULT_ALWAYS, DEFAULT_FILES
    return list(loaded.get("always") or []), dict(loaded.get("files") or {})


def skills_for_files(root: str, files: list[str]) -> list[str]:
    always, by_pattern = load_skill_rules(root)
    skills = list(always)
    for pattern, names in by_pattern.items():
        if any(matches(path, pattern) for path in files):
            skills.extend(names)
    return unique(skills)


def skills_for_plan(root: str, plan_text: str) -> list[str]:
    found = SKILLS_LINE.search(plan_text)
    named = re.findall(r"`([^`]+)`", found.group(1)) if found else []
    return unique(load_skill_rules(root)[0] + DEFAULT_ALWAYS + named)


def build_rules_block(name: str, path: str) -> str:
    return f'<rules name="{name}">\n{FRONTMATTER.sub("", read_text(path)).strip()}\n</rules>'


def build_rules(skills: list[str], languages: Iterable[str] = ()) -> str:
    blocks = []
    others = []
    for skill in skills:
        prefix, _, name = skill.partition(":")
        path = os.path.join(PLUGIN_ROOT, "skills", name, "SKILL.md")
        if prefix == "amoniac" and os.path.isfile(path):
            blocks.append(build_rules_block(skill, path))
        else:
            others.append(skill)
    for language in languages:
        blocks.append(build_rules_block(language, os.path.join(ASSETS, "languages", f"{language}.md")))
    if others:
        blocks.append(
            "Load these skills before you read the code, and apply them: " + ", ".join(others) + "."
            " Without a Skill tool, read the SKILL.md of each skill."
        )
    return "\n\n".join(blocks)


def run_git(root: str, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise DebateError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def find_repository_root() -> str:
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else os.getcwd()


def build_diff_prompt(root: str, exclude: list[str]) -> str | None:
    def filter_excluded(paths):
        return [path for path in paths if path and not any(matches(path, pattern) for pattern in exclude)]

    tracked = filter_excluded(run_git(root, "diff", "--name-only", "-z", "HEAD").split("\0"))
    untracked = filter_excluded(run_git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    files = unique(tracked + untracked)
    if not files:
        return None

    command = " ".join(["git diff HEAD --", *map(shlex.quote, tracked)]) if tracked else "none"
    new_files = "\n".join(f"- {path}" for path in untracked) or "none"

    languages = [name for name, patterns in LANGUAGES.items() if any(matches(path, p) for path in files for p in patterns)]
    template = read_text(os.path.join(ASSETS, "diff-review.md"))
    return (
        template.replace("{{rules}}", build_rules(skills_for_files(root, files), languages))
        .replace("{{files}}", "\n".join(f"- {path}" for path in files))
        .replace("{{diff_command}}", command)
        .replace("{{new_files}}", new_files)
    )


def build_plan_prompt(root: str, plan_file: str) -> str:
    try:
        plan_text = read_text(os.path.join(root, plan_file))
    except OSError as error:
        raise DebateError(f"cannot read plan file {plan_file}: {error.strerror}")
    checklist = read_text(os.path.join(ASSETS, "plan-review.md")).strip()
    return "\n\n".join([
        checklist,
        "The rules of the skills are below. You do not need to load them.",
        build_rules(skills_for_plan(root, plan_text)),
        f"Plan file: {plan_file}",
        f"<plan>\n{plan_text.strip()}\n</plan>",
    ])


def fill_template(template: str, **values: object) -> str:
    text = read_text(os.path.join(ASSETS, template))
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text.strip()


def detect_mux(env: dict[str, str]) -> str:
    return "herdr" if env.get("HC_TERMINAL_ID") else "none"


def check_codex_rule(env: dict[str, str]) -> None:
    codex_home = env.get("CODEX_HOME") or os.path.join(env.get("HOME", ""), ".codex")
    path = os.path.join(codex_home, "rules", "default.rules")
    try:
        lines = {line.strip() for line in read_text(path).splitlines()}
    except OSError:
        lines = set()
    if CODEX_RULE not in lines:
        raise DebateError(f"codex cannot reply from its sandbox: run /amoniac:setup-review first ({path} has no hc rule)")


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        raise DebateError(f"{command[0]} is not on PATH")


def describe_failure(command: list[str], result: subprocess.CompletedProcess) -> str:
    return f"{' '.join(command[:2])} failed (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"


def parse_json_output(command: list[str], result: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise DebateError(describe_failure(command, result))


def build_question(author: str, directory: str, round_number: int, question: str | None) -> str:
    reply = fill_template("debate-reply-herdr.md", author=author, directory=directory, round=round_number)
    if round_number == 1:
        question = fill_template("debate-round-1.md", prompt_file=os.path.join(directory, PROMPT_NAME))
    return f"{question} {reply}"


def send_question(reviewer: str, text: str) -> None:
    command = ["hc", "send", reviewer, text]
    result = run_command(command)
    if result.returncode != 0:
        raise DebateError(describe_failure(command, result))


def find_free_name(base: str) -> str:
    name = base
    number = 1
    while True:
        command = ["hc", "get", name, "--json"]
        result = run_command(command)
        if result.returncode == HC_NOT_FOUND:
            return name
        if result.returncode != 0:
            raise DebateError(describe_failure(command, result))
        if parse_json_output(command, result).get("state") != "live":
            return name
        number += 1
        name = f"{base}-{number}"


def template_name(agent: str) -> str:
    return f"amoniac-review-{agent}"


def installed_template_path(agent: str, env: dict[str, str]) -> str:
    return os.path.join(env.get("HOME", ""), ".config", "herdr-core", "templates", f"{template_name(agent)}.md")


def compare_template(agent: str, env: dict[str, str]) -> str:
    expected = read_text(os.path.join(TEMPLATES, f"{template_name(agent)}.md"))
    path = installed_template_path(agent, env)
    try:
        installed = read_text(path)
    except FileNotFoundError:
        return "missing"
    except OSError as error:
        raise DebateError(f"cannot read {path}: {error.strerror}")
    return "same" if installed == expected else "different"


def check_template(agent: str, env: dict[str, str]) -> None:
    state = compare_template(agent, env)
    if state != "same":
        raise DebateError(f"the herdr-core template {template_name(agent)} is {state}: run /amoniac:setup-review first ({installed_template_path(agent, env)})")


def show_herdr_pane(address: str) -> subprocess.CompletedProcess:
    command = ["herdr-app", "do", "terminal.keep", "--terminal", address, "--place", "right"]
    deadline = time.monotonic() + PANE_TIMEOUT
    while True:
        result = run_command(command)
        if result.returncode == 0 or time.monotonic() > deadline:
            return result
        time.sleep(PANE_RETRY_DELAY)


def find_pane_labels(author: str) -> list[str]:
    command = ["hc", "get", author, "--json"]
    result = run_command(command)
    if result.returncode != 0:
        raise DebateError(describe_failure(command, result))
    labels = parse_json_output(command, result).get("labels") or {}
    if not all(key in labels for key in PANE_LABELS):
        return []
    return [option for key in PANE_LABELS for option in ("--label", f"{key}={labels[key]}")]


def start_reviewer(agent: str, author: str, root: str, directory: str) -> tuple[str, str, bool]:
    name = find_free_name(f"review-{agent}-{author}")
    pane_labels = find_pane_labels(author)
    question = build_question(author, directory, 1, None)
    command = ["hc", "run", "--bg", "--json", "--name", name, *pane_labels, "--cwd", root, "--", template_name(agent), question]
    result = run_command(command)
    started = parse_json_output(command, result)
    if result.returncode != 0 or "address" not in started:
        raise DebateError(describe_failure(command, result))
    address = started["address"]
    if not pane_labels:
        shown = show_herdr_pane(address)
        if shown.returncode != 0:
            print(f"debate: the reviewer runs, but herdr-app did not show its pane: {shown.stdout.strip() or shown.stderr.strip()}", file=sys.stderr)
    first_message = started.get("first_message") or {}
    return address, name, bool(first_message.get("sent"))


def parse_start(argv: list[str]) -> tuple[str, str | None, str]:
    parser = argparse.ArgumentParser(prog="debate.py start", description="Start a review debate with one reviewer in herdr.")
    parser.add_argument("subject", nargs="?", default="diff", choices=["diff", "plan"])
    parser.add_argument("names", nargs="*", metavar="FILE|AGENT", help=f"plan: the plan file first; then one agent: {', '.join(AGENTS)}")
    args = parser.parse_args(argv)
    names = args.names
    plan_file = None
    if args.subject == "plan":
        if not names:
            parser.error("plan needs the path of the plan file")
        plan_file, names = names[0], names[1:]
    agents = unique(name.strip() for item in names for name in item.split(",") if name.strip())
    if len(agents) != 1 or agents[0] not in AGENTS:
        raise DebateError(f"the debate needs exactly one reviewer, claude or codex, not: {', '.join(agents) or 'none'}")
    return args.subject, plan_file, agents[0]


def start(argv: list[str], env: dict[str, str]) -> int:
    subject, plan_file, agent = parse_start(argv)
    if detect_mux(env) == "none":
        print("debate: herdr is necessary for a debate", file=sys.stderr)
        return MUX_MISSING
    if agent == "codex":
        check_codex_rule(env)
    check_template(agent, env)
    runtime_dir = env.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        raise DebateError("XDG_RUNTIME_DIR is not set")

    root = find_repository_root()
    if subject == "plan":
        prompt = build_plan_prompt(root, plan_file)
    else:
        prompt = build_diff_prompt(root, load_exclude(root))
    if prompt is None:
        print("No changes to review.")
        return 1

    author = env["HC_TERMINAL_ID"]
    author_dir = os.path.join(runtime_dir, "amoniac", "reviews", author)
    os.makedirs(author_dir, exist_ok=True)
    directory = tempfile.mkdtemp(prefix=time.strftime("%Y%m%d-%H%M%S-"), dir=author_dir)
    with open(os.path.join(directory, PROMPT_NAME), "w", encoding="utf-8") as handle:
        handle.write(prompt)

    reviewer, name, ready = start_reviewer(agent, author, root, directory)

    values = {"reviewer": reviewer, "name": name, "author": author, "directory": directory, "script": SCRIPT}
    wait = fill_template("debate-wait-herdr.md", **values)
    instructions = fill_template("debate-author.md", wait=wait, **values)
    if not ready:
        instructions = fill_template("debate-start-blocked.md", **values) + "\n\n" + instructions
    print(instructions)
    return 0 if ready else NOT_READY


def ask(argv: list[str], env: dict[str, str]) -> int:
    parser = argparse.ArgumentParser(prog="debate.py ask", description="Send a question to the reviewer, with the reply instructions of the round. Round 1 sends the review question; later rounds read the question from stdin.")
    parser.add_argument("reviewer")
    parser.add_argument("directory")
    parser.add_argument("round", type=int)
    args = parser.parse_args(argv)
    if detect_mux(env) == "none":
        raise DebateError("herdr is necessary for a debate")
    question = None
    if args.round > 1:
        question = sys.stdin.read().strip()
        if not question:
            raise DebateError("no question on stdin")
    send_question(args.reviewer, build_question(env["HC_TERMINAL_ID"], args.directory, args.round, question))
    print(f"Round {args.round} sent to {args.reviewer}.")
    return 0


def print_answer(argv: list[str], env: dict[str, str]) -> int:
    parser = argparse.ArgumentParser(prog="debate.py answer", description="Print the answer file of a round. Exit 1 when the reviewer did not write it yet.")
    parser.add_argument("directory")
    parser.add_argument("round", type=int)
    args = parser.parse_args(argv)
    path = os.path.join(args.directory, f"review-{args.round}.md")
    try:
        text = read_text(path)
    except OSError:
        print(f"debate: no answer file {path} yet", file=sys.stderr)
        return 1
    print(text)
    return 0


def print_codex_rules(argv: list[str], env: dict[str, str]) -> int:
    if detect_mux(env) == "none":
        print("debate: herdr is necessary for a debate", file=sys.stderr)
        return MUX_MISSING
    path = shutil.which("hc", path=env.get("PATH"))
    if path is None:
        raise DebateError("hc is not on PATH")
    print(f'host_executable(name="hc", paths=["{path}"])')
    print(CODEX_RULE)
    return 0


def print_templates(argv: list[str], env: dict[str, str]) -> int:
    for agent in AGENTS:
        print(f"=== {installed_template_path(agent, env)} ({compare_template(agent, env)})")
        print(read_text(os.path.join(TEMPLATES, f"{template_name(agent)}.md")), end="")
    return 0


COMMANDS = {"start": start, "ask": ask, "answer": print_answer, "codex-rules": print_codex_rules, "templates": print_templates}


def main(argv: list[str]) -> int:
    env = dict(os.environ)
    if argv[:1] == ["env"]:
        print(detect_mux(env))
        return 0
    command = COMMANDS.get(argv[0]) if argv else None
    if command is None:
        print("usage: debate.py env | codex-rules | templates | start [diff | plan FILE] AGENT | ask REVIEWER DIRECTORY ROUND < question | answer DIRECTORY ROUND", file=sys.stderr)
        return 2
    try:
        return command(argv[1:], env)
    except DebateError as error:
        print(f"debate: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
