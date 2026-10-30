#!/usr/bin/env python3
"""Format, lint, and type-check a file after Claude edits it.

Wired as a PreToolUse and PostToolUse hook on Edit|Write|MultiEdit.
``pre`` records each check's issues before the first edit of the session
(the baseline); ``post`` applies fixers, reruns the checks, and exits 2 with
only the issues the edit introduced, so Claude sees them and fixes them.

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
    """

    key: str
    cmd: list
    cwd: Path
    parse: Callable
    fix_cmd: list | None = None

    def run(self, fix: bool = False) -> list:
        """Run the check under a lock and return its issues."""
        lock = CACHE / "locks" / f"{_digest(self.key)}.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            proc = subprocess.run(
                self.fix_cmd if fix and self.fix_cmd else self.cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
            )
        return self.parse(proc.stdout, proc.stderr, self.cwd)


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


def _git_root(path: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    return Path(proc.stdout.strip()) if proc.returncode == 0 else None


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


parse_tsc = _regex_parser(r"^(.+?)\((\d+),\d+\): error (TS\d+): (.*)$", 1, 2, 3, 4)
parse_mypy = _regex_parser(r"^(.+?):(\d+): error: (?:(.*?)(?:  \[([\w-]+)\])?)$", 1, 2, 4, 3)
parse_pyright = _regex_parser(r"^\s+(.+?):(\d+):\d+ - error: (.*?)(?: \((\w+)\))?$", 1, 2, 4, 3)
parse_ruff = _regex_parser(r"^(.+?):(\d+):\d+: (\S+) (.*)$", 1, 2, 3, 4)
parse_markdownlint = _regex_parser(r"^(.+?):(\d+)(?::\d+)? (MD\d+)\S* (.*)$", 1, 2, 3, 4)


def parse_eslint(stdout: str, stderr: str, cwd: Path) -> list:
    return [
        (r["filePath"], m.get("line", 0), m.get("ruleId") or "", m["message"])
        for r in json.loads(stdout or "[]")
        for m in r["messages"]
    ]


def parse_oxlint(stdout: str, stderr: str, cwd: Path) -> list:
    return [
        (_abs(cwd, d["filename"]), (d.get("labels") or [{}])[0].get("span", {}).get("line", 0), d["code"], d["message"])
        for d in json.loads(stdout or "{}").get("diagnostics", [])
    ]


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
    return [r / "tsconfig.json" if r.is_dir() else r for r in refs if r.exists()]


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
            checks.append(Check(f"tsc:{config}", cmd, config.parent, parse_tsc))
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


def pre(file: Path, session: str, checks: list) -> None:
    for check in checks:
        baseline = _baseline_path(session, check)
        if baseline.exists():
            continue
        is_file_scoped = check.key.endswith(f":{file}")
        issues = check.run() if file.exists() or not is_file_scoped else []
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(json.dumps(issues))


def post(file: Path, root: Path, session: str, formatters: list, checks: list) -> None:
    for cmd in formatters:
        subprocess.run(cmd, capture_output=True)
    new = []
    for check in checks:
        issues = check.run(fix=True)
        baseline_file = _baseline_path(session, check)
        if baseline_file.exists():
            remaining = _counter(json.loads(baseline_file.read_text()))
        else:
            # No baseline (e.g. resumed session after temp cleanup): only trust issues in the edited file.
            remaining = _counter([i for i in issues if i[0] != str(file)])
        for path, line, code, message in issues:
            identity = (path, code, message)
            if remaining[identity]:
                remaining[identity] -= 1
            else:
                new.append((check.key.split(":", 1)[0], path, line, code, message))
    if not new:
        return
    new.sort(key=lambda n: (n[1] != str(file), n[1], n[2]))
    lines = [
        f"{tool}: {Path(path).relative_to(root) if path.startswith(f'{root}/') else path}:{line} {code} {message}".rstrip()
        for tool, path, line, code, message in new
    ]
    extra = f"\n... and {len(lines) - MAX_LINES} more" if len(lines) > MAX_LINES else ""
    print(
        f"Edit to {file.name} introduced {len(new)} new issue(s) (paths relative to {root}):\n"
        + "\n".join(lines[:MAX_LINES])
        + extra,
        file=sys.stderr,
    )
    sys.exit(2)


def main() -> None:
    payload = json.load(sys.stdin)
    file_path = payload.get("tool_input", {}).get("file_path")
    plan = PLANS.get(Path(file_path).suffix) if file_path else None
    file = Path(file_path).resolve() if plan else None
    root = _git_root(file) if file and file.parent.exists() else None
    if not root:
        return
    formatters, checks = plan(file, _ancestors(file, root))
    if sys.argv[1] == "pre":
        pre(file, payload["session_id"], checks)
    else:
        post(file, root, payload["session_id"], formatters, checks)


if __name__ == "__main__":
    main()
