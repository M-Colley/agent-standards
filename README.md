# HCI and Open Science Agent Standards

Native Antigravity plugin and cross-agent instruction bundle for Google Antigravity, Claude Code, and OpenAI Codex.

## Included Components

* `rules/AGENTS.md`: Compact (~500 tokens) always-on operating rules covering direct scientific tone, open science, single-line paragraph reflow, dash prohibition, banned rhetorical styles, default-reject peer review stance, library reuse, platform independence, auto-fixers, branch cleanup, upstream PRs, and model routing.
* `skills/hci-paper-writing/`: On-demand skill (`SKILL.md`, `references/colley-hci-spec.md`, and `agents/openai.yaml`) implementing the Colley et al. (CHI, IMWUT, AutomotiveUI) empirical paper style specification and automated [`mechcheck`](https://github.com/M-Colley/mechcheck) verification.

## Install in Antigravity

With the Antigravity CLI (`agy`):

```bash
agy plugin install https://github.com/M-Colley/agent-standards
```

Without the CLI (Antigravity App and Antigravity IDE auto-discover global plugins on the next turn):

```bash
git clone https://github.com/M-Colley/agent-standards ~/.gemini/config/plugins/agent-standards
```

Update at any time with `git -C ~/.gemini/config/plugins/agent-standards pull`. Manage or toggle the bundle in the Antigravity App under **Customizations > Installed**, and invoke the writing skill via `/hci-paper-writing`.

## Install in Claude Code and Codex

Run the zero-dependency Python installer from the cloned repository to sync `~/.claude/` and `~/.codex/` (plus `~/.gemini/config/plugins/agent-standards/` if cloned elsewhere):

```bash
python scripts/install.py              # Sync Antigravity, Claude Code, and Codex
python scripts/install.py --check      # Verify zero drift across targets
python scripts/install.py --uninstall  # Remove managed rules, skills, and plugin
```
