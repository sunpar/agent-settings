import json
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "hooks" / "hooks.json"
PIP_HOOK = next(
    hook["command"]
    for group in json.loads(HOOKS.read_text())["hooks"]["PreToolUse"]
    if group["matcher"] == "Bash"
    for hook in group["hooks"]
    if "pip3? install" in hook["command"]
)


def decision(command: str) -> str | None:
    out = subprocess.run(
        ["bash", "-c", PIP_HOOK],
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
    ],
)
def test_allows_other_commands(command: str) -> None:
    assert decision(command) is None
