#!/usr/bin/env python3
import json
import os
import sys

from bash_hook import deny, split_commands, split_words, strip_prefix_words

REWRITERS = {"sed", "awk", "gawk", "mawk", "perl"}

FILTERS = REWRITERS | {"grep", "egrep", "fgrep", "rg", "head", "tail", "cut", "sort", "uniq", "tr", "wc", "jq", "yq", "column"}

FETCHERS = {"gh", "curl", "wget"}

NPM_FETCHES = {"view", "info", "show"}

RULE = (
    "Save the output to a file in the scratchpad first: add `> <scratchpad>/<name>.log 2>&1` "
    "(for gh, `> <scratchpad>/gh-<what>.json`). Then search the file with the Grep tool or read it with Read."
)


def find_program(stage: str) -> str:
    words = strip_prefix_words(split_words(stage))
    return os.path.basename(words[0]) if words else ""


def fetches_data(stage: str) -> bool:
    words = strip_prefix_words(split_words(stage))
    if not words:
        return False
    program = os.path.basename(words[0])
    if program in FETCHERS:
        return True
    return program == "npm" and len(words) > 1 and words[1] in NPM_FETCHES


def check_command(command: str) -> None:
    for stages in split_commands(command):
        filters = [program for program in map(find_program, stages[1:]) if program in FILTERS]
        if not filters:
            continue
        if fetches_data(stages[0]):
            deny("Blocked: the pipe filters data that %s fetched. Fetch it one time and keep it. %s" % (find_program(stages[0]), RULE))
        rewriters = [program for program in filters if program in REWRITERS]
        if rewriters:
            deny("Blocked: the pipe rewrites command output with %s. %s" % (rewriters[0], RULE))
        if len(filters) >= 2:
            deny("Blocked: the pipe chains %d filters (%s). %s A single filter, such as `| tail -30`, is fine." % (len(filters), ", ".join(filters), RULE))


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command") or ""
    if "|" in command:
        check_command(command)
    sys.exit(0)


if __name__ == "__main__":
    main()
