#!/usr/bin/env python3
import json
import os
import re
import sys

from bash_hook import split_commands, split_words, strip_prefix_words

MODCACHE = "/pkg/mod/"
TEXT_FILTERS = {"grep", "rg", "awk", "sed", "ag", "ack"}
SEARCH_TOOL = re.compile(r"\b(grep|rg|ag|ack)\b")
GO_FILES = re.compile(r"--include=['\"]?\*?\.go\b|\S+\.go\b|(?:-t|--type[= ])\s*go\b|-g\s*['\"]?\*\.go\b")

LSP_HINT = (
    "Or ask the LSP tool (gopls): hover on a symbol for its doc, documentSymbol for the methods of a type, "
    "definition and references to follow it."
)
MODCACHE_REASON = (
    "Blocked: Go library sources are read with go doc, not from the module cache. "
    "Run `go doc <pkg>` to list the API and `go doc <pkg>.<Type>.<Method>` for one symbol. "
    "If go doc says the package is not in the main module, run `go get <module>@<version>` first, then go doc again. "
    + LSP_HINT
)
FILTERED_REASON = (
    "Blocked: do not grep the output of go doc. Ask go doc for the symbol itself: "
    "`go doc <pkg>.<Symbol>` or `go doc <pkg>.<Type>.<Method>`; `go doc <pkg>` lists what the package exports. "
    + LSP_HINT
)
GREP_REMINDER = (
    "This search targets Go files. If you are looking for where a Go symbol is defined or used, "
    "the LSP tool (gopls) is exact: definition, references, documentSymbol. "
    "Keep grep for text: strings, comments, yaml, docs."
)


def runs_go_doc(stage: str) -> bool:
    words = strip_prefix_words(split_words(stage))
    if not words or os.path.basename(words[0]) != "go":
        return False
    words = words[1:]
    if words[:1] == ["-C"]:
        words = words[2:]
    return words[:1] == ["doc"]


def filters_go_doc(command: str) -> bool:
    for stages in split_commands(command):
        for stage, next_stage in zip(stages, stages[1:]):
            words = split_words(next_stage)
            if runs_go_doc(stage) and words and os.path.basename(words[0]) in TEXT_FILTERS:
                return True
    return False


def denial(tool, data):
    if tool == "Bash":
        command = data.get("command", "")
        if MODCACHE in command:
            return MODCACHE_REASON
        if filters_go_doc(command):
            return FILTERED_REASON
    elif tool in ("Read", "Grep"):
        if MODCACHE in (data.get("file_path") or data.get("path") or ""):
            return MODCACHE_REASON
    return ""


def searches_go(tool, data):
    if tool == "Bash":
        command = data.get("command", "")
        return bool(SEARCH_TOOL.search(command) and GO_FILES.search(command))
    if tool == "Grep":
        return data.get("type") == "go" or (data.get("glob") or "").endswith(".go") or (data.get("path") or "").endswith(".go")
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool = payload.get("tool_name", "")
    data = payload.get("tool_input") or {}
    output = {"hookEventName": "PreToolUse"}

    reason = denial(tool, data)
    if reason:
        output["permissionDecision"] = "deny"
        output["permissionDecisionReason"] = reason
    elif searches_go(tool, data):
        output["additionalContext"] = GREP_REMINDER
    else:
        return 0

    json.dump({"hookSpecificOutput": output}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
