#!/usr/bin/env python3
"""Format, lint, and type-check edits from Claude Code and Codex.

``pre`` records each check's issues before the first edit of the session
(the baseline); ``post`` applies fixers, reruns the checks, and exits 2 with
issues the edit introduced or errors that prevented the checks from running.

Type checks run per edit, scoped to the whole project where the checker is
incremental (tsc --incremental, mypy's cache), so broken callers in other
files surface immediately. Only tools already installed are used; a missing
tool is skipped.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Callable

CACHE = Path.home() / ".cache" / "claude-edit-checks"
MD_DEFAULT_CONFIG = Path(__file__).with_name("default.markdownlint.jsonc")
MAX_LINES = 40
PRETTIER_CONFIGS = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.js",
    ".prettierrc.cjs",
    ".prettierrc.mjs",
    ".prettierrc.yaml",
    ".prettierrc.yml",
    "prettier.config.js",
    "prettier.config.mjs",
    "prettier.config.cjs",
)


@dataclass
class Check:
    """A diagnostic command plus how to read its output.

    Attributes:
        key (str): Stable identity for baseline storage and locking.
        cmd (list[str]): Command that reports issues without changing files.
        cwd (Path): Working directory, also the base for relative paths in output.
        parse (Callable): Turns (stdout, stderr, cwd) into a list of issues.
        fix_cmd (list[str] | None): Variant that applies fixes and reports what remains.
        project_wide (bool): Whether the check can run without the edited file.
        diagnostic_exits (tuple[int, ...]): Nonzero exits that can carry ordinary diagnostics.
    """

    key: str
    cmd: list
    cwd: Path
    parse: Callable
    fix_cmd: list | None = None
    project_wide: bool = False
    diagnostic_exits: tuple[int, ...] = (1,)

    def run(self, fix: bool = False) -> list:
        """Run the check under a lock and return its issues."""
        lock = CACHE / "locks" / f"{_digest(self.key)}.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            proc = _run_tool(
                self.fix_cmd if fix and self.fix_cmd else self.cmd, self.cwd
            )
        if proc.returncode and proc.returncode not in self.diagnostic_exits:
            raise _tool_error(proc)
        try:
            issues = self.parse(proc.stdout, proc.stderr, self.cwd)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise _tool_error(proc, f"could not collect diagnostics ({exc})") from exc
        if proc.returncode and not issues:
            raise _tool_error(proc, "no recognized diagnostics")
        return issues


def _run_tool(cmd: list, cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(
            f"{Path(cmd[0]).name} could not start in {cwd}: {exc}"
        ) from exc


def _tool_error(
    proc: subprocess.CompletedProcess, reason: str = "command failed"
) -> RuntimeError:
    output = "\n".join(
        line for line in (proc.stderr.strip(), proc.stdout.strip()) if line
    )
    message = f"{Path(proc.args[0]).name}: {reason} (exit {proc.returncode})"
    return RuntimeError(f"{message}\n{output}" if output else message)


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def _ancestors(path: Path, stop: Path) -> list:
    """Return path's parent directories from nearest up to and including stop."""
    dirs = []
    for parent in path.parents:
        dirs.append(parent)
        if parent == stop:
            break
    return dirs


@cache
def _git_root(directory: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return Path(proc.stdout.strip()).resolve() if proc.returncode == 0 else None


def _nearest(dirs: list, *names: str) -> Path | None:
    """Return the first existing dir/name across dirs, nearest first."""
    return next((d / n for d in dirs for n in names if (d / n).exists()), None)


def _abs(cwd: Path, name: str) -> str:
    return str((cwd / name).resolve())


# Output parsers: each returns [(abs_path, line, code, message), ...]


def _regex_parser(pattern: str, path_group: int, line_group: int, code_group: int, msg_group: int) -> Callable:
    regex = re.compile(pattern, re.M)

    def parse(stdout: str, stderr: str, cwd: Path) -> list:
        return [
            (_abs(cwd, m.group(path_group)), int(m.group(line_group)), m.group(code_group) or "", m.group(msg_group))
            for m in regex.finditer(stdout + "\n" + stderr)
        ]

    return parse


_parse_tsc = _regex_parser(r"^(.+?)\((\d+),\d+\): error (TS\d+): (.*)$", 1, 2, 3, 4)
_parse_mypy = _regex_parser(r"^(.+?):(\d+): error: (?:(.*?)(?:  \[([\w-]+)\])?)$", 1, 2, 4, 3)
_parse_pyright = _regex_parser(r"^\s+(.+?):(\d+):\d+ - error: (.*?)(?: \((\w+)\))?$", 1, 2, 4, 3)
parse_ruff = _regex_parser(r"^(.+?):(\d+):\d+: (\S+) (.*)$", 1, 2, 3, 4)
parse_markdownlint = _regex_parser(r"^(.+?):(\d+)(?::\d+)? (MD\d+)\S* (.*)$", 1, 2, 3, 4)


def parse_tsc(stdout: str, stderr: str, cwd: Path) -> list:
    issues = _parse_tsc(stdout, stderr, cwd)
    if re.search(r"^error TS\d+:", f"{stdout}\n{stderr}", re.M) or any(
        Path(path).suffix in {".json", ".jsonc"} for path, *_ in issues
    ):
        raise ValueError("TypeScript project configuration error")
    return issues


def parse_mypy(stdout: str, stderr: str, cwd: Path) -> list:
    if re.search(r"^(?:.*/)?(?:\.?mypy\.ini|pyproject\.toml|setup\.cfg):", stderr, re.M):
        raise ValueError("mypy configuration error")
    return _parse_mypy(stdout, stderr, cwd)


def parse_pyright(stdout: str, stderr: str, cwd: Path) -> list:
    if re.search(r"^(?:Config file |Pyproject file parse attempt |Circular reference in configuration file )", stderr, re.M):
        raise ValueError("Pyright configuration error")
    return _parse_pyright(stdout, stderr, cwd)


def _json_issue(cwd: Path, path: str, line: int, code: str | None, message: str) -> tuple:
    if not isinstance(path, str) or not path or type(line) is not int or line < 0:
        raise ValueError("expected a file path and a nonnegative line number")
    if (code is not None and not isinstance(code, str)) or not isinstance(message, str):
        raise ValueError("expected a string rule code and message")
    return _abs(cwd, path), line, code or "", message


def parse_eslint(stdout: str, stderr: str, cwd: Path) -> list:
    reports = json.loads(stdout)
    if not isinstance(reports, list):
        raise ValueError("expected a list of ESLint reports")
    issues = []
    for report in reports:
        path, messages = report["filePath"], report["messages"]
        if not isinstance(messages, list):
            raise ValueError("expected a list of ESLint messages")
        issues.extend(
            _json_issue(cwd, path, message.get("line", 0), message["ruleId"], message["message"])
            for message in messages
        )
    return issues


def parse_oxlint(stdout: str, stderr: str, cwd: Path) -> list:
    diagnostics = json.loads(stdout)["diagnostics"]
    if not isinstance(diagnostics, list):
        raise ValueError("expected a list of Oxlint diagnostics")
    issues = []
    for diagnostic in diagnostics:
        labels = diagnostic.get("labels", [])
        if not isinstance(labels, list):
            raise ValueError("expected a list of Oxlint labels")
        line = labels[0].get("span", {}).get("line", 0) if labels else 0
        issues.append(_json_issue(cwd, diagnostic["filename"], line, diagnostic.get("code"), diagnostic["message"]))
    return issues


# Per-language plans: (formatter commands, checks)


def _bin(dirs: list, name: str) -> Path | None:
    return _nearest(dirs, f"node_modules/.bin/{name}")


def python_plan(file: Path, dirs: list) -> tuple:
    project = next(
        (d for d in dirs if any((d / n).exists() for n in ("pyproject.toml", "setup.cfg", "mypy.ini"))), dirs[-1]
    )
    venv = _nearest(dirs, ".venv")
    ruff = str(venv / "bin/ruff") if venv and (venv / "bin/ruff").exists() else shutil.which("ruff")
    formatters = [[ruff, "format", "--quiet", str(file)]] if ruff else []
    checks = []
    if ruff:
        base = [ruff, "check", "--output-format", "concise", "--quiet", str(file)]
        checks.append(Check(f"ruff:{file}", base, project, parse_ruff, fix_cmd=[*base, "--fix"]))

    pyproject = project / "pyproject.toml"
    text = pyproject.read_text() if pyproject.exists() else ""
    mypy_section = re.search(r"^\[tool\.mypy\]\s*$(.*?)(?=^\[[^\[\]]+\]\s*$|\Z)", text, re.M | re.S)
    mypy_configured = mypy_section or (project / "mypy.ini").exists()
    mypy = venv / "bin/mypy" if venv else None
    pyright = next(
        (
            p
            for p in (
                venv / "bin/basedpyright" if venv else None,
                venv / "bin/pyright" if venv else None,
                _bin(dirs, "pyright"),
            )
            if p and p.exists()
        ),
        shutil.which("pyright"),
    )
    if mypy_configured and mypy and mypy.exists():
        # With `files` configured, check the whole project so broken callers surface; mypy's cache keeps it fast.
        whole_project = bool(mypy_section and re.search(r"^files\s*=", mypy_section.group(1), re.M))
        target = [] if whole_project else [str(file)]
        key = f"mypy:{project}" if whole_project else f"mypy:{file}"
        checks.append(
            Check(
                key,
                [str(mypy), "--no-color-output", "--no-error-summary", "--show-error-codes", *target],
                project,
                parse_mypy,
                project_wide=whole_project,
            )
        )
    elif pyright and (
        re.search(r"^\[tool\.(based)?pyright\]", text, re.M) or (project / "pyrightconfig.json").exists()
    ):
        # pyright has no incremental CLI mode (7s full run on a 450-file project), so check only the edited file.
        python = [] if not venv else ["--pythonpath", str(venv / "bin/python")]
        checks.append(Check(f"pyright:{file}", [str(pyright), *python, str(file)], project, parse_pyright))
    return formatters, checks


def _tsconfigs(dirs: list) -> list:
    """Return the tsconfig files to check, expanding solution-style configs into their references."""
    config = _nearest(dirs, "tsconfig.json")
    if not config:
        return []
    text = config.read_text()
    if not re.search(r'"files"\s*:\s*\[\s*\]', text):
        return [config]
    refs = [config.parent / p for p in re.findall(r'"path"\s*:\s*"([^"]+)"', text)]
    return [
        config,
        *(r / "tsconfig.json" if r.is_dir() else r for r in refs if r.exists()),
    ]


def typescript_plan(file: Path, dirs: list) -> tuple:
    formatters, checks = [], []
    oxfmt, prettier = _bin(dirs, "oxfmt"), _bin(dirs, "prettier")
    if oxfmt:
        formatters.append([str(oxfmt), str(file)])
    elif prettier and _nearest(dirs, *PRETTIER_CONFIGS):
        formatters.append([str(prettier), "--write", "--log-level", "warn", str(file)])

    eslint, oxlint = _bin(dirs, "eslint"), _bin(dirs, "oxlint")
    eslint_config = _nearest(
        dirs,
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.cjs",
        "eslint.config.ts",
        ".eslintrc",
        ".eslintrc.json",
        ".eslintrc.js",
        ".eslintrc.cjs",
    )
    if eslint and eslint_config:
        base = [str(eslint), "--format", "json", str(file)]
        checks.append(Check(f"eslint:{file}", base, eslint_config.parent, parse_eslint, fix_cmd=[*base, "--fix"]))
    elif oxlint:
        base = [str(oxlint), "--format", "json", str(file)]
        checks.append(Check(f"oxlint:{file}", base, oxlint.parents[2], parse_oxlint, fix_cmd=[*base, "--fix"]))

    if file.suffix in {".ts", ".tsx", ".mts", ".cts"}:
        for config in _tsconfigs(dirs):
            config = config.resolve()
            tsc = _bin(_ancestors(config, dirs[-1]), "tsc")
            if not tsc:
                continue
            buildinfo = CACHE / "tsbuildinfo" / f"{_digest(str(config))}.tsbuildinfo"
            buildinfo.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                str(tsc),
                "--noEmit",
                "--pretty",
                "false",
                "-p",
                str(config),
                "--incremental",
                "--tsBuildInfoFile",
                str(buildinfo),
            ]
            checks.append(
                Check(
                    f"tsc:{config}",
                    cmd,
                    config.parent,
                    parse_tsc,
                    project_wide=True,
                    diagnostic_exits=(1, 2),
                )
            )
    return formatters, checks


def markdown_plan(file: Path, dirs: list) -> tuple:
    formatters, checks = [], []
    prettier = _bin(dirs, "prettier")
    if prettier and _nearest(dirs, *PRETTIER_CONFIGS):
        formatters.append([str(prettier), "--write", "--log-level", "warn", str(file)])
    markdownlint = _bin(dirs, "markdownlint-cli2") or shutil.which("markdownlint-cli2")
    if markdownlint:
        repo_config = _nearest(
            dirs,
            ".markdownlint-cli2.jsonc",
            ".markdownlint-cli2.yaml",
            ".markdownlint.jsonc",
            ".markdownlint.json",
            ".markdownlint.yaml",
            ".markdownlint.yml",
        )
        config = [] if repo_config else ["--config", str(MD_DEFAULT_CONFIG)]
        base = [str(markdownlint), *config, str(file)]
        checks.append(
            Check(
                f"markdownlint:{file}",
                base,
                file.parent,
                parse_markdownlint,
                fix_cmd=[str(markdownlint), "--fix", *config, str(file)],
            )
        )
    return formatters, checks


PLANS = {
    **dict.fromkeys((".py", ".pyi"), python_plan),
    **dict.fromkeys((".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"), typescript_plan),
    **dict.fromkeys((".md", ".mdx"), markdown_plan),
}


def _baseline_path(session: str, check: Check) -> Path:
    return Path(tempfile.gettempdir()) / "claude-edit-checks" / session / f"{_digest(check.key)}.json"


def _counter(issues: list) -> Counter:
    # Line numbers shift as code is edited, so an issue's identity is its file, code, and message.
    return Counter((path, code, message) for path, _, code, message in issues)


def pre(session: str, checks: dict[str, tuple[Check, bool]]) -> list[str]:
    failures = []
    for check, exists in checks.values():
        baseline = _baseline_path(session, check)
        if baseline.exists():
            continue
        try:
            issues = check.run() if exists or check.project_wide else []
        except (OSError, RuntimeError) as exc:
            failures.append(str(exc))
            continue
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(json.dumps(issues))
    return failures


def post(
    files: dict[Path, bool],
    root: Path,
    session: str,
    formatters: list,
    checks: list[Check],
) -> str:
    for cmd in formatters:
        proc = _run_tool(cmd, root)
        if proc.returncode:
            raise _tool_error(proc)
    edited = {str(file) for file in files}
    new = []
    for check in sorted(checks, key=lambda check: check.project_wide):
        issues = check.run(fix=True)
        baseline_file = _baseline_path(session, check)
        if baseline_file.exists():
            remaining = _counter(json.loads(baseline_file.read_text()))
        else:
            # After temp cleanup we can still report issues on the paths edited here.
            remaining = _counter([i for i in issues if i[0] not in edited])
        for path, line, code, message in issues:
            identity = (path, code, message)
            if remaining[identity]:
                remaining[identity] -= 1
            else:
                new.append((check.key.split(":", 1)[0], path, line, code, message))
    if not new:
        return ""
    new.sort(key=lambda n: (n[1] not in edited, n[1], n[2]))
    lines = [
        f"{tool}: {Path(path).relative_to(root) if path.startswith(f'{root}/') else path}:{line} {code} {message}".rstrip()
        for tool, path, line, code, message in new
    ]
    extra = f"\n... and {len(lines) - MAX_LINES} more" if len(lines) > MAX_LINES else ""
    subject = (
        f"Edit to {next(iter(files)).name}"
        if len(files) == 1
        else f"Edit to {len(files)} paths"
    )
    return (
        f"{subject} introduced {len(new)} new issue(s) (paths relative to {root}):\n"
        + "\n".join(lines[:MAX_LINES])
        + extra
    )


def _patch_paths(cwd: Path, command: str) -> dict[Path, bool]:
    """Read patch headers and mark deleted and moved-from paths."""
    if not isinstance(command, str):
        raise ValueError("apply_patch requires patch text in tool_input.command")
    lines = command.strip().split("\n")
    if lines[0] in ("<<EOF", "<<'EOF'", '<<"EOF"') and lines[-1].endswith("EOF"):
        lines = lines[1:-1]
    if (
        len(lines) < 2
        or lines[0].strip() != "*** Begin Patch"
        or lines[-1].strip() != "*** End Patch"
    ):
        raise ValueError("apply_patch requires Begin Patch and End Patch markers")

    paths = {}
    operation = ""
    move_source = None
    for number, raw in enumerate(lines[1:-1], 2):
        line = raw.rstrip() if operation == "Update File" else raw.strip()
        header = re.fullmatch(
            r"\*\*\* (Add File|Update File|Delete File|Move to): (.+)", line
        )
        if header:
            action, name = header.groups()
            path = _event_path(cwd, name)
            if path in paths:
                raise ValueError(f"apply_patch contains a duplicate path: {name}")
            if action == "Move to":
                if move_source is None:
                    raise ValueError(
                        "apply_patch Move to must follow an Update File header"
                    )
                paths[move_source] = True
                move_source = None
            else:
                operation = action
                move_source = path if action == "Update File" else None
            paths[path] = action == "Delete File"
            continue
        if (
            line.startswith("***")
            and line != "*** End of File"
            and not (number == 2 and line.startswith("*** Environment ID: "))
        ):
            raise ValueError(f"apply_patch has invalid metadata on line {number}")
        move_source = None
    return paths


def _event_path(cwd: Path, name: str) -> Path:
    if not isinstance(name, str) or not name.strip() or "\0" in name:
        raise ValueError("expected a nonempty file path")
    return (cwd / name).resolve()


def _read_event(phase: str, payload: dict) -> tuple[str, dict[Path, bool]]:
    if not isinstance(payload, dict):
        raise ValueError("hook input requires an object")
    session = payload["session_id"]
    if not isinstance(session, str) or Path(session).name != session or session in ("", "..") or "\0" in session:
        raise ValueError("hook input requires a valid session_id")
    event_name = "PreToolUse" if phase == "pre" else "PostToolUse"
    if payload.get("hook_event_name", event_name) != event_name:
        raise ValueError(f"expected a {event_name} event")
    process_cwd = Path.cwd()
    cwd = _event_path(process_cwd, payload.get("cwd", str(process_cwd)))
    tool_input = payload["tool_input"]
    if not isinstance(tool_input, dict):
        raise ValueError("hook input requires a tool_input object")
    if payload.get("tool_name") == "apply_patch":
        return session, _patch_paths(cwd, tool_input.get("command"))
    return session, {_event_path(cwd, tool_input.get("file_path")): False}


def _check_edits(phase: str, session: str, paths: dict[Path, bool]) -> list[str]:
    repositories: dict[Path, dict[Path, bool]] = {}
    for file, removed in paths.items():
        if file.suffix in PLANS:
            directory = next(parent for parent in file.parents if parent.is_dir())
            if root := _git_root(directory):
                repositories.setdefault(root, {})[file] = removed

    reports = []
    for root, files in repositories.items():
        formatters = []
        checks = {}
        for file, removed in files.items():
            commands, file_checks = PLANS[file.suffix](file, _ancestors(file, root))
            exists = file.is_file() and (phase == "pre" or not removed)
            if exists:
                formatters.extend(commands)
            for check in file_checks:
                if phase == "pre" or exists or check.project_wide:
                    checks.setdefault(check.key, (check, exists))
        if phase == "pre":
            reports.extend(pre(session, checks))
        elif report := post(
            files, root, session, formatters, [check for check, _ in checks.values()]
        ):
            reports.append(report)
    return reports


def main() -> None:
    try:
        if sys.argv[1:] not in (["pre"], ["post"]):
            raise ValueError("expected a pre or post argument")
        phase = sys.argv[1]
        session, paths = _read_event(phase, json.load(sys.stdin))
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"Edit checks: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        reports = _check_edits(phase, session, paths)
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        reports = [f"Edit checks: {exc}"]
    if reports and phase == "pre":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "Could not collect edit-check baselines.\n" + "\n".join(reports),
        }}))
    elif reports:
        print("\n".join(reports), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
