#!/usr/bin/env python3
import json
import re
import sys

from bash_hook import deny, split_commands, split_words, strip_prefix_words

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

GLOBAL_VALUE_OPTS = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}


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
        return "git config changes the configuration"

    if sub in LIST_LIKE:
        if list_like_is_safe(sub, rest):
            return None
        return "git %s in this form creates, renames or deletes a ref" % sub

    if sub in SUBCOMMAND_ALLOW:
        nested = rest[0] if rest else ""
        if nested in SUBCOMMAND_ALLOW[sub]:
            return None
        return "git %s %s changes the repository" % (sub, nested)

    return "git %s changes the repository, the index or a remote" % sub


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command") or ""
    if "git" not in command:
        sys.exit(0)

    for stages in split_commands(command):
        for stage in stages:
            tokens = strip_prefix_words(split_words(stage))
            if not tokens:
                continue
            head = tokens[0]
            if head == "git" or head.endswith("/git"):
                reason = check_git(tokens[1:])
                if reason:
                    deny(
                        "Blocked: %s. Only read-only git commands are allowed "
                        "(status, log, diff, show, blame, rev-parse and similar). "
                        "Ask the user to run it themselves with ! in the prompt." % reason
                    )

    for match in re.finditer(r"\bgit\s+(?:-\S+\s+)*([a-z][a-z-]*)", command):
        sub = match.group(1)
        if sub not in MUTATING:
            continue
        deny(
            "Blocked: git %s changes the repository. Only read-only git commands "
            "are allowed (status, log, diff, show, blame, rev-parse and similar). "
            "Ask the user to run it themselves with ! in the prompt." % sub
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
