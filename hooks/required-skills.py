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


def required(root, path):
    relative = os.path.relpath(path, root)
    if relative.startswith(".."):
        return []
    try:
        with open(os.path.join(root, CONFIG), encoding="utf-8") as handle:
            rules = json.load(handle)
    except (OSError, ValueError):
        return []
    skills = []
    for pattern, names in rules.items():
        if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(os.path.basename(relative), pattern):
            skills.extend(name for name in names if name not in skills)
    return skills


def deny(path, skills):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Blocked: {os.path.basename(path)} needs these skills loaded first: "
                    + ", ".join(skills)
                    + ". Load each one with the Skill tool, then make this edit again."
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

    if event == "UserPromptExpansion" and payload.get("expansion_type") == "slash_command":
        mark(payload, payload.get("command_name", ""))
        return 0
    if event == "PostToolUse" and tool == "Skill":
        mark(payload, data.get("skill", ""))
        return 0
    if event != "PreToolUse" or tool not in ("Write", "Edit"):
        return 0

    path = data.get("file_path", "")
    if not path:
        return 0
    root = payload.get("cwd") or os.getcwd()
    directory = session_dir(payload)
    missing = [skill for skill in required(root, path) if not os.path.exists(os.path.join(directory, skill))]
    if missing:
        deny(path, missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
