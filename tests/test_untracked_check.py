import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "untracked_check.py"
INSTRUCTION = (
    "For each one: add it to the change if it belongs to the work, delete it if it is a stray"
    " you created (an unrelated lockfile, a scratch script), or tell the user why it stays"
    " untracked. Leave files you did not create alone."
)


def hook(home: Path, event: dict) -> str:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"session_id": "s1", **event}),
        env={**os.environ, "HOME": str(home)},
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def start(home: Path, cwd: Path) -> None:
    assert hook(home, {"hook_event_name": "SessionStart", "cwd": str(cwd)}) == ""


def stop(home: Path, cwd: Path, active: bool = False) -> list[str] | None:
    out = hook(
        home,
        {"hook_event_name": "Stop", "cwd": str(cwd), "stop_hook_active": active},
    )
    if not out:
        return None
    result = json.loads(out)
    assert result["decision"] == "block"
    return result["reason"].splitlines()


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n")
    return path


def age(path: Path) -> None:
    os.utime(path, (time.time() - 60, time.time() - 60))


@pytest.fixture
def home(tmp_path: Path) -> Path:
    (tmp_path / "home").mkdir()
    return tmp_path / "home"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / ".gitignore").write_text("ignored.log\n")
    subprocess.run(["git", "-C", str(path), "add", ".gitignore"], check=True)
    return path


def test_lists_each_new_path_once(home: Path, repo: Path) -> None:
    start(home, repo)
    for name in ("new.py", "migrations/0001.py", "migrations/0002.py", "ignored.log"):
        touch(repo / name)
    assert stop(home, repo / "migrations") == [
        f"Untracked files changed during this session in {repo}:",
        "  migrations/",
        "  new.py",
        INSTRUCTION,
    ]
    assert stop(home, repo) is None
    touch(repo / "later.txt")
    assert stop(home, repo)[1:-1] == ["  later.txt"]


def test_lists_every_path_before_the_active_follow_up(home: Path, repo: Path) -> None:
    start(home, repo)
    for n in range(25):
        touch(repo / f"f{n:02}.txt")
    touch(repo / "ignored.log")
    assert stop(home, repo)[1:-1] == [f"  f{n:02}.txt" for n in range(25)]
    assert stop(home, repo, active=True) is None
    assert stop(home, repo) is None


def test_lists_a_path_once_per_git_root(home: Path, repo: Path) -> None:
    other_repo = repo.parent / "other"
    subprocess.run(["git", "init", "-q", str(other_repo)], check=True)
    start(home, repo)
    touch(repo / "notes.txt")
    touch(other_repo / "notes.txt")
    assert stop(home, repo)[1:-1] == ["  notes.txt"]
    assert stop(home, other_repo)[1:-1] == ["  notes.txt"]
    assert stop(home, repo) is None
    assert stop(home, other_repo) is None


def test_keeps_carriage_return_and_newline_paths_distinct(
    home: Path, repo: Path
) -> None:
    start(home, repo)
    touch(repo / "line\nbreak.txt")
    touch(repo / "line\rbreak.txt")
    assert stop(home, repo)[1:-1] == [
        "  'line\\nbreak.txt'",
        "  'line\\rbreak.txt'",
    ]
    assert stop(home, repo) is None


def test_legacy_history_keeps_the_session_start(home: Path, repo: Path) -> None:
    old = touch(repo / "old.txt")
    age(old)
    state = home / ".cache" / "agent-hooks" / "untracked" / "s1.json"
    state.parent.mkdir(parents=True)
    state.write_text(
        json.dumps({"start": old.stat().st_mtime + 1, "listed": ["same.txt"]})
    )
    touch(repo / "same.txt")
    assert stop(home, repo)[1:-1] == ["  same.txt"]
    assert stop(home, repo) is None


def test_skips_files_from_before_the_session(home: Path, repo: Path) -> None:
    age(touch(repo / "old.txt"))
    start(home, repo)
    assert stop(home, repo) is None


def test_lists_an_edit_inside_an_older_untracked_directory(
    home: Path, repo: Path
) -> None:
    age(touch(repo / "notes" / "kept.txt"))
    age(touch(repo / "notes" / "edited.txt"))
    age(repo / "notes")
    start(home, repo)
    (repo / "notes" / "edited.txt").write_text("changed\n")
    assert stop(home, repo)[1:-1] == ["  notes/"]


def test_does_nothing_while_a_stop_hook_is_active(home: Path, repo: Path) -> None:
    start(home, repo)
    touch(repo / "new.py")
    assert stop(home, repo, active=True) is None
    assert stop(home, repo)[1:-1] == ["  new.py"]


def test_does_nothing_outside_git(home: Path, tmp_path: Path) -> None:
    start(home, tmp_path)
    touch(tmp_path / "plain" / "new.py")
    assert stop(home, tmp_path / "plain") is None


def test_without_session_start_begins_at_first_stop(home: Path, repo: Path) -> None:
    touch(repo / "first.txt")
    assert stop(home, repo) is None
    touch(repo / "second.txt")
    assert stop(home, repo)[1:-1] == ["  second.txt"]
