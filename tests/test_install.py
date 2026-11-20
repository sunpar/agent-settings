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
RETIRED_CODEX_PLUGINS = (
    "anthropic-essentials@agent-settings",
    "bio-research@claude-cowork",
    "claude-md-management@claude-plugins-official",
    "claude-tools@claude-settings",
    "codex-advisor@claude-settings",
    "codex@openai-codex",
    "cowork-plugin-management@claude-cowork",
    "desktop-commander@claude-cowork",
    "feature-dev@claude-plugins-official",
    "frontend-design@claude-plugins-official",
    "intelligent-compact@claude-settings",
    "phd-skills@agent-settings",
    "product-tracking-skills@claude-cowork",
    "skill-creator@claude-plugins-official",
    "superpowers@claude-plugins-official",
)
DISABLED_CODEX_PLUGINS = (
    "agent-browser@claude-settings",
    "cloudflare-skills@claude-settings",
    "data@claude-cowork",
    "design@claude-cowork",
    "engineering@claude-cowork",
    "finance@claude-cowork",
    "google-drive@openai-curated",
    "labrat@agent-settings",
    "miro@claude-cowork",
    "openobserve-skills@claude-settings",
    "product-management@claude-cowork",
)


def run_installer(home: Path, *args: str, path: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO / "install"), *args],
        env={**os.environ, "HOME": str(home), "PATH": path},
        capture_output=True,
        text=True,
    )


def run(home: Path, *args: str) -> str:
    result = run_installer(home, *args)
    result.check_returncode()
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


def test_codex_install_refresh_requires_configured_packages(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    codex = bin_dir / "codex"
    write(
        codex,
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "assert sys.argv[1:] == ['app-server', '--stdio']\n"
        "assert json.loads(input())['method'] == 'initialize'\n"
        "print(json.dumps({'id': 1, 'result': {}}), flush=True)\n"
        "assert json.loads(input())['method'] == 'initialized'\n"
        "request = json.loads(input())\n"
        "assert request['method'] == 'plugin/list'\n"
        "assert request['params'] == {'marketplaceKinds': ['local'], 'forceRefetch': True}\n"
        "print(json.dumps({'id': 2, 'result': {'marketplaces': []}}), flush=True)\n",
    )
    codex.chmod(0o755)
    home = tmp_path / "home"
    assert run_installer(home, "codex", "--dry-run", path=str(bin_dir)).returncode == 0
    assert not (home / ".codex/config.toml").exists()
    result = run_installer(home, "codex", path=str(bin_dir))
    assert result.returncode == 1
    assert (home / ".codex/config.toml").is_file()
    assert "Codex could not install" in result.stderr
    assert "labrat@agent-settings" in result.stderr
    assert "pstack@agent-settings" in result.stderr
    assert "google-drive@openai-curated-remote" not in result.stderr


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
                    "codex-advisor@claude-settings": True,
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
        + "".join(
            f'[plugins."{name}"]\nenabled = true\n\n'
            for name in (*RETIRED_CODEX_PLUGINS, *DISABLED_CODEX_PLUGINS)
        )
        + '[marketplaces.cursor-plugins]\nsource_type = "git"\nsource = "https://github.com/cursor/plugins.git"\n\n'
        '[marketplaces.openai-codex]\nsource_type = "git"\nsource = "https://example.invalid/bridge.git"\n\n'
        '[marketplaces.claude-plugins-official]\nsource_type = "git"\nsource = "https://example.invalid/marketplace.git"\n\n'
        f'[[skills.config]]\npath = "{tmp_path}/local-skill/SKILL.md"\nenabled = false\n\n'
        '[[skills.config]]\nname = "pages:write-page"\nenabled = true\n',
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
    assert "codex-advisor@claude-settings" not in settings["enabledPlugins"]
    assert settings["enabledPlugins"]["codex-advisor@agent-settings"] is True
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
    assert set(RETIRED_CODEX_PLUGINS).isdisjoint(config["plugins"])
    assert config["plugins"]["codex-advisor@agent-settings"] == {"enabled": True}
    for name in DISABLED_CODEX_PLUGINS:
        assert config["plugins"][name]["enabled"] is False
    assert config["plugins"]["pstack@agent-settings"] == {"enabled": True}
    assert "cursor-plugins" not in config["marketplaces"]
    assert "openai-codex" not in config["marketplaces"]
    assert "claude-plugins-official" not in config["marketplaces"]
    assert config["marketplaces"]["agent-settings"] == {
        "source_type": "local",
        "source": f"{REPO}/plugins",
    }
    assert config["notify"][0].startswith(f"{home}/.codex/")
    rules = config["skills"]["config"]
    assert rules[0] == {"path": str(home / "local-skill/SKILL.md"), "enabled": False}
    assert [rule for rule in rules if rule.get("name") == "pages:write-page"] == [
        {"name": "pages:write-page", "enabled": False}
    ]


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
    codex_config = tomllib.loads((tmp_path / ".codex/config.toml").read_text())
    codex_plugins = codex_config["plugins"]
    assert set(RETIRED_CODEX_PLUGINS).isdisjoint(codex_plugins)
    assert "openai-codex" not in codex_config["marketplaces"]
    for name in DISABLED_CODEX_PLUGINS:
        assert codex_plugins[name]["enabled"] is False
    assert codex_plugins["product-tracking@claude-cowork"] == {"enabled": True}
    assert codex_plugins["pstack@agent-settings"] == {"enabled": True}
    for name in ("app-68de829bf7648191acd70a907364c67c", "google-drive", "pages", "sites"):
        assert codex_plugins[f"{name}@openai-curated-remote"] == {"enabled": True}
    assert codex_config["marketplaces"]["claude-cowork"] == {
        "source_type": "local",
        "source": f"{REPO}/codex/marketplaces/claude-cowork",
    }
    assert codex_config["marketplaces"]["mattpocock"]["source"] == "https://github.com/mattpocock/skills.git"
    assert len(codex_config["skills"]["config"]) == 16
    assert not (tmp_path / BACKUPS).exists()
    assert run(tmp_path).strip() == "up to date"
