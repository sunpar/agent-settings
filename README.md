# agent-settings

Global instructions, skills, hooks, settings, and plugins for Claude Code and Codex, installed from one repo.

- `AGENTS.md`: global instructions for both tools (`CLAUDE.md` symlinks to it).
- `skills/`: [tstack](https://github.com/t3dotgg/tstack) at `11e37a7` (MIT, see `skills/LICENSE-tstack`), plus local skills. Keep the locally maintained `council` override when refreshing tstack.
- `plugins/`: the `agent-settings` local marketplace for both tools. Claude Code and Codex use the pinned [backnotprop/pstack mirror](https://github.com/backnotprop/pstack).
- `hooks/`: edit-check hooks shared by both tools.
- `claude/`: Claude Code settings, statusline, and rules.
- `codex/`: Codex `config.toml`, approved command rules, and the Codex catalog for public Cowork packages.
- `opencode/`: OpenCode config. Not installed.

## Install

```sh
git pull && ./install
```

`./install` needs [uv](https://docs.astral.sh/uv/). It prints each change, then links, renders, and merges the files into `~/.claude`, `~/.codex`, and `~/.agents`. Settings and config files are merged, so keys that Claude Code and Codex write themselves (permission approvals, project trust, hook trust) are kept. Run it again any time. When nothing changed it prints `up to date`.

- `./install --dry-run` prints the plan and writes nothing.
- `./install claude` or `./install codex` installs one tool only.
- Every file it replaces or removes is copied first to `~/.local/state/agent-settings/backups/<UTC timestamp>/`.
- After the first run, and whenever `hooks/hooks.json` changes, Codex asks you to trust the hooks again.

When `claude` is on `PATH`, `./install claude` installs or updates pstack through Claude Code. When `codex` is on `PATH`, `./install codex` fetches the configured marketplace packages through Codex, including plugins installed for on-demand use. If you use the desktop app alone, open its Plugins view after installation to let Codex fetch the packages. The ChatGPT account supplies connected plugins, and the app supplies its bundled plugins. Codex applies the skill exclusions for Spotify, Google Drive, Pages, and Sites from `codex/config.toml`.

To update pstack, change the pinned revision in both `plugins/.claude-plugin/marketplace.json` and `plugins/.agents/plugins/marketplace.json`.
