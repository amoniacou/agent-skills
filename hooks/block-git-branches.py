#!/usr/bin/env python3
import json
import re
import shlex
import sys

REF_LISTING = {
    "branch",
    "for-each-ref",
    "show-ref",
    "show-branch",
    "symbolic-ref",
    "ls-remote",
    "name-rev",
    "describe",
}

REV_PARSE_FLAGS = {"--abbrev-ref", "--symbolic-full-name", "--branches", "--remotes", "--all"}

HISTORY = {"log", "show", "diff", "rev-list", "shortlog", "whatchanged", "cherry", "merge-base", "range-diff"}

HISTORY_FLAGS = {"--all", "--branches", "--remotes", "--glob"}

REF_MARKERS = ("origin/", "upstream/", "refs/heads/", "refs/remotes/")

PREFIX_WORDS = {"sudo", "env", "time", "nice", "ionice", "command", "xargs", "then", "else", "do", "!"}

GLOBAL_VALUE_OPTS = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}

SEGMENT_SPLIT = re.compile(r"\|\||&&|\||;|\n|\$\(|`|\(|\)")

REASON = (
    "Blocked: git %s reads branches or refs. Branches are not read in this project: work on the "
    "checked-out tree, and if a branch name is needed for a URL or a config, ask the user."
)


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
        if t in PREFIX_WORDS or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", t):
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


def flag_name(token):
    return token.split("=", 1)[0]


def check_git(args):
    args = strip_global_opts(args)
    if not args:
        return None
    sub = args[0]
    rest = args[1:]

    if sub in REF_LISTING:
        return sub

    if sub == "rev-parse":
        if any(flag_name(t) in REV_PARSE_FLAGS for t in rest):
            return "rev-parse " + " ".join(rest)
        return None

    if sub in HISTORY:
        for t in rest:
            if flag_name(t) in HISTORY_FLAGS:
                return "%s %s" % (sub, t)
            if any(m in t for m in REF_MARKERS):
                return "%s %s" % (sub, t)
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if payload.get("tool_name") not in (None, "Bash"):
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
            hit = check_git(tokens[1:])
            if hit:
                deny(REASON % hit)

    sys.exit(0)


if __name__ == "__main__":
    main()
