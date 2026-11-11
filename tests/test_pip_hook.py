import json
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "hooks" / "hooks.json"
BASH_HOOKS = [
    hook["command"]
    for group in json.loads(HOOKS.read_text())["hooks"]["PreToolUse"]
    if group["matcher"] == "Bash"
    for hook in group["hooks"]
]
PIP_HOOK = next(h for h in BASH_HOOKS if "pip3? install" in h)
TIMEOUT_HOOK = next(h for h in BASH_HOOKS if "timeout[[:space:]]" in h)


def decision(command: str, hook: str = PIP_HOOK) -> str | None:
    out = subprocess.run(
        ["bash", "-c", hook],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


@pytest.mark.parametrize(
    "command",
    [
        "pip install requests",
        "pip3 install -r requirements.txt",
        "python -m pip install requests",
        "python3 -m pip install requests",
        "cd backend && pip install -e .",
        "source .venv/bin/activate; pip install x",
        "cd backend\npip install -e .",
    ],
)
def test_denies_pip_install(command: str) -> None:
    assert decision(command) == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "uv pip install requests",
        "uv add requests",
        "pip list",
        "pip show requests",
        "echo 'pip install requests'",
        'rg "pip install" README.md',
        'git commit -m "Use uv\n\npip install is blocked now"',
    ],
)
def test_allows_other_commands(command: str) -> None:
    assert decision(command) is None


def test_timeout_hook_reads_multi_line_commands() -> None:
    assert decision("cd /tmp\ntimeout 5 ssh host", TIMEOUT_HOOK) == "deny"
    assert decision('git commit -m "Fix\n\ntimeout 5 is gone"', TIMEOUT_HOOK) is None
