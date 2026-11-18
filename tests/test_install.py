import hashlib
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BACKUPS = Path(".local/state/agent-settings/backups")


def run(home: Path, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(REPO / "install"), *args],
        env={**os.environ, "HOME": str(home)},
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): f"-> {os.readlink(path)}"
        if path.is_symlink()
        else hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_symlink() or path.is_file()
    }


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    write(
        tmp_path / ".claude/settings.json",
        json.dumps(
            {
                "theme": "light",
                "feedbackSurveyState": {"lastShownTime": 1},
                "permissions": {
                    "allow": ["Bash(ls:*)", "Bash(my-own-tool:*)"],
                    "ask": ["Bash(rm -rf:*)"],
                },
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit",
                            "hooks": [{"type": "command", "command": "old"}],
                        }
                    ]
                },
                "enabledPlugins": {
                    "pstack@cursor-plugins": True,
                    "mine@elsewhere": True,
                },
                "extraKnownMarketplaces": {
                    "cursor-plugins": {
                        "source": {"source": "github", "repo": "cursor/plugins"}
                    }
                },
            }
        ),
    )
    write(
        tmp_path / ".codex/config.toml",
        "# my comment\n"
        'model = "old-model"\n\n'
        '[projects."/x"]\ntrust_level = "trusted"\n\n'
        '[hooks.state."/h/hooks.json:pre_tool_use:0:0"]\ntrusted_hash = "abc"\n\n'
        '[plugins."pstack@cursor-plugins"]\nenabled = true\n\n'
        '[plugins."anthropic-essentials@agent-settings"]\nenabled = true\n\n'
        '[marketplaces.cursor-plugins]\nsource_type = "git"\nsource = "https://github.com/cursor/plugins.git"\n',
    )
    write(
        tmp_path / ".codex/rules/default.rules",
        'prefix_rule(pattern=["my-approved"], decision="allow")\n',
    )
    write(tmp_path / ".claude/skills/full-send/SKILL.md", "stale copy\n")
    write(tmp_path / ".claude/skills/synced/thing/SKILL.md", "managed by claude\n")
    write(tmp_path / ".codex/skills/.system/thing/SKILL.md", "managed by codex\n")
    write(tmp_path / ".claude/hooks/edit_checks.py", "old hook\n")
    return tmp_path


def test_links_point_into_repo(home: Path) -> None:
    run(home)
    for link, target in [
        (".claude/CLAUDE.md", "AGENTS.md"),
        (".codex/AGENTS.md", "AGENTS.md"),
        (".agents/AGENTS.md", "AGENTS.md"),
        (".claude/rules/pstack-models.md", "claude/rules/pstack-models.md"),
        (".claude/skills/full-send", "skills/full-send"),
        (".codex/skills/full-send", "skills/full-send"),
    ]:
        assert (home / link).is_symlink() and (
            home / link
        ).resolve() == REPO / target, link


def test_claude_settings_merge(home: Path) -> None:
    run(home)
    settings = json.loads((home / ".claude/settings.json").read_text())
    assert settings["feedbackSurveyState"] == {"lastShownTime": 1}
    assert settings["theme"] == "dark"
    assert settings["permissions"]["allow"][:2] == ["Bash(ls:*)", "Bash(my-own-tool:*)"]
    assert "ask" not in settings["permissions"]
    assert settings["enabledPlugins"]["mine@elsewhere"] is True
    assert settings["enabledPlugins"]["pstack@agent-settings"] is True
    assert "pstack@cursor-plugins" not in settings["enabledPlugins"]
    assert "cursor-plugins" not in settings["extraKnownMarketplaces"]
    assert (
        settings["extraKnownMarketplaces"]["agent-settings"]["source"]["path"]
        == f"{REPO}/plugins"
    )
    assert settings["statusLine"]["command"] == f'bash "{REPO}/claude/statusline.sh"'
    commands = [
        hook["command"]
        for group in settings["hooks"]["PreToolUse"]
        for hook in group["hooks"]
    ]
    assert "old" not in commands
    assert f'python3 "{REPO}/hooks/edit_checks.py" pre' in commands
    for event in ("SessionStart", "Stop"):
        assert settings["hooks"][event][0]["hooks"][0]["command"] == (
            f'python3 "{REPO}/hooks/untracked_check.py"'
        )


def test_codex_config_merge(home: Path) -> None:
    run(home)
    text = (home / ".codex/config.toml").read_text()
    config = tomllib.loads(text)
    assert "# my comment" in text
    assert config["projects"]["/x"] == {"trust_level": "trusted"}
    assert config["hooks"]["state"]["/h/hooks.json:pre_tool_use:0:0"] == {
        "trusted_hash": "abc"
    }
    assert config["model"] != "old-model"
    assert "pstack@cursor-plugins" not in config["plugins"]
    assert "anthropic-essentials@agent-settings" not in config["plugins"]
    assert config["plugins"]["pstack@agent-settings"] == {"enabled": True}
    assert "cursor-plugins" not in config["marketplaces"]
    assert config["marketplaces"]["agent-settings"] == {
        "source_type": "local",
        "source": f"{REPO}/plugins",
    }
    assert config["notify"][0].startswith(f"{home}/.codex/")


def test_codex_hooks_and_rules(home: Path) -> None:
    run(home)
    hooks = (home / ".codex/hooks.json").read_text()
    assert not (home / ".codex/hooks.json").is_symlink()
    assert f'python3 \\"{REPO}/hooks/edit_checks.py\\" pre' in hooks
    assert hooks.count(f'python3 \\"{REPO}/hooks/untracked_check.py\\"') == 2
    assert "{{" not in hooks
    rules = (home / ".codex/rules/default.rules").read_text().splitlines()
    assert rules[0] == 'prefix_rule(pattern=["my-approved"], decision="allow")'
    assert 'prefix_rule(pattern=["gh"], decision="allow")' in rules


def test_harness_managed_dirs_untouched(home: Path) -> None:
    run(home)
    assert (
        home / ".claude/skills/synced/thing/SKILL.md"
    ).read_text() == "managed by claude\n"
    assert (
        home / ".codex/skills/.system/thing/SKILL.md"
    ).read_text() == "managed by codex\n"


def test_originals_backed_up_and_replaced(home: Path) -> None:
    run(home)
    [backup] = (home / BACKUPS).iterdir()
    assert (backup / ".claude/skills/full-send/SKILL.md").read_text() == "stale copy\n"
    assert (
        json.loads((backup / ".claude/settings.json").read_text())["theme"] == "light"
    )
    assert (backup / ".codex/config.toml").read_text().startswith("# my comment")


def test_unrelated_hook_scripts_survive(home: Path) -> None:
    write(home / ".claude/hooks/my_stop.py", "mine\n")
    run(home)
    assert (home / ".claude/hooks/my_stop.py").read_text() == "mine\n"


def test_second_run_is_up_to_date(home: Path) -> None:
    run(home)
    before = snapshot(home)
    assert run(home).strip() == "up to date"
    assert snapshot(home) == before


def test_up_to_date_after_harness_reformats_config(home: Path) -> None:
    run(home)
    settings = home / ".claude/settings.json"
    settings.write_text(json.dumps(json.loads(settings.read_text())))
    assert run(home).strip() == "up to date"


def test_dry_run_writes_nothing(home: Path) -> None:
    before = snapshot(home)
    assert "~/.claude/settings.json theme" in run(home, "--dry-run")
    assert snapshot(home) == before


def test_single_harness_leaves_other_alone(home: Path) -> None:
    codex = snapshot(home / ".codex")
    run(home, "claude")
    assert snapshot(home / ".codex") == codex
    assert not (home / ".agents").exists()
    assert (home / ".claude/CLAUDE.md").is_symlink()


def test_fresh_home(tmp_path: Path) -> None:
    run(tmp_path)
    assert (
        json.loads((tmp_path / ".claude/settings.json").read_text())["enabledPlugins"][
            "pstack@agent-settings"
        ]
        is True
    )
    codex_plugins = tomllib.loads((tmp_path / ".codex/config.toml").read_text())["plugins"]
    assert "anthropic-essentials@agent-settings" not in codex_plugins
    assert codex_plugins["pstack@agent-settings"] == {"enabled": True}
    assert not (tmp_path / BACKUPS).exists()
    assert run(tmp_path).strip() == "up to date"
