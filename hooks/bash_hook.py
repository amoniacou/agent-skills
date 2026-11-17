import json
import os
import re
import shlex
import sys
from typing import NoReturn

PREFIX_WORDS = {"sudo", "env", "time", "nice", "ionice", "command", "xargs", "then", "else", "do", "!"}

ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")

SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}

SHELL_CODE_FLAG = re.compile(r"-[a-zA-Z]*c[a-zA-Z]*")

TARGET_BEFORE = re.compile(r"(?:>>?|(?:^|[|&;(\s])tee(?:\s+-\S+)*)\s*$")

SHELL_VALUE_OPTIONS = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}

SHELL_CODE_BEFORE = re.compile(
    r"(?:^|[|&;(\s])(?:\S*/)?(?:ba|z|da|k)?sh"
    r"(?:\s+(?:[-+][oO]\s+\S+|--(?:rcfile|init-file)\s+\S+|[-+][a-zA-Z]+|--[a-zA-Z][\w-]*))*"
    r"\s+-[a-zA-Z]*c[a-zA-Z]*\s*$"
)

DOUBLE_QUOTE_ESCAPE = re.compile(r"\\([\"\\$`])")

COMMENT_BEFORE = " \t\n;&|("

HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*(?:'([^'\n]+)'|\"([^\"\n]+)\"|(\\?)([A-Za-z_][A-Za-z0-9_]*))")


def decide(decision: str, reason: str) -> NoReturn:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def deny(reason: str) -> NoReturn:
    decide("deny", reason)


def split_words(stage: str) -> list[str]:
    try:
        return shlex.split(stage)
    except ValueError:
        return stage.split()


def strip_prefix_words(words: list[str]) -> list[str]:
    index = 0
    while index < len(words) and (words[index] in PREFIX_WORDS or ASSIGNMENT.fullmatch(words[index])):
        index += 1
    return words[index:]


def find_shell_code(stage: str) -> str | None:
    words = strip_prefix_words(split_words(stage))
    if not words or os.path.basename(words[0]) not in SHELLS:
        return None
    index = 1
    while index < len(words):
        word = words[index]
        if SHELL_CODE_FLAG.fullmatch(word):
            return words[index + 1] if index + 1 < len(words) else None
        if word in SHELL_VALUE_OPTIONS:
            index += 2
            continue
        if not word.startswith(("-", "+")):
            return None
        index += 1
    return None


def strip_comments(command: str) -> str:
    kept = []
    quote = None
    substitutions = []
    index = 0
    while index < len(command):
        char = command[index]
        if quote != "'" and char == "\\":
            kept.append(command[index : index + 2])
            index += 2
            continue
        if quote != "'" and command[index : index + 2] == "$(":
            substitutions.append([quote, 0])
            quote = None
            kept.append("$(")
            index += 2
            continue
        if quote:
            if char == quote:
                quote = None
        elif char == "(" and substitutions:
            substitutions[-1][1] += 1
        elif char == ")" and substitutions:
            if substitutions[-1][1]:
                substitutions[-1][1] -= 1
            else:
                quote = substitutions.pop()[0]
        elif char in "'\"":
            quote = char
        elif char == "#" and (index == 0 or command[index - 1] in COMMENT_BEFORE):
            end = command.find("\n", index)
            index = len(command) if end < 0 else end
            continue
        kept.append(char)
        index += 1
    return "".join(kept)


def find_substitutions(text: str) -> list[str]:
    found = []
    index = 0
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text.startswith("$(", index):
            end = find_substitution_end(text, index + 2)
        elif text[index] == "`":
            end = text.find("`", index + 1)
            end = len(text) if end < 0 else end + 1
        else:
            index += 1
            continue
        found.append(text[index:end])
        index = end
    return found


def strip_heredoc_bodies(command: str) -> str:
    lines = command.split("\n")
    kept = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        index += 1
        for match in HEREDOC.finditer(line):
            tabs, single, double, backslash, word = match.groups()
            delimiter = single or double or word
            end = index
            while end < len(lines) and (lines[end].lstrip("\t") if tabs else lines[end]) != delimiter:
                end += 1
            if end == len(lines):
                return "\n".join(kept + lines[index:])
            if not (single or double or backslash):
                kept.extend(find_substitutions("\n".join(lines[index:end])))
            index = end + 1
    return "\n".join(kept)


def split_raw_commands(command: str) -> list[list[str]]:
    command = strip_comments(strip_heredoc_bodies(command))
    levels = [[[""]]]
    finished = []
    quote = None
    resume = []
    index = 0

    def add_text(text):
        levels[-1][-1][-1] += text

    def open_substitution(closer):
        resume.append([quote, closer, 0])
        levels.append([[""]])

    while index < len(command):
        char = command[index]
        pair = command[index : index + 2]
        if quote == "'":
            if char == "'":
                quote = None
            add_text(char)
        elif quote == '"' and char == "\\":
            add_text(pair)
            index += 2
            continue
        elif pair == "$(" and quote in (None, '"'):
            open_substitution(")")
            quote = None
            index += 2
            continue
        elif char == "`" and quote == '"':
            open_substitution("`")
            quote = None
        elif quote == '"':
            if char == '"':
                quote = None
            add_text(char)
        elif char == "(" and resume and resume[-1][1] == ")":
            resume[-1][2] += 1
            levels[-1].append([""])
        elif char == ")" and resume and resume[-1][1] == ")" and resume[-1][2]:
            resume[-1][2] -= 1
            levels[-1].append([""])
        elif resume and char == resume[-1][1]:
            quote = resume.pop()[0]
            finished.extend(levels.pop())
        elif char == "`":
            open_substitution("`")
        elif char == "\\":
            add_text(pair)
            index += 2
            continue
        elif char in "'\"":
            quote = char
            add_text(char)
        elif pair in ("&&", "||"):
            levels[-1].append([""])
            index += 2
            continue
        elif char in ";\n()":
            levels[-1].append([""])
        elif char == "|":
            levels[-1][-1].append("")
        else:
            add_text(char)
        index += 1
    for level in levels:
        finished.extend(level)
    return [stages for stages in finished if any(stage.strip() for stage in stages)]


def split_commands(command: str) -> list[list[str]]:
    commands = split_raw_commands(command)
    for stages in list(commands):
        for stage in stages:
            code = find_shell_code(stage)
            if code:
                commands.extend(split_commands(code))
    return commands


def find_substitution_end(command: str, index: int) -> int:
    depth = 0
    while index < len(command):
        char = command[index]
        if char == "\\":
            index += 2
            continue
        if char in "'\"":
            index = find_quoted_end(command, index)
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            if not depth:
                return index + 1
            depth -= 1
        index += 1
    return len(command)


def find_quoted_end(command: str, start: int) -> int:
    if command[start] == "'":
        end = command.find("'", start + 1)
        return len(command) if end < 0 else end + 1
    index = start + 1
    while index < len(command):
        char = command[index]
        if char == "\\":
            index += 2
        elif char == '"':
            return index + 1
        elif command[index : index + 2] == "$(":
            index = find_substitution_end(command, index + 2)
        else:
            index += 1
    return len(command)


def find_quoted(command: str) -> list[tuple[int, int]]:
    spans = []
    index = 0
    while index < len(command):
        char = command[index]
        if char == "\\":
            index += 2
        elif char in "'\"":
            end = find_quoted_end(command, index)
            spans.append((index, end))
            index = end
        else:
            index += 1
    return spans


def mask_quoted_text(command: str) -> str:
    command = strip_comments(strip_heredoc_bodies(command))

    def replace(start: int, end: int) -> str:
        text = command[start:end]
        before = command[:start]
        if SHELL_CODE_BEFORE.search(before):
            code = text[1:-1]
            if text.startswith('"'):
                code = DOUBLE_QUOTE_ESCAPE.sub(r"\1", code)
            return " ; " + mask_quoted_text(code) + " ; "
        if TARGET_BEFORE.search(before):
            return text
        if text.startswith('"') and ("$(" in text or "`" in text):
            return text
        return "''"

    masked = []
    last = 0
    for start, end in find_quoted(command):
        masked.append(command[last:start] + replace(start, end))
        last = end
    return "".join(masked) + command[last:]
