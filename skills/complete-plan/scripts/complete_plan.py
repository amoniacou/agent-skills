#!/usr/bin/env python3
import argparse
import os
import re
import shlex
import subprocess
import sys

TITLE = re.compile(r"^# .+$", re.M)
GOAL = re.compile(r"^\*\*Goal:\*\*.*$", re.M)
SECTION = re.compile(r"^## (.+)$", re.M)
OPEN_BOX = re.compile(r"^\s*- (?:\S+ )?\[ \] .*$", re.M)
ITERATION = re.compile(r"^### (.+)\n(?:(?!### ).*\n)*?\*\*Status:\*\*\s*(.+?)\s*$", re.M)


class CompletePlanError(Exception):
    pass


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as error:
        raise CompletePlanError(f"cannot read {path}: {error.strerror}")


def find_decision_sections(text: str) -> list[str]:
    headings = list(SECTION.finditer(text))
    sections = []
    for index, heading in enumerate(headings):
        if "decision" not in heading.group(1).lower():
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections.append(text[heading.start() : end].strip())
    return sections


def find_open_items(text: str) -> list[str]:
    boxes = [box.strip() for box in OPEN_BOX.findall(text)]
    iterations = [f"{name}: {status}" for name, status in ITERATION.findall(text) if status != "done"]
    return boxes + iterations


def build_completed_text(text: str, path: str) -> str:
    title = TITLE.search(text)
    if not title:
        raise CompletePlanError(f"{path} has no title line")
    sections = find_decision_sections(text)
    if not sections:
        raise CompletePlanError(f"{path} has no Decisions section")
    goal = GOAL.search(text)
    parts = [title.group(0)] + ([goal.group(0)] if goal else []) + sections
    return "\n\n".join(parts) + "\n"


def is_tracked(path: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", os.path.basename(path)],
        cwd=os.path.dirname(os.path.abspath(path)),
        capture_output=True,
    )
    return result.returncode == 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="complete_plan.py", description="Keep the title, Goal and Decisions of a finished plan in docs/plans/completed/.")
    parser.add_argument("plan_file")
    parser.add_argument("--force", action="store_true", help="complete the plan also with open boxes")
    args = parser.parse_args(argv)

    try:
        text = read_text(args.plan_file)
        open_items = find_open_items(text)
        if open_items and not args.force:
            print("The plan has open boxes or iterations that are not done. Close them, or run again with --force:")
            print("\n".join(open_items))
            return 1
        completed_text = build_completed_text(text, args.plan_file)
        target = os.path.join(os.path.dirname(args.plan_file), "completed", os.path.basename(args.plan_file))
        if os.path.exists(target):
            raise CompletePlanError(f"{target} already exists")
    except CompletePlanError as error:
        print(f"complete_plan: {error}", file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(completed_text)
    remove = "git rm" if is_tracked(args.plan_file) else "rm"
    print(f"Completed plan: {target}")
    print(f"Delete the plan: ! {remove} -- {shlex.quote(args.plan_file)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
