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


def stop(
    home: Path, cwd: Path, transcript: Path | None, active: bool = False
) -> list[str] | None:
    event = {
        "session_id": "s1",
        "cwd": str(cwd),
        "hook_event_name": "Stop",
        "stop_hook_active": active,
        "transcript_path": str(transcript) if transcript else None,
    }
    out = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        env={**os.environ, "HOME": str(home)},
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if not out:
        return None
    result = json.loads(out)
    assert result["decision"] == "block"
    return result["reason"].splitlines()


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n")
    return path


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


def test_lists_each_new_path_once(home: Path, repo: Path, tmp_path: Path) -> None:
    transcript = touch(tmp_path / "transcript.jsonl")
    for name in ("new.py", "migrations/0001.py", "migrations/0002.py", "ignored.log"):
        touch(repo / name)
    assert stop(home, repo / "migrations", transcript) == [
        f"Untracked files changed during this session in {repo}:",
        "  migrations/",
        "  new.py",
        INSTRUCTION,
    ]
    assert stop(home, repo, transcript) is None
    touch(repo / "later.txt")
    assert stop(home, repo, transcript)[1:-1] == ["  later.txt"]


def test_caps_the_list(home: Path, repo: Path, tmp_path: Path) -> None:
    transcript = touch(tmp_path / "transcript.jsonl")
    for n in range(25):
        touch(repo / f"f{n:02}.txt")
    lines = stop(home, repo, transcript)[1:-1]
    assert lines[0] == "  f00.txt"
    assert lines[19] == "  f19.txt"
    assert lines[20:] == ["  ...and 5 more"]


def test_skips_files_from_before_the_session(
    home: Path, repo: Path, tmp_path: Path
) -> None:
    old = touch(repo / "old.txt")
    os.utime(old, (time.time() - 60, time.time() - 60))
    transcript = touch(tmp_path / "transcript.jsonl")
    assert stop(home, repo, transcript) is None


def test_does_nothing_while_a_stop_hook_is_active(
    home: Path, repo: Path, tmp_path: Path
) -> None:
    transcript = touch(tmp_path / "transcript.jsonl")
    touch(repo / "new.py")
    assert stop(home, repo, transcript, active=True) is None
    assert not (home / ".cache").exists()


def test_does_nothing_outside_git(home: Path, tmp_path: Path) -> None:
    transcript = touch(tmp_path / "transcript.jsonl")
    touch(tmp_path / "plain" / "new.py")
    assert stop(home, tmp_path / "plain", transcript) is None


def test_without_transcript_starts_at_first_stop(home: Path, repo: Path) -> None:
    touch(repo / "first.txt")
    assert stop(home, repo, None) is None
    touch(repo / "second.txt")
    assert stop(home, repo, None)[1:-1] == ["  second.txt"]
