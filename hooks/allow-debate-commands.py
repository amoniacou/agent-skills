#!/usr/bin/env python3
import json
import os
import re
import sys

from bash_hook import decide

METACHARACTERS = re.compile(r"[;&|<>$`\n\r]")
DIRECTORY = r"[A-Za-z0-9/._-]+"
ADDRESS = r"[a-z0-9/_-]+"

ANSWER = re.compile(rf"answer {DIRECTORY} [0-9]+")
ASK = re.compile(rf"ask {ADDRESS} {DIRECTORY} [0-9]+ <<'([A-Za-z_][A-Za-z0-9_]*)'")
HC_WAIT = re.compile(r"hc wait --children any --json --timeout [0-9]+")
HC_READ = re.compile(rf"hc read {ADDRESS}(?: --lines [0-9]+)?")


def strip_script(command: str, root: str) -> str | None:
    script = f"{root}/skills/review/scripts/debate.py"
    for prefix in (f'python3 "{script}" ', f"python3 {script} "):
        if command.startswith(prefix):
            return command[len(prefix):]
    return None


def is_quoted_heredoc(rest: str) -> bool:
    first, _, body = rest.partition("\n")
    found = ASK.fullmatch(first)
    if not found or "\r" in rest or not body:
        return False
    tag = found.group(1)
    lines = body.split("\n")
    return lines[-1] == tag and tag not in lines[:-1]


def is_debate_command(rest: str) -> bool:
    if rest.startswith("ask "):
        return is_quoted_heredoc(rest)
    if METACHARACTERS.search(rest):
        return False
    return rest == "env" or rest.startswith("start ") or bool(ANSWER.fullmatch(rest))


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = ((payload.get("tool_input") or {}).get("command") or "").rstrip("\n")
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not command or not root:
        sys.exit(0)

    rest = strip_script(command, root)
    if rest is not None and is_debate_command(rest):
        decide("allow", "amoniac review debate: a command of the debate script")
    if HC_WAIT.fullmatch(command):
        decide("allow", "amoniac review debate: wait for the reviewer")
    if HC_READ.fullmatch(command):
        decide("allow", "amoniac review debate: read the reviewer screen")
    sys.exit(0)


if __name__ == "__main__":
    main()
