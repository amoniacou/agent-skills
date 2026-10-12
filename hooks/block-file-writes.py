#!/usr/bin/env python3
import json
import os
import re
import sys

RULE = (
    "Project files are edited only through Edit or Write: the user reviews the diff before it "
    "lands, while a shell edit slips past unseen and leaves the harness with a stale view of the "
    "file. One Edit per hunk (or replace_all). A mechanical rewrite of Go expressions goes through "
    "gofmt -r, which this hook allows. If a change is otherwise mechanical across hundreds of "
    "sites, say so and ask the user. Write temporary files to the scratchpad (/tmp/)."
)

SAFE_REDIRECT = re.compile(r"(?:\d*>&\d+|&>>?\s*/dev/null|\d*>>?\s*/dev/(?:null|stdout|stderr)\b)")

REDIRECT = re.compile(r"(?<![0-9&<>=!\-])>>?(?![=>])\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s\"'|;&<>]+))")

TEE = re.compile(r"(?:^|[|&;(\s])tee(?:\s+-\S+)*\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s\"'|;&<>]+))")

INPLACE = [
    (re.compile(r"(?:^|[|&;(\s])sed(?:\s+-\S*)*\s+-[a-zA-Z]*i"), "sed -i"),
    (re.compile(r"(?:^|[|&;(\s])sed(?:\s|[^|&;]*\s)--in-place"), "sed --in-place"),
    (re.compile(r"(?:^|[|&;(\s])perl(?:\s+-\S*)*\s*-[a-zA-Z]*i"), "perl -i"),
    (re.compile(r"(?:^|[|&;(\s])awk[^|;&]*-i\s+inplace"), "awk -i inplace"),
    (re.compile(r"(?:^|[|&;(\s])dd\s+[^|;]*of="), "dd of="),
    (re.compile(r"(?:^|[|&;(\s])truncate\s+-s"), "truncate -s"),
    (re.compile(r"(?:^|[|&;(\s])patch\s+-[a-zA-Z]*p"), "patch -p"),
    (re.compile(r"(?:^|[|&;(\s])(?:ex|ed)\s+-s"), "ex/ed -s"),
    (re.compile(r"(?:^|[|&;(\s])shred\b"), "shred"),
    (re.compile(r"(?:^|[|&;(\s])sponge\b"), "sponge"),
    (re.compile(r"(?:^|[|&;(\s])(?:yq|jq|crudini)(?:\s+-\S*)*\s+(?:-i\b|--in-?place\b)"), "yq/jq -i"),
]

FILE_OPS = re.compile(
    r"(?:^|&&|\|\||[;|(\n])\s*(?:sudo(?:\s+-\S+)*\s+|xargs\b[^|;&\n]*?\s)?"
    r"(mv|cp|rm|rmdir|mkdir|touch|ln|install|rsync|unlink)(?:\s|$)"
)

INTERPRETER = re.compile(r"(?:^|[|&;(\s])(?:python3?|ruby|node|php)(?:\s|$)")
INTERPRETER_INPUT = re.compile(r"<<|\s-c(?:\s|$)|\s-e(?:\s|$)")
INTERPRETER_WRITE = re.compile(
    r"open\([^)]*['\"][wa]|\.write|writeFileSync|appendFileSync|createWriteStream|"
    r"File\.(?:write|open)|write_text|write_bytes|Pathlib|shutil\.(?:copy|move)"
)

FETCH_OUT = [
    (re.compile(r"(?:^|[|&;(\s])curl\b"), re.compile(r"\s(?:-o|--output)\s+(\S+)")),
    (re.compile(r"(?:^|[|&;(\s])wget\b"), re.compile(r"\s(?:-O|--output-document)\s+(\S+)")),
]

ALLOWED_PREFIXES = ("/dev/", "/tmp/", "/var/tmp/", "/proc/")


def deny(reason):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def target_allowed(raw, root):
    target = raw.strip().strip("\"'")
    if not target or target.startswith("$"):
        return True
    if "$XDG_RUNTIME_DIR" in target or re.search(r"claude-[^/]*/.*scratchpad", target):
        return True
    if target.startswith(ALLOWED_PREFIXES):
        return True
    if target.startswith("/"):
        expanded = os.path.expanduser(target)
        return not (root and (expanded == root or expanded.startswith(root.rstrip("/") + "/")))
    return target.startswith(".git/")


def check_command(command, root):
    cleaned = SAFE_REDIRECT.sub(" ", command)

    for pattern, name in INPLACE:
        if pattern.search(cleaned):
            deny("Blocked: %s edits the file in place. %s" % (name, RULE))

    found = FILE_OPS.search(cleaned)
    if found:
        deny("Blocked: %s changes files. Ask the user to run it themselves with ! in the prompt." % found.group(1))

    if INTERPRETER.search(cleaned) and INTERPRETER_INPUT.search(cleaned) and INTERPRETER_WRITE.search(cleaned):
        deny("Blocked: a one-liner or heredoc that writes a file. %s" % RULE)

    for launcher, out in FETCH_OUT:
        if launcher.search(cleaned):
            found = out.search(cleaned)
            if found and not target_allowed(found.group(1), root):
                deny("Blocked: a download into the file %s. %s" % (found.group(1), RULE))

    for pattern, kind in ((REDIRECT, "a redirect"), (TEE, "tee")):
        for match in pattern.finditer(cleaned):
            target = next(g for g in match.groups() if g is not None)
            if not target_allowed(target, root):
                deny("Blocked: %s into the file %s. %s" % (kind, target, RULE))


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        sys.exit(0)

    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ""
    check_command(command, root)
    sys.exit(0)


if __name__ == "__main__":
    main()
