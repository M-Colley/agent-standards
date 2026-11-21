#!/usr/bin/env python3
"""Claude Code SessionStart and SubagentStart hook keeping rules/AGENTS.md active by default."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BEGIN_MARKER = "<!-- BEGIN AGENT-STANDARDS -->"


def claude_config_dir() -> Path:
    env_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".claude"


def global_claude_md_has_rules() -> bool:
    claude_md = claude_config_dir() / "CLAUDE.md"
    if not claude_md.is_file():
        return False
    try:
        return BEGIN_MARKER in claude_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def main() -> int:
    if global_claude_md_has_rules():
        return 0

    repo_root = Path(__file__).resolve().parent.parent
    rules_path = repo_root / "rules" / "AGENTS.md"
    if not rules_path.is_file():
        return 0
    try:
        rules_text = rules_path.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    if not rules_text:
        return 0

    if "--subagent" in sys.argv:
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": rules_text,
            }
        }
        sys.stdout.write(json.dumps(payload) + "\n")
    else:
        sys.stdout.write(rules_text + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
