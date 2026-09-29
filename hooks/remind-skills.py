#!/usr/bin/env python3
import json
import os
import re
import sys

CODE_SUFFIXES = (
    ".rb", ".rake", ".py", ".go", ".rs", ".ts", ".tsx", ".js", ".jsx", ".mjs",
    ".java", ".kt", ".swift", ".cs", ".php", ".ex", ".exs", ".scala",
    ".c", ".cc", ".cpp", ".h", ".hpp",
)

DEFINITION = re.compile(
    r"^\s*(export\s+)?(default\s+)?(pub(\([^)]*\))?\s+)?(abstract\s+|async\s+)?"
    r"(class|module|def|func|fn|function|struct|enum|trait|interface|type)\s+\S"
)

ABSTRACTION = re.compile(
    r"(\bclass\s+Base\w*|<\s*Base\w*|\babstract\s+class\b|\binterface\b|\btrait\s+\w"
    r"|\bNotImplemented(Error)?\b|\b\w+(Factory|Strategy|Registry|Provider|Adapter)\b)"
)

TEST_FILE = re.compile(r"(_test\.(go|py|rb|exs?)|_spec\.rb|(^|/)test_\w+\.py|\.(test|spec)\.[cm]?[jt]sx?)$")

TEST_CASE = re.compile(
    r"^\s*(func\s+(\([^)]*\)\s*)?Test\w*|def\s+test_\w*|(It|Describe|Context|When)\s*\("
    r"|(it|describe|context|test|specify)\s*[(\s]['\"])"
)

TEST_DOUBLE = re.compile(
    r"(\bsleep\b|time\.Sleep|\ballow\(|\bdouble\(|instance_double|\bstub|\bmock|\bMock|httpmock|gomock|sqlmock|\bSkip\()"
)

NAMING = "agent-skills:naming"
PRINCIPLES = "agent-skills:principles"
TESTING = "agent-skills:testing"


def matching(pattern, text):
    return {line.strip() for line in text.splitlines() if pattern.search(line)}


def added(pattern, new, old):
    return sorted(matching(pattern, new) - matching(pattern, old))


def current(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def reminder(skill, reason, lines):
    preview = "\n".join(f"  {line[:120]}" for line in lines[:5])
    return (
        f"{reason}:\n{preview}\n"
        f"If the {skill} skill is not loaded in this session yet, load it with the Skill tool "
        "and check these lines against it. Fix them in the next edit if they break its rules."
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool = payload.get("tool_name", "")
    data = payload.get("tool_input", {}) or {}
    path = data.get("file_path", "")

    if tool == "Write":
        new, old = data.get("content", ""), current(path)
    elif tool == "Edit":
        new, old = data.get("new_string", ""), data.get("old_string", "")
    else:
        return 0

    notes = []
    new_file = tool == "Write" and path and not path.startswith("/tmp/") and not os.path.exists(path)
    if new_file:
        notes.append(reminder(NAMING, "This change creates a new file", [path]))

    if TEST_FILE.search(path):
        tests = added(TEST_CASE, new, old) + added(TEST_DOUBLE, new, old)
        if new_file or tests:
            notes.append(reminder(TESTING, "This change writes tests", tests or [path]))

    if not path.lower().endswith(CODE_SUFFIXES):
        new = old = ""

    names = added(DEFINITION, new, old)
    if names:
        notes.append(reminder(NAMING, "This change adds new names", names))
    abstractions = added(ABSTRACTION, new, old)
    if abstractions:
        notes.append(reminder(PRINCIPLES, "This change adds abstractions", abstractions))

    if not notes:
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "\n\n".join(notes),
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
