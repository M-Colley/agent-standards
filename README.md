# HCI and Open Science Agent Standards

Multi-provider plugin and global instruction repository for Google Antigravity, Claude Code, and OpenAI Codex.

## Included Components

* `rules/AGENTS.md` and `rules/upstream-prs.md`: Always-on and conditional operating rules covering direct HCI technical prose, single-line prose paragraph reflow with formatter-safe code/commit exemptions, prose dash prohibition with lexical hyphen retention, banned rhetorical styles, open science, library reuse, CI verification (`gh pr checks` and `gh run view --log-failed`), branch hygiene, upstream pull requests, and model routing.
* `skills/hci-paper-writing/`: On-demand skill (`SKILL.md`, `references/colley-hci-spec.md`, `references/peer-review-rubric.md`, and `agents/openai.yaml`) implementing the Colley et al. (CHI, IMWUT, AutomotiveUI) empirical paper style specification, mixed-effects and equivalence-testing statistical reporting standards, a four-gate peer-review rubric, and automated [`mechcheck`](https://github.com/M-Colley/mechcheck) verification.
* `hooks.json` and `scripts/stop_prose_gate.py`: Synchronous `Stop` gate for Antigravity and Claude Code that inspects modified `.tex` files for prose dashes, banned phrases, raw `\ref{}` usage, and `mechcheck` errors prior to turn completion.
* `.antigravity-plugin/plugin.json`, `.claude-plugin/plugin.json`, and `.codex-plugin/plugin.json`: Native multi-provider plugin manifests validated on Linux, Windows, and macOS via `.github/workflows/validate.yml`.

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

## Sync Across Antigravity, Claude Code, and Codex

Run the zero-dependency Python installer to sync Antigravity (`~/.gemini/config/plugins/agent-standards/`), Claude Code (`~/.claude/CLAUDE.md` and `~/.claude/skills/`), and Codex (`~/.codex/AGENTS.md` and `~/.codex/skills/`):

```bash
python scripts/install.py              # Sync Antigravity, Claude Code, and Codex
python scripts/install.py --check      # Verify zero drift across targets
python scripts/validate_repo.py        # Run manifest, hook, and installer self-tests
python scripts/install.py --uninstall  # Remove managed rules, skills, and plugin
```
