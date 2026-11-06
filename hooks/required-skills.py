#!/usr/bin/env python3
import fnmatch
import json
import os
import sys

CONFIG = os.path.join(".agents", "required-skills.json")
MARKERS = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "claude-skills")


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
        )
    for pattern, names in files.items():
        lines.append(f"Before a Write or Edit of {pattern} files, load: " + ", ".join(unique(names)) + ".")
    if not lines:
        return
    json.dump(
        {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(lines)}},
        sys.stdout,
    )


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
    if missing:
        deny(tool, missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
