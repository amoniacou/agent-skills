#!/usr/bin/env python3
import fnmatch
import json
import os
import re
import sys

from bash_hook import split_words

CONFIG = os.path.join(".agents", "required-skills.json")
MARKERS = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "claude-skills")
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_NAME = "amoniac"
USER_SKILL_DIRS = (".claude/skills", ".agents/skills", ".codex/skills")
METACHARACTERS = re.compile(r"[;&|<>$`\n\r]")
READERS = {"cat", "head", "nl"}
SKILL_FILE = re.compile(r".*/skills/([^/]+)/SKILL\.md")


def session_dir(payload):
    return os.path.join(MARKERS, payload.get("session_id") or "unknown")


def mark(payload, skill):
    skill = skill.lstrip("/")
    if not skill:
        return
    directory = session_dir(payload)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, skill), "w"):
        pass


def load_config(root):
    try:
        with open(os.path.join(root, CONFIG), encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, ValueError):
        return [], {}
    if not isinstance(loaded, dict):
        return [], {}
    return list(loaded.get("always") or []), dict(loaded.get("files") or {})


def unique(skills):
    result = []
    result.extend(skill for skill in skills if skill not in result)
    return result


def required_for_file(root, path):
    relative = os.path.relpath(path, root)
    if relative.startswith(".."):
        return []
    skills = []
    for pattern, names in load_config(root)[1].items():
        if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(os.path.basename(relative), pattern):
            skills.extend(names)
    return skills


def announce(root):
    always, files = load_config(root)
    lines = []
    if always:
        lines.append(
            f"This project requires these skills ({CONFIG}): " + ", ".join(unique(always))
            + ". Every tool except Skill is blocked until each one is loaded."
            " Load them with the Skill tool now, as the first thing you do."
            " Without a Skill tool, read each SKILL.md with cat, one command for each file: "
            + "; ".join(describe_skill_file(skill) for skill in unique(always))
            + "."
        )
    for pattern, names in files.items():
        lines.append(f"Before a Write or Edit of {pattern} files, load: " + ", ".join(unique(names)) + ".")
    if not lines:
        return
    json.dump(
        {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(lines)}},
        sys.stdout,
    )


def find_skill_file(skill: str) -> str | None:
    prefix, _, name = skill.rpartition(":")
    if prefix == PLUGIN_NAME:
        candidates = [os.path.join(PLUGIN_ROOT, "skills", name, "SKILL.md")]
    else:
        home = os.path.expanduser("~")
        candidates = [os.path.join(home, directory, name, "SKILL.md") for directory in USER_SKILL_DIRS]
    return next((path for path in candidates if os.path.isfile(path)), None)


def find_read_skill_files(command: str) -> list[str]:
    if METACHARACTERS.search(command):
        return []
    words = split_words(command)
    if not words or words[0] not in READERS | {"sed"}:
        return []
    paths = words[1:]
    if words[0] == "sed":
        if paths[:1] != ["-n"] or len(paths) < 2:
            return []
        paths = paths[2:]
    elif paths[:1] == ["-ba"]:
        paths = paths[1:]
    if not paths or not all(SKILL_FILE.fullmatch(path) for path in paths):
        return []
    return [os.path.realpath(os.path.expanduser(path)) for path in paths]


def describe_skill_file(skill: str) -> str:
    path = find_skill_file(skill)
    return f"{skill}: {path}" if path else f"{skill}: no SKILL.md found, ask the user"


def deny(tool, skills):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Blocked: {tool} needs these skills loaded first: "
                    + ", ".join(skills)
                    + ". Load each one with the Skill tool, then run this call again."
                    + " Without a Skill tool, read each SKILL.md with cat, one command for each file: "
                    + "; ".join(describe_skill_file(skill) for skill in skills)
                    + "."
                ),
            }
        },
        sys.stdout,
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    event = payload.get("hook_event_name", "")
    tool = payload.get("tool_name", "")
    data = payload.get("tool_input") or {}

    if event == "SessionStart":
        announce(payload.get("cwd") or os.getcwd())
        return 0
    if event == "UserPromptExpansion" and payload.get("expansion_type") == "slash_command":
        mark(payload, payload.get("command_name", ""))
        return 0
    if event == "PostToolUse" and tool == "Skill":
        mark(payload, data.get("skill", ""))
        return 0
    if event != "PreToolUse" or tool == "Skill":
        return 0

    root = payload.get("cwd") or os.getcwd()
    directory = session_dir(payload)
    skills = load_config(root)[0]
    if tool in ("Write", "Edit") and data.get("file_path"):
        skills = skills + required_for_file(root, data["file_path"])
    missing = [skill for skill in unique(skills) if not os.path.exists(os.path.join(directory, skill))]
    if missing and tool == "Bash":
        read = find_read_skill_files(data.get("command") or "")
        if read:
            for skill in missing:
                path = find_skill_file(skill)
                if path and os.path.realpath(path) in read:
                    mark(payload, skill)
            return 0
    if missing:
        deny(tool, missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
