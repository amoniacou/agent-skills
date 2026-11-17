#!/usr/bin/env python3
import io
import json
import os
import re
import subprocess
import sys
import token
import tokenize

ALLOW = re.compile(
    r"(eslint-disable|prettier-ignore|@ts-|tslint:|noqa|type:\s*ignore|nolint"
    r"|\+kubebuilder:|\+k8s:|\+groupName=|\+optional\b|\+genclient\b"
    r"|//go:|#pragma|SPDX-|shellcheck|ruff:|flake8:|pylint:|biome-ignore"
    r"|#\s*v\d+\.\d+|checkov:|hadolint|yamllint|nosec|codespell"
    r"|^#\s*(syntax|escape|check)\s*=|^#\s*-\*-|^#\s*coding[:=]"
    r"|^#\s*--(\s|$)|^#\s*@(ignored|default|section|raw|skip|extra))",
    re.IGNORECASE,
)

COMMENT = re.compile(r"^\s*(#|//|/\*|\*/|\*\s|<!--)")

HELM_COMMENT_OPEN = re.compile(r"^\{\{-?\s*/\*")
HELM_COMMENT_CLOSE = re.compile(r"\*/\s*-?\}\}")

HELMDOCS_OPEN = re.compile(r"^#\s*(--(\s|$)|@(ignored|default|section|raw|skip|extra))")
HELMDOCS_CONT = re.compile(r"^#")

CONFIG_VALUE = re.compile(r"^//\S*=")

PROSE_SUFFIXES = (".md", ".mdx", ".markdown", ".txt", ".rst", ".adoc")

GODOC = re.compile(r"^//")

GODOC_TARGET = re.compile(
    r"^(package\s+[A-Za-z_]\w*\s*$"
    r"|func\s+\([^)]*\)\s*[A-Z]"
    r"|func\s+[A-Z]"
    r"|(?:type|var|const)\s+[A-Z]"
    r"|(?:type|var|const)\s*\(\s*$"
    r"|[A-Z]\w*(?:\s+[\w\.\*\[\]{}<>-]+)?\s*(?:=|`|$))"
)


PYTHON_STRING_TOKENS = {token.STRING} | {getattr(token, name) for name in ("FSTRING_MIDDLE", "TSTRING_MIDDLE") if hasattr(token, name)}


def find_python_string_rows(text: str) -> set[int]:
    rows = set()
    try:
        for item in tokenize.generate_tokens(io.StringIO(text).readline):
            if item.type in PYTHON_STRING_TOKENS:
                rows.update(range(item.start[0], item.end[0] + 1))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return set()
    return rows


def comment_lines(text, is_go=False, is_python=False):
    found = []
    in_helm_comment = False
    in_helmdocs = False
    doc_block = []
    string_rows = find_python_string_rows(text) if is_python else set()
    for index, line in enumerate(text.splitlines()):
        if index + 1 in string_rows:
            continue
        stripped = line.strip()
        if is_go and doc_block:
            if GODOC.match(stripped):
                doc_block.append(stripped)
                continue
            if not GODOC_TARGET.match(stripped):
                found.extend(doc_block)
            doc_block = []
        if not stripped:
            in_helmdocs = False
            continue
        if in_helmdocs:
            if HELMDOCS_CONT.match(stripped):
                continue
            in_helmdocs = False
        if HELMDOCS_OPEN.match(stripped):
            in_helmdocs = True
            continue
        if in_helm_comment:
            if HELM_COMMENT_CLOSE.search(stripped):
                in_helm_comment = False
            continue
        if HELM_COMMENT_OPEN.match(stripped):
            if not HELM_COMMENT_CLOSE.search(stripped):
                in_helm_comment = True
            continue
        if stripped.startswith("#!"):
            continue
        if not COMMENT.match(line):
            continue
        if CONFIG_VALUE.match(stripped):
            continue
        if ALLOW.search(stripped):
            continue
        if is_go and GODOC.match(stripped):
            doc_block.append(stripped)
            continue
        found.append(stripped)
    found.extend(doc_block)
    return found


def baseline(path, is_go=False, is_python=False):
    known = set()
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            known.update(comment_lines(handle.read(), is_go, is_python))
    except OSError:
        pass
    try:
        directory = os.path.dirname(path) or "."
        head = subprocess.run(
            ["git", "-C", directory, "show", f"HEAD:./{os.path.basename(path)}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if head.returncode == 0:
            known.update(comment_lines(head.stdout, is_go, is_python))
    except (OSError, subprocess.SubprocessError):
        pass
    return known


def applied_text(path, data):
    old = data.get("old_string", "")
    new = data.get("new_string", "")
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return None
    if not old or old not in text:
        return None
    if data.get("replace_all"):
        return text.replace(old, new)
    return text.replace(old, new, 1)


def main():
    if os.environ.get("CLAUDE_ALLOW_COMMENTS") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool = payload.get("tool_name", "")
    data = payload.get("tool_input", {}) or {}
    path = data.get("file_path", "")

    if path.lower().endswith(PROSE_SUFFIXES):
        return 0

    is_go = path.lower().endswith(".go")
    is_python = path.lower().endswith(".py")

    if tool == "Write":
        candidates = comment_lines(data.get("content", ""), is_go, is_python)
        known = baseline(path, is_go, is_python)
    elif tool == "Edit":
        known = baseline(path, is_go, is_python)
        applied = applied_text(path, data)
        if applied is not None:
            candidates = comment_lines(applied, is_go, is_python)
        else:
            candidates = comment_lines(data.get("new_string", ""), is_go, is_python)
            replaced = comment_lines(data.get("old_string", ""), is_go, is_python)
            if len(candidates) <= len(replaced):
                return 0
            known |= set(replaced)
    else:
        return 0

    added = [line for line in candidates if line not in known]

    if not added:
        return 0

    preview = "\n".join(f"  {line[:120]}" for line in added[:8])
    more = f"\n  ... and {len(added) - 8} more" if len(added) > 8 else ""
    sys.stderr.write(
        f"BLOCKED by the global no-comments rule (~/.claude/CLAUDE.md, Code Comments).\n"
        f"{len(added)} comment line(s) would be added to {path}:\n{preview}{more}\n\n"
        "Rewrite the file with no comments and put the explanation in the chat response. "
        "This applies to YAML, workflows, Dockerfiles and shell scripts too, and existing "
        "comments nearby are not permission to add new ones. If the user explicitly asked "
        "for comments in this request, tell them to re-run you with CLAUDE_ALLOW_COMMENTS=1.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
