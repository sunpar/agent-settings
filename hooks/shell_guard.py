"""Check literal shell commands without evaluating submitted text."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import PurePosixPath

PIP_REASON = (
    "Use uv, not pip: uv add <pkg> in a project, uv pip install inside a "
    "uv-managed venv, or uv run --with <pkg> for a one-off."
)
TIMEOUT_REASON = (
    "macOS has no timeout command on this host, so timeout N ... exits 127 "
    "with empty output and silently hides the real result (a remote ssh sweep "
    "can look idle when it is not). Use ssh -o ConnectTimeout=N, or gtimeout N "
    "(brew coreutils), or for a remote Linux host put timeout inside the ssh quotes."
)

WORD_PART = re.compile(
    r"""[^ \t\n"'\\;&|()<>]+|'[^']*'|"(?:\\[\s\S]|[^"\\])*"|\\[\s\S]"""
)
TOKEN = re.compile(
    r"(?P<ignore>[ \t]+|\\\n|#[^\n]*)"
    r"|(?P<redirect>[0-9]*(?:<<<|<<-|<<|<>|<&|>>|>&|>\||[<>])|&>>?)"
    r"|(?P<separator>[;&|()\n])"
    rf"|(?P<word>(?:{WORD_PART.pattern})+)"
)
CLAUSE_PREFIXES = {"!", "{", "if", "then", "elif", "else", "do", "while", "until"}
ASSIGNMENT = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*=")
DOUBLE_QUOTE_ESCAPE = re.compile(r'\\([$"`\\\n])')
PYTHON = re.compile(r"python(?:3(?:\.[0-9]+)*)?")


def literal_word(word: str) -> str:
    parts = []
    for part in WORD_PART.findall(word):
        if part.startswith("'"):
            parts.append(part[1:-1])
        elif part.startswith('"'):
            parts.append(
                DOUBLE_QUOTE_ESCAPE.sub(lambda m: m[1].removesuffix("\n"), part[1:-1])
            )
        elif part != "\\\n":
            parts.append(part.removeprefix("\\"))
    return "".join(parts)


def after_heredocs(source: str, start: int, heredocs: list[tuple[str, bool]]) -> int:
    for delimiter, strip_tabs in heredocs:
        while start < len(source):
            end = source.find("\n", start)
            if end == -1:
                return len(source)
            line = source[start:end]
            start = end + 1
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                break
    return start


def shell_commands(source: str) -> Iterator[list[str]]:
    """Find literal clause heads, skipping here-doc bodies and quoted expansions."""
    start = 0
    words: list[str] = []
    heredocs: list[tuple[str, bool]] = []
    redirect = ""
    while match := TOKEN.match(source, start):
        start = match.end()
        token = match[0]
        if match.lastgroup == "separator":
            if words:
                yield words
                words = []
            if token == "\n":
                start = after_heredocs(source, start, heredocs)
                heredocs.clear()
        elif match.lastgroup == "redirect":
            redirect = token.lstrip("0123456789")
        elif match.lastgroup == "word":
            if redirect:
                if redirect in {"<<", "<<-"}:
                    heredocs.append((literal_word(token), redirect == "<<-"))
                redirect = ""
            elif words or (
                token not in CLAUSE_PREFIXES and not ASSIGNMENT.match(token)
            ):
                words.append(literal_word(token))
    if start == len(source) and words:
        yield words


def submitted_commands(command: object) -> Iterator[list[str]]:
    if isinstance(command, str):
        yield from shell_commands(command)
    elif isinstance(command, list) and all(isinstance(arg, str) for arg in command):
        if (
            len(command) >= 3
            and PurePosixPath(command[0]).name in {"bash", "sh", "zsh"}
            and command[1] in {"-c", "-cl", "-lc"}
        ):
            yield from shell_commands(command[2])
        elif command:
            yield command
    else:
        raise ValueError("tool_input.command must be shell text or an array of strings")


def denial_reason(words: list[str]) -> str | None:
    if words[0] == "timeout" and len(words) > 1:
        return TIMEOUT_REASON
    if PYTHON.fullmatch(words[0]) and words[1:2] == ["-m"]:
        words = words[2:]
    if words[:2] in (["pip", "install"], ["pip3", "install"]):
        return PIP_REASON
    return None


def unique_object(fields: list[tuple[str, object]]) -> dict[str, object]:
    payload = dict(fields)
    if len(payload) != len(fields):
        raise ValueError("Duplicate field in hook payload")
    return payload


def main() -> None:
    payload = json.load(sys.stdin, object_pairs_hook=unique_object)
    for words in submitted_commands(payload["tool_input"]["command"]):
        if reason := denial_reason(words):
            output = {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
            print(json.dumps({"hookSpecificOutput": output}))
            return


if __name__ == "__main__":
    main()
