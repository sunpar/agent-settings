import json
import shlex
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
(BASH_HOOK,) = (
    hook["command"].replace("{{REPO}}", str(REPO))
    for group in json.loads((REPO / "hooks" / "hooks.json").read_text())["hooks"][
        "PreToolUse"
    ]
    if group["matcher"] == "Bash"
    for hook in group["hooks"]
)


def run_hook(payload: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", BASH_HOOK],
        input=payload,
        capture_output=True,
        text=True,
        check=check,
    )


def decision(command: str | list[str]) -> str | None:
    out = run_hook(json.dumps({"tool_input": {"command": command}})).stdout
    if not out:
        return None
    result = json.loads(out)["hookSpecificOutput"]
    assert result["hookEventName"] == "PreToolUse"
    assert result["permissionDecision"] == "deny"
    return result["permissionDecisionReason"]


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
        "pip\tinstall sample",
        "pip \\\ninstall sample",
        "python3.12\t-m\tpip\tinstall sample",
        '"pip" install sample',
        "if true; then pip install sample; fi",
        "pip 2>/dev/null install sample",
        ["pip3", "install", "sample"],
        ["/bin/bash", "-lc", "cd backend && python3.12 -m pip install sample"],
    ],
)
def test_denies_pip_install(command: str | list[str]) -> None:
    reason = decision(command)
    assert reason is not None
    assert reason.startswith("Use uv, not pip")


@pytest.mark.parametrize(
    "command",
    [
        "uv pip install requests",
        "uv add requests",
        "pip list",
        "pip show requests",
        "pip installed",
        "echo 'pip install requests'",
        'rg "pip install" README.md',
        'git commit -m "Use uv\n\npip install is blocked now"',
        "cat <<'DOC'\npip install sample\ntimeout 5 sample\nDOC",
        "cat <<'FIRST' <<-'SECOND'\npip install sample\nFIRST\n\ttimeout 5 sample\n\tSECOND",
        ": # examples; pip install sample | timeout 5 sample",
        ": \\\n# example; pip install sample",
        "echo then timeout 5 sample",
        'printf "%s" ";" timeout 5 sample',
        'case "$task" in\n timeout) echo wait;;\nesac',
        "ssh sample 'timeout 5 sample'",
        'git commit -m "Fix\n\ntimeout 5 is gone"',
        ["uv", "pip", "install", "sample"],
        ["echo", "documentation; pip install sample", "timeout"],
    ],
)
def test_allows_other_commands(command: str | list[str]) -> None:
    assert decision(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "cd /tmp\ntimeout 5 ssh sample",
        "timeout \\\n5 ssh sample",
        "'timeout' 5 sample",
        "for item in x; do timeout 5 sample; done",
        "cat <<'DOC'\npip install sample\nDOC\ntimeout 5 sample",
        ["timeout", "5", "sample"],
        ["/bin/zsh", "-lc", "printf x | timeout 5 sample"],
    ],
)
def test_denies_timeout(command: str | list[str]) -> None:
    reason = decision(command)
    assert reason is not None
    assert reason.startswith("macOS has no timeout command")


def test_does_not_execute_submitted_text(tmp_path: Path) -> None:
    marker = tmp_path / "ran"
    assert decision(f"echo sample > {shlex.quote(str(marker))}") is None
    assert not marker.exists()


def test_rejects_duplicated_command() -> None:
    result = run_hook(
        '{"tool_input":{"command":"pip install sample","command":"uv add sample"}}',
        check=False,
    )
    assert result.returncode == 1
    assert "Duplicate field in hook payload" in result.stderr
