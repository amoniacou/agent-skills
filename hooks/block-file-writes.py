#!/usr/bin/env python3
import json
import os
import re
import sys

RULE = (
    "Файли проєкту редагуються тільки через Edit або Write — користувач переглядає диф перед "
    "застосуванням, а через shell правка проходить непоміченою і залишає гарнес зі застарілим "
    "станом файлу. Один Edit на кожен фрагмент (або replace_all). Якщо зміна справді механічна на "
    "сотні місць — скажи про це і спитай користувача. Тимчасові файли пиши у scratchpad (/tmp/)."
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
            deny("Заблоковано: %s редагує файл на місці. %s" % (name, RULE))

    if INTERPRETER.search(cleaned) and INTERPRETER_INPUT.search(cleaned) and INTERPRETER_WRITE.search(cleaned):
        deny("Заблоковано: однорядковий скрипт або heredoc, що пише файл. %s" % RULE)

    for launcher, out in FETCH_OUT:
        if launcher.search(cleaned):
            found = out.search(cleaned)
            if found and not target_allowed(found.group(1), root):
                deny("Заблоковано: завантаження у файл %s. %s" % (found.group(1), RULE))

    for pattern, kind in ((REDIRECT, "перенаправлення"), (TEE, "tee")):
        for match in pattern.finditer(cleaned):
            target = next(g for g in match.groups() if g is not None)
            if not target_allowed(target, root):
                deny("Заблоковано: %s у файл %s. %s" % (kind, target, RULE))


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
