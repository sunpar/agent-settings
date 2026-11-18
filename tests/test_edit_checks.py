import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "edit_checks.py"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (tmp_path / "tmp").mkdir()
    (tmp_path / "home").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "git").symlink_to(shutil.which("git"))
    return repo


def run_hook(
    repo: Path, phase: str, tool_name: str, **tool_input: str
) -> subprocess.CompletedProcess:
    workdir = repo.parent
    event = {
        "cwd": str(repo),
        "session_id": "test-session",
        "hook_event_name": {"pre": "PreToolUse", "post": "PostToolUse"}[phase],
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    if phase == "post":
        event["tool_response"] = (
            "Success. Updated the following files:\n"
            if tool_name == "apply_patch"
            else {}
        )
    return subprocess.run(
        [sys.executable, str(HOOK), phase],
        cwd=workdir,
        env={
            **os.environ,
            "PATH": str(workdir / "bin"),
            "HOME": str(workdir / "home"),
            "TMPDIR": str(workdir / "tmp"),
        },
        input=json.dumps(event),
        text=True,
        capture_output=True,
    )


def executable(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n{source}")
    path.chmod(0o755)


def tsc(repo: Path, source: str) -> None:
    (repo / "tsconfig.json").write_text('{"include":["**/*.ts"]}\n')
    executable(repo / "node_modules/.bin/tsc", source)


def test_codex_checks_all_patch_paths_and_runs_each_project_check_once(
    repo: Path,
) -> None:
    tsc(
        repo,
        """from pathlib import Path
import sys
with Path('checks.log').open('a') as log:
    log.write('tsc\\n')
print('caller.ts(1,7): error TS2322: Existing issue')
if Path('new folder/deeper/added.ts').is_file():
    print('caller.ts(3,7): error TS2322: New issue in caller')
sys.exit(2)
""",
    )
    executable(
        repo / "node_modules/.bin/oxfmt",
        """from pathlib import Path
import sys
file = Path(sys.argv[1])
file.write_text(file.read_text() + '// formatted\\n')
""",
    )
    (repo / "remove.ts").write_text("// remove\n")
    (repo / "move.ts").write_text("// move\n")
    (repo / "update.ts").write_text("// update\n")
    (repo / "fake.ts").write_text("// untouched\n")
    patch = """*** Begin Patch
*** Add File: new folder/deeper/added.ts
+*** Add File: fake.ts
*** Delete File: remove.ts
*** Update File: move.ts
*** Move to: renamed.ts
*** Update File: update.ts
@@
-// update
+// updated
*** End Patch"""

    before = run_hook(repo, "pre", "apply_patch", command=patch)
    assert before.returncode == 0, before.stderr
    added = repo / "new folder/deeper/added.ts"
    added.parent.mkdir(parents=True)
    added.write_text("// added\n")
    (repo / "move.ts").rename(repo / "renamed.ts")
    (repo / "remove.ts").unlink()
    (repo / "update.ts").write_text("// updated\n")
    after = run_hook(repo, "post", "apply_patch", command=patch)

    assert after.returncode == 2, after.stderr
    assert after.stderr.splitlines()[1:] == [
        "tsc: caller.ts:3 TS2322 New issue in caller"
    ]
    assert (repo / "checks.log").read_text() == "tsc\ntsc\n"
    assert added.read_text() == "// added\n// formatted\n"
    assert (repo / "renamed.ts").read_text() == "// move\n// formatted\n"
    assert (repo / "update.ts").read_text() == "// updated\n// formatted\n"
    assert (repo / "fake.ts").read_text() == "// untouched\n"
    assert not (repo / "remove.ts").exists()
    assert not (repo / "move.ts").exists()


def test_claude_first_write_records_project_baseline_before_directory_exists(
    repo: Path,
) -> None:
    tsc(
        repo,
        """from pathlib import Path
import sys
print('caller.ts(1,7): error TS2322: Existing issue')
if Path('new/deeper/first.ts').is_file():
    print('caller.ts(3,7): error TS2322: New issue in caller')
sys.exit(2)
""",
    )
    path = repo / "new/deeper/first.ts"
    before = run_hook(repo, "pre", "Write", file_path=str(path))
    assert before.returncode == 0, before.stderr
    path.parent.mkdir(parents=True)
    path.touch()
    after = run_hook(repo, "post", "Write", file_path=str(path))
    assert after.returncode == 2, after.stderr
    assert after.stderr.splitlines()[1:] == [
        "tsc: caller.ts:3 TS2322 New issue in caller"
    ]


def test_formatter_failure_explains_the_failed_tool_and_config(repo: Path) -> None:
    path = repo / "note.ts"
    path.touch()
    executable(
        repo / "node_modules/.bin/oxfmt",
        "import sys\nprint('Invalid formatter config', file=sys.stderr)\nsys.exit(2)\n",
    )

    result = run_hook(repo, "post", "Edit", file_path=str(path))
    assert result.returncode == 2, result.stderr
    assert "oxfmt" in result.stderr
    assert "Invalid formatter config" in result.stderr


@pytest.mark.parametrize(
    ("tool_output", "exit_code", "detail"),
    [
        (
            "error TS5083: Cannot read file 'missing.json'.",
            1,
            "Cannot read file 'missing.json'",
        ),
        (
            "tsconfig.json(1,3): error TS5023: Unknown compiler option",
            1,
            "Unknown compiler option",
        ),
        (
            "caller.ts(1,7): error TS2322: Existing issue\nerror TS5095: Invalid compiler option",
            2,
            "Invalid compiler option",
        ),
        ("Unexpected compiler output", 2, "Unexpected compiler output"),
        ("", 137, "137"),
    ],
)
def test_checker_errors_warn_pre_without_a_baseline_and_fail_post(
    repo: Path, tool_output: str, exit_code: int, detail: str
) -> None:
    tsc(repo, f"import sys\nprint({tool_output!r})\nsys.exit({exit_code})\n")
    path = repo / "note.ts"
    path.touch()

    result = run_hook(repo, "pre", "Edit", file_path=str(path))
    assert result.returncode == 0, result.stderr
    warning = json.loads(result.stdout)["hookSpecificOutput"]
    assert warning["hookEventName"] == "PreToolUse"
    assert "tsc" in warning["additionalContext"]
    assert detail in warning["additionalContext"]
    assert not list((repo.parent / "tmp").rglob("*.json"))
    result = run_hook(repo, "post", "Edit", file_path=str(path))
    assert result.returncode == 2
    assert detail in result.stderr


@pytest.mark.parametrize(
    "output", ["{", "{}", '{"diagnostics":[{"filename":"bad.js","message":42}]}']
)
def test_invalid_json_diagnostics_report_the_checker(repo: Path, output: str) -> None:
    path = repo / "note.js"
    path.touch()
    executable(repo / "node_modules/.bin/oxlint", f"print({output!r})\n")

    result = run_hook(repo, "post", "Edit", file_path=str(path))
    assert result.returncode == 2, result.stderr
    assert "oxlint" in result.stderr
    assert "diagnostics" in result.stderr


def test_oxlint_syntax_diagnostic_can_omit_a_rule_code(repo: Path) -> None:
    (repo / "note.js").touch()
    executable(
        repo / "node_modules/.bin/oxlint",
        """import sys
print('{"diagnostics":[{"filename":"note.js","severity":"error","message":"Unexpected token","labels":[{"span":{"line":3}}]}]}')
sys.exit(1)
""",
    )

    result = run_hook(repo, "post", "Edit", file_path="note.js")
    assert result.returncode == 2, result.stderr
    assert result.stderr.splitlines()[1:] == ["oxlint: note.js:3  Unexpected token"]


@pytest.mark.parametrize(
    "metadata",
    [
        "*** Move to: note.ts",
        "*** Update File: note.ts\n*** Unknown File: fake.ts",
        "*** Update File: note.ts\n*** Delete File: ./note.ts",
    ],
)
def test_invalid_patch_metadata_is_rejected_before_formatting(
    repo: Path, metadata: str
) -> None:
    path = repo / "note.ts"
    path.write_text("// original\n")
    executable(
        repo / "node_modules/.bin/oxfmt",
        "from pathlib import Path\nPath('note.ts').write_text('changed')\n",
    )

    result = run_hook(
        repo,
        "post",
        "apply_patch",
        command=f"*** Begin Patch\n{metadata}\n*** End Patch",
    )
    assert result.returncode == 2, result.stderr
    assert "apply_patch" in result.stderr
    assert path.read_text() == "// original\n"


@pytest.mark.parametrize("config_problem", [True, False])
def test_mypy_config_errors_and_informational_stderr_are_distinct(
    repo: Path, config_problem: bool
) -> None:
    (repo / "mypy.ini").write_text("[mypy]\n")
    (repo / "note.py").touch()
    notice = (
        "mypy.ini: [mypy]: Unrecognized option: bogus = x"
        if config_problem
        else "note: cache is disabled"
    )
    executable(
        repo / ".venv/bin/mypy",
        f"import sys\nprint({notice!r}, file=sys.stderr)\n"
        "print('note.py:3: error: Incorrect type  [assignment]')\nsys.exit(1)\n",
    )

    result = run_hook(repo, "pre", "Edit", file_path="note.py")
    assert result.returncode == 0, result.stderr
    if config_problem:
        assert (
            "Unrecognized option"
            in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        )
        assert not list((repo.parent / "tmp").rglob("*.json"))
    else:
        assert result.stdout == ""
        result = run_hook(repo, "post", "Edit", file_path="note.py")
        assert result.returncode == 0, result.stderr


def test_invalid_solution_config_is_reported_and_shared_reference_is_baselined_once(
    repo: Path,
) -> None:
    tsc(
        repo,
        """import sys
from pathlib import Path
config = Path(sys.argv[sys.argv.index('-p') + 1])
with Path(config.parents[0] / 'checks.log').open('a') as log:
    log.write('tsc\\n')
if config.parent.name == 'repo':
    print('tsconfig.json(1,33): error TS6053: File missing not found.')
    sys.exit(2)
""",
    )
    (repo / "tsconfig.json").write_text(
        '{"files":[],"references":[{"path":"./app"},{"path":"./app/../app"},{"path":"./missing"}]}'
    )
    (repo / "app").mkdir()
    (repo / "app/tsconfig.json").write_text('{"include":["*.ts"]}')
    patch = """*** Begin Patch
*** Add File: root.ts
+export const a = 1;
*** Add File: app/module.ts
+export const b = 2;
*** End Patch"""

    result = run_hook(repo, "pre", "apply_patch", command=patch)
    assert result.returncode == 0, result.stderr
    assert (
        "TS6053: File missing not found"
        in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    )
    assert (repo / "checks.log").read_text() == "tsc\n"
    assert (repo / "app/checks.log").read_text() == "tsc\n"
