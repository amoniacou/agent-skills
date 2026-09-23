#!/usr/bin/env python3
import json
import re
import shlex
import sys

READ_ONLY = {
    "status",
    "log",
    "diff",
    "show",
    "blame",
    "annotate",
    "shortlog",
    "whatchanged",
    "reflog",
    "describe",
    "rev-parse",
    "rev-list",
    "name-rev",
    "merge-base",
    "cat-file",
    "ls-files",
    "ls-tree",
    "ls-remote",
    "diff-tree",
    "diff-index",
    "diff-files",
    "for-each-ref",
    "show-ref",
    "show-branch",
    "check-ignore",
    "check-attr",
    "count-objects",
    "verify-commit",
    "verify-tag",
    "grep",
    "help",
    "version",
    "var",
    "cherry",
    "range-diff",
    "format-patch",
    "bundle",
    "archive",
}

VALUE_FLAGS = {
    "--contains",
    "--no-contains",
    "--merged",
    "--no-merged",
    "--points-at",
    "--sort",
    "--format",
    "--color",
    "-n",
}

LIST_SAFE_FLAGS = {
    "branch": {
        "-a",
        "--all",
        "-r",
        "--remotes",
        "-v",
        "-vv",
        "--verbose",
        "-l",
        "--list",
        "--show-current",
        "--color",
        "--no-color",
        "-i",
        "--ignore-case",
        "--omit-empty",
    },
    "tag": {
        "-l",
        "--list",
        "-n",
        "--color",
        "--no-color",
        "-i",
        "--ignore-case",
        "--omit-empty",
    },
}

SUBCOMMAND_ALLOW = {
    "remote": {"", "show", "get-url", "-v", "--verbose"},
    "stash": {"list", "show"},
    "worktree": {"list"},
    "notes": {"list", "show"},
    "submodule": {"status", "summary"},
    "bisect": {"log", "view"},
    "sparse-checkout": {"list"},
    "maintenance": {},
}

CONFIG_READ_FLAGS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l"}

LIST_LIKE = set(LIST_SAFE_FLAGS)

MUTATING = {
    "commit",
    "push",
    "pull",
    "fetch",
    "clone",
    "init",
    "add",
    "rm",
    "mv",
    "reset",
    "checkout",
    "restore",
    "switch",
    "clean",
    "rebase",
    "merge",
    "cherry-pick",
    "revert",
    "am",
    "apply",
    "gc",
    "prune",
    "repack",
    "filter-branch",
    "update-ref",
    "update-index",
    "symbolic-ref",
    "replace",
    "rerere",
    "mktag",
    "commit-tree",
    "hash-object",
    "write-tree",
    "read-tree",
    "checkout-index",
    "fast-import",
    "gitk",
}

GIT_PREFIX_WORDS = {"sudo", "env", "time", "nice", "ionice", "command", "xargs", "then", "else", "do", "!"}

GLOBAL_VALUE_OPTS = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}

SEGMENT_SPLIT = re.compile(r"\|\||&&|\||;|\n|\$\(|`|\(|\)")


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


def tokenize(segment):
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def strip_prefix(tokens):
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in GIT_PREFIX_WORDS or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", t):
            i += 1
        else:
            break
    return tokens[i:]


def strip_global_opts(tokens):
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in GLOBAL_VALUE_OPTS:
            i += 2
        elif t.startswith("-"):
            i += 1
        else:
            break
    return tokens[i:]


def list_like_is_safe(sub, args):
    safe = LIST_SAFE_FLAGS[sub]
    i = 0
    while i < len(args):
        t = args[i]
        if t in VALUE_FLAGS:
            i += 2
            continue
        if t.startswith("--") and "=" in t and t.split("=", 1)[0] in (VALUE_FLAGS | safe):
            i += 1
            continue
        if t in safe:
            i += 1
            continue
        return False
    return True


def check_git(args):
    args = strip_global_opts(args)
    if not args:
        return None
    sub = args[0]
    rest = args[1:]

    if sub in READ_ONLY:
        return None

    if sub == "config":
        if any(f in rest or any(r.startswith(f + "=") for r in rest) for f in CONFIG_READ_FLAGS):
            return None
        return "git config змінює конфігурацію"

    if sub in LIST_LIKE:
        if list_like_is_safe(sub, rest):
            return None
        return "git %s у цій формі створює, перейменовує або видаляє ref" % sub

    if sub in SUBCOMMAND_ALLOW:
        nested = rest[0] if rest else ""
        if nested in SUBCOMMAND_ALLOW[sub]:
            return None
        return "git %s %s змінює стан репозиторію" % (sub, nested)

    return "git %s змінює стан репозиторію, індексу або віддаленого сховища" % sub


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command") or ""
    if "git" not in command:
        sys.exit(0)

    for segment in SEGMENT_SPLIT.split(command):
        tokens = strip_prefix(tokenize(segment))
        if not tokens:
            continue
        head = tokens[0]
        if head == "git" or head.endswith("/git"):
            reason = check_git(tokens[1:])
            if reason:
                deny(
                    "Заблоковано: %s. Дозволені лише read-only git-команди "
                    "(status, log, diff, show, blame, rev-parse тощо). "
                    "Попроси користувача виконати це самостійно через ! у промпті." % reason
                )

    for match in re.finditer(r"\bgit\s+(?:-\S+\s+)*([a-z][a-z-]*)", command):
        sub = match.group(1)
        if sub not in MUTATING:
            continue
        deny(
            "Заблоковано: git %s змінює стан репозиторію. Дозволені лише read-only "
            "git-команди (status, log, diff, show, blame, rev-parse тощо). "
            "Попроси користувача виконати це самостійно через ! у промпті." % sub
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
