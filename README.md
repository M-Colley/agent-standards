# HCI and Open Science Agent Standards

[![Validate Agent Standards](https://github.com/M-Colley/agent-standards/actions/workflows/validate.yml/badge.svg)](https://github.com/M-Colley/agent-standards/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Default-on operating rules, HCI empirical manuscript skill, four-gate peer-review rubric, automated LaTeX prose gates, and companion engineering skills ([`mattpocock/skills`](https://github.com/mattpocock/skills)) for Google Antigravity, Claude Code, and OpenAI Codex.

## Default-On Architecture

Every target installation activates universal engineering and prose invariants continuously while loading detailed manuscript and software-engineering skills on demand to minimize token consumption.

| Agent Surface | Always-On Global Rules | Auto-Invoked Skill (`hci-paper-writing`) | Companion Engineering Skills ([`mattpocock/skills`](https://github.com/mattpocock/skills)) | Mechanical `Stop` Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Antigravity** (App, CLI, IDE) | `~/.gemini/config/plugins/agent-standards/rules/AGENTS.md` + `upstream-prs.md` | `~/.gemini/config/plugins/agent-standards/skills/hci-paper-writing/` (auto or `/hci-paper-writing`) | `~/.gemini/config/plugins/mattpocock-skills/skills/*` (27 promoted skills, auto or `/<skill>`) | `hooks.json` (`stop_prose_gate.py`) |
| **Claude Code** (CLI, VS Code, JetBrains, Desktop) | `~/.claude/CLAUDE.md` (or plugin `SessionStart` + `SubagentStart` hooks) | `~/.claude/skills/hci-paper-writing/` (auto or `/hci-paper-writing`) | `~/.claude/skills/*` via `install.py`, or `mattpocock-skills@claude-plugins-official` (auto-deduplicated) | `~/.claude/settings.json` `hooks.Stop` (or plugin `Stop` hook) |
| **OpenAI Codex** (CLI and Desktop App) | `~/.codex/AGENTS.md` (or `$CODEX_HOME/AGENTS.md`) | `~/.codex/skills/hci-paper-writing/` (`allow_implicit_invocation: true`, auto or `$hci-paper-writing`) | `~/.codex/skills/*` via `install.py`, or `mattpocock-skills@mattpocock` (auto-deduplicated) | Run `python -m mechcheck check .` via `AGENTS.md` + `SKILL.md` |

## Quickstart: Enable Everywhere by Default

Clone the repository once and run the zero-dependency Python 3.12+ installer to configure Antigravity, Claude Code, and Codex with all rules, skills, companion [`mattpocock/skills`](https://github.com/mattpocock/skills) workflows, and hooks enabled by default across every workspace on your machine:

```bash
git clone https://github.com/M-Colley/agent-standards ~/.gemini/config/plugins/agent-standards
python ~/.gemini/config/plugins/agent-standards/scripts/install.py
```

After that single command finishes, every new session across Antigravity, Claude Code, and Codex enforces the global operating rules and exposes both `hci-paper-writing` and the promoted [`mattpocock/skills`](https://github.com/mattpocock/skills) suite automatically without per-project installation.

## Detailed Setup and Usage by Agent

### 1. Google Antigravity (App, CLI, and IDE)

Clone `agent-standards` and run `scripts/install.py` targeting Antigravity to install both `agent-standards` and `mattpocock-skills` globally:

```bash
git clone https://github.com/M-Colley/agent-standards ~/.gemini/config/plugins/agent-standards
python ~/.gemini/config/plugins/agent-standards/scripts/install.py --agents antigravity
```

If you install `agent-standards` via `agy plugin install https://github.com/M-Colley/agent-standards`, still run `python ~/.gemini/config/plugins/agent-standards/scripts/install.py --agents antigravity` once so the flat `mattpocock-skills` plugin bundle is staged under `~/.gemini/config/plugins/mattpocock-skills`.

* **Default-on behavior**: Antigravity loads both `agent-standards` and `mattpocock-skills` automatically on the next turn with `"disabled": false`. Therefore, `rules/AGENTS.md` applies on every turn, `rules/upstream-prs.md` activates whenever upstream dependency bugs appear, `hooks.json` runs `scripts/stop_prose_gate.py` automatically whenever `.tex` files change, `hci-paper-writing` activates automatically whenever you draft, edit, or review academic prose, and all 27 promoted engineering and productivity skills from `mattpocock/skills` are available on demand.
* **Explicit invocation and UI controls**: Type `/hci-paper-writing`, `/grill-me`, `/grill-with-docs`, `/tdd`, `/to-spec`, `/to-tickets`, or `/setup-matt-pocock-skills` in chat to invoke skills explicitly, or open **Customizations > Installed** in the Antigravity App to inspect **HCI and Open Science Standards** and **Matt Pocock Skills**.

### 2. Claude Code (CLI, IDE Extensions, and Desktop)

Two installation methods keep all rules, skills, companion `mattpocock/skills` workflows, and hooks enabled by default in Claude Code.

#### Method A: Global Configuration Sync (Recommended for CLI + VS Code + JetBrains + Desktop + `-p` Headless Runs)

Run the installer targeting Claude Code (honors `CLAUDE_CONFIG_DIR`, defaulting to `~/.claude`):

```bash
python scripts/install.py --agents claude
```

* **Default-on behavior**: Writes the managed rules block into `~/.claude/CLAUDE.md` (preserving any personal instructions outside `<!-- BEGIN AGENT-STANDARDS -->`), installs `~/.claude/skills/hci-paper-writing/` plus all 27 promoted skills from `mattpocock/skills` (unless `mattpocock-skills` is already enabled in `~/.claude/settings.json`), and registers `~/.claude/hooks/agent-standards-stop.py` under `hooks.Stop` in `~/.claude/settings.json`. Consequently, every interactive chat, IDE panel, subagent, and non-interactive `claude -p` run inherits the rules, skills, and LaTeX `Stop` gate automatically.
* **Explicit invocation**: Claude activates model-invoked skills automatically from frontmatter descriptions; type `/hci-paper-writing`, `/grill-me`, `/grill-with-docs`, `/tdd`, or `/setup-matt-pocock-skills` in chat whenever you want to invoke a skill manually.

#### Method B: Native Claude Code Marketplace Plugins

Install both plugins directly via the Claude Code CLI so Claude Code manages updates automatically:

```bash
claude plugin marketplace add M-Colley/agent-standards
claude plugin install agent-standards@agent-standards
claude plugin install mattpocock-skills@claude-plugins-official
```

Inside an active Claude Code interactive session, run the equivalent slash commands:

```text
/plugin marketplace add M-Colley/agent-standards
/plugin install agent-standards@agent-standards
/plugin install mattpocock-skills@claude-plugins-official
```

* **Default-on behavior**: `.claude-plugin/plugin.json` wires `SessionStart` and `SubagentStart` (`scripts/claude_session_start.py`) to inject `rules/AGENTS.md` into every main thread and subagent automatically, wires `Stop` (`scripts/stop_prose_gate.py`) to block turn completion when modified `.tex` files violate prose or `mechcheck` rules, and registers `/hci-paper-writing` alongside `mattpocock-skills`. If Method A is also run on the same machine, `install.py` detects enabled plugins in `~/.claude/settings.json` and skips duplicate hooks and flat skill copies automatically.

### 3. OpenAI Codex (CLI and Desktop App)

Sync the global Codex rules and skill directories (honors `CODEX_HOME`, defaulting to `~/.codex`):

```bash
python scripts/install.py --agents codex
```

Alternatively, if you prefer Codex's native marketplace updater for `mattpocock/skills`, register the marketplace and plugin via the Codex CLI before or after running `install.py`:

```bash
codex plugin marketplace add mattpocock/skills
codex plugin add mattpocock-skills@mattpocock
```

* **Default-on behavior**: Codex loads `~/.codex/AGENTS.md` unconditionally at the start of every Codex CLI and Codex Desktop App conversation, including delegated subagents and review agents, across all repositories. Additionally, `install.py` installs `hci-paper-writing` plus all 27 promoted `mattpocock/skills` directories (each including `agents/openai.yaml`) into `~/.codex/skills/`, automatically skipping flat `mattpocock/skills` copies whenever `mattpocock-skills@mattpocock` is already enabled in `~/.codex/config.toml`.
* **Explicit invocation**: Codex prefixes skills with `$`. Type `$hci-paper-writing`, `$grill-me`, `$grill-with-docs`, `$tdd`, or `$setup-matt-pocock-skills` in any Codex CLI or Desktop prompt to invoke a skill explicitly.

### 4. Gemini CLI (Optional Companion Surface)

When also using the standalone Gemini CLI, install the two promoted buckets from [`mattpocock/skills`](https://github.com/mattpocock/skills) directly:

```bash
gemini skills install https://github.com/mattpocock/skills.git --path skills/engineering
gemini skills install https://github.com/mattpocock/skills.git --path skills/productivity
```

## Included and Companion Components

* `rules/AGENTS.md` and `rules/upstream-prs.md`: Always-on and conditional rules enforcing concise candid tone, HCI technical register, single-line prose paragraph reflow with formatter-safe code/commit limits, prose dash prohibition with lexical hyphen retention, banned rhetorical styles, open science, codebase ownership, permissive dependency reuse, newest stable software and runtime version targeting, auto-fixers, live CI verification (`gh pr checks` and `gh run view --log-failed`), merged-branch cleanup, upstream pull requests, and model tiering.
* `skills/hci-paper-writing/`: Progressive-disclosure skill (`SKILL.md`, `references/colley-hci-spec.md`, `references/peer-review-rubric.md`, and `agents/openai.yaml`) encoding the Colley et al. (CHI, IMWUT, AutomotiveUI) quantitative style specification, mixed-effects and equivalence-testing (`TOST` / $BF_{01}$) statistical reporting rules, a four-gate peer-review rubric, and [`mechcheck`](https://github.com/M-Colley/mechcheck) verification.
* [`mattpocock/skills`](https://github.com/mattpocock/skills) (`mattpocock-skills`, automatically cloned and synced by `scripts/install.py`): Promoted engineering skills (`ask-matt`, `code-review`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `grill-with-docs`, `implement`, `implement-spec`, `improve-codebase-architecture`, `pr`, `prototype`, `research`, `retro`, `setup-matt-pocock-skills`, `tdd`, `to-spec`, `to-tickets`, `triage`, `wayfinder`, `wizard`) and productivity skills (`grill-me`, `grilling`, `handoff`, `teach`, `to-questionnaire`, `wait-what`, `writing-for-agents`). Run `/setup-matt-pocock-skills` (or `$setup-matt-pocock-skills` in Codex) once per repository when configuring issue-tracker and documentation conventions for that workflow.
* `hooks.json`, `scripts/stop_prose_gate.py`, and `scripts/claude_session_start.py`: Cross-platform Python 3.12+ lifecycle hooks for Antigravity and Claude Code.

## Updating, Verification, and Removal

Pull upstream `agent-standards` changes and re-sync all installed agents (which also fast-forwards the cached [`mattpocock/skills`](https://github.com/mattpocock/skills) repository and updates all installed skill targets):

```bash
git -C ~/.gemini/config/plugins/agent-standards pull
python ~/.gemini/config/plugins/agent-standards/scripts/install.py
```

Verify zero drift across installed targets or run the full repository test suite:

```bash
python scripts/install.py --check
python scripts/validate_repo.py
```

Remove all managed blocks, skills (including managed `mattpocock/skills` installations), hooks, and plugin files cleanly while preserving unrelated user settings:

```bash
python scripts/install.py --uninstall
```
