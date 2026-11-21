# HCI and Open Science Agent Standards

[![Validate Agent Standards](https://github.com/M-Colley/agent-standards/actions/workflows/validate.yml/badge.svg)](https://github.com/M-Colley/agent-standards/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Default-on operating rules, HCI empirical manuscript skill, four-gate peer-review rubric, and automated LaTeX prose gates for Google Antigravity, Claude Code, and OpenAI Codex.

## Default-On Architecture

Every target installation activates universal engineering and prose invariants continuously while loading detailed manuscript rules on demand to minimize token consumption.

| Agent Surface | Always-On Global Rules | Auto-Invoked Skill (`hci-paper-writing`) | Mechanical `Stop` Gate |
| :--- | :--- | :--- | :--- |
| **Antigravity** (App, CLI, IDE) | `~/.gemini/config/plugins/agent-standards/rules/AGENTS.md` + `upstream-prs.md` | `~/.gemini/config/plugins/agent-standards/skills/hci-paper-writing/` (auto or `/hci-paper-writing`) | `hooks.json` (`stop_prose_gate.py`) |
| **Claude Code** (CLI, VS Code, JetBrains, Desktop) | `~/.claude/CLAUDE.md` (or plugin `SessionStart` + `SubagentStart` hooks) | `~/.claude/skills/hci-paper-writing/` (auto or `/hci-paper-writing`) | `~/.claude/settings.json` `hooks.Stop` (or plugin `Stop` hook) |
| **OpenAI Codex** (CLI and Desktop App) | `~/.codex/AGENTS.md` (or `$CODEX_HOME/AGENTS.md`) | `~/.codex/skills/hci-paper-writing/` (`allow_implicit_invocation: true`, auto or `$hci-paper-writing`) | Run `python -m mechcheck check .` via `AGENTS.md` + `SKILL.md` |

## Quickstart: Enable Everywhere by Default

Clone the repository once and run the zero-dependency Python 3.12+ installer to configure Antigravity, Claude Code, and Codex with all rules, skills, and hooks enabled by default across every workspace on your machine:

```bash
git clone https://github.com/M-Colley/agent-standards ~/.gemini/config/plugins/agent-standards
python ~/.gemini/config/plugins/agent-standards/scripts/install.py
```

After that single command finishes, every new session across Antigravity, Claude Code, and Codex enforces the global operating rules automatically without per-project setup or manual slash commands.

## Detailed Setup and Usage by Agent

### 1. Google Antigravity (App, CLI, and IDE)

Install globally from GitHub with the Antigravity CLI (`agy`):

```bash
agy plugin install https://github.com/M-Colley/agent-standards
```

Alternatively, clone directly into `~/.gemini/config/plugins/agent-standards` if you use only the Antigravity App or Antigravity IDE:

```bash
git clone https://github.com/M-Colley/agent-standards ~/.gemini/config/plugins/agent-standards
```

* **Default-on behavior**: Antigravity loads the plugin automatically on the next turn with `"disabled": false`. Therefore, `rules/AGENTS.md` applies on every turn, `rules/upstream-prs.md` activates whenever upstream dependency bugs appear, `hooks.json` runs `scripts/stop_prose_gate.py` automatically whenever `.tex` files change, and `hci-paper-writing` activates automatically whenever you draft, edit, or review academic prose.
* **Explicit invocation and UI controls**: Type `/hci-paper-writing` in chat to force skill activation on edge-case prompts, or open **Customizations > Installed > HCI and Open Science Standards** in the Antigravity App to inspect bundled rules, skills, and starter prompts.

### 2. Claude Code (CLI, IDE Extensions, and Desktop)

Two installation methods keep all rules, skills, and hooks enabled by default in Claude Code.

#### Method A: Global Configuration Sync (Recommended for CLI + VS Code + JetBrains + Desktop + `-p` Headless Runs)

Run the installer targeting Claude Code (honors `CLAUDE_CONFIG_DIR`, defaulting to `~/.claude`):

```bash
python scripts/install.py --agents claude
```

* **Default-on behavior**: Writes the managed rules block into `~/.claude/CLAUDE.md` (preserving any personal instructions outside `<!-- BEGIN AGENT-STANDARDS -->`), installs `~/.claude/skills/hci-paper-writing/`, and registers `~/.claude/hooks/agent-standards-stop.py` under `hooks.Stop` in `~/.claude/settings.json`. Consequently, every interactive chat, IDE panel, subagent, and non-interactive `claude -p` run inherits the rules and LaTeX `Stop` gate automatically.
* **Explicit invocation**: Claude activates `hci-paper-writing` automatically from its frontmatter description when working on papers, proposals, statistics, or reviews; type `/hci-paper-writing` in chat whenever you want to invoke it manually.

#### Method B: Native Claude Code Marketplace Plugin

Install directly from GitHub via the Claude Code CLI:

```bash
claude plugin marketplace add M-Colley/agent-standards
claude plugin install agent-standards@agent-standards
```

Inside an active Claude Code interactive session, run the equivalent slash commands:

```text
/plugin marketplace add M-Colley/agent-standards
/plugin install agent-standards@agent-standards
```

* **Default-on behavior**: `.claude-plugin/plugin.json` wires `SessionStart` and `SubagentStart` (`scripts/claude_session_start.py`) to inject `rules/AGENTS.md` into every main thread and subagent automatically, wires `Stop` (`scripts/stop_prose_gate.py`) to block turn completion when modified `.tex` files violate prose or `mechcheck` rules, and registers `/hci-paper-writing` globally. If Method A is also installed on the same machine, both hooks deduplicate automatically so rules and checks run once.

### 3. OpenAI Codex (CLI and Desktop App)

Sync the global Codex rules and skill directory (honors `CODEX_HOME`, defaulting to `~/.codex`):

```bash
python scripts/install.py --agents codex
```

* **Default-on behavior**: Codex loads `~/.codex/AGENTS.md` unconditionally at the start of every Codex CLI and Codex Desktop App conversation, including delegated subagents and review agents, across all repositories. Additionally, `skills/hci-paper-writing/agents/openai.yaml` sets `policy.allow_implicit_invocation: true`, so Codex automatically selects and loads `hci-paper-writing` whenever a prompt involves papers, abstracts, LaTeX sections, statistical reporting, proposals, or peer reviews.
* **Explicit invocation**: Codex prefixes skills with `$`. Type `$hci-paper-writing` in any Codex CLI or Desktop prompt to invoke the manuscript and review specification explicitly.

## Included Components

* `rules/AGENTS.md` and `rules/upstream-prs.md`: Always-on and conditional rules enforcing concise candid tone, HCI technical register, single-line prose paragraph reflow with formatter-safe code/commit limits, prose dash prohibition with lexical hyphen retention, banned rhetorical styles, open science, permissive dependency reuse, newest stable software and runtime version targeting, auto-fixers, live CI verification (`gh pr checks` and `gh run view --log-failed`), merged-branch cleanup, upstream pull requests, and model tiering.
* `skills/hci-paper-writing/`: Progressive-disclosure skill (`SKILL.md`, `references/colley-hci-spec.md`, `references/peer-review-rubric.md`, and `agents/openai.yaml`) encoding the Colley et al. (CHI, IMWUT, AutomotiveUI) quantitative style specification, mixed-effects and equivalence-testing (`TOST` / $BF_{01}$) statistical reporting rules, a four-gate peer-review rubric, and [`mechcheck`](https://github.com/M-Colley/mechcheck) verification.
* `hooks.json`, `scripts/stop_prose_gate.py`, and `scripts/claude_session_start.py`: Cross-platform Python 3.12+ lifecycle hooks for Antigravity and Claude Code.

## Updating, Verification, and Removal

Pull upstream changes and re-sync all installed agents:

```bash
git -C ~/.gemini/config/plugins/agent-standards pull
python ~/.gemini/config/plugins/agent-standards/scripts/install.py
```

Verify zero drift across installed targets or run the full repository test suite:

```bash
python scripts/install.py --check
python scripts/validate_repo.py
```

Remove all managed blocks, skills, hooks, and plugin files cleanly while preserving unrelated user settings:

```bash
python scripts/install.py --uninstall
```
