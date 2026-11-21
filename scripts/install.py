#!/usr/bin/env python3
"""Sync plugin and global rules/skills across Antigravity, Claude Code, and Codex."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

PLUGIN_NAME = "agent-standards"
BEGIN_MARKER = "<!-- BEGIN AGENT-STANDARDS -->"
END_MARKER = "<!-- END AGENT-STANDARDS -->"
BLOCK_RE = re.compile(
    rf"{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}\n?",
    flags=re.DOTALL,
)
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}


def build_managed_block(core_rules: str) -> str:
    return f"{BEGIN_MARKER}\n{core_rules.strip()}\n{END_MARKER}\n"


def merge_rules(existing: str | None, managed_block: str) -> str:
    if not existing or not existing.strip():
        return managed_block
    if BEGIN_MARKER in existing and END_MARKER in existing:
        updated = BLOCK_RE.sub(lambda _: managed_block, existing, count=1)
        return updated.rstrip() + "\n"
    return existing.rstrip() + "\n\n" + managed_block


def remove_rules_block(existing: str) -> str:
    cleaned = BLOCK_RE.sub("", existing).strip()
    return (cleaned + "\n") if cleaned else ""


def iter_files(root: Path) -> dict[Path, bytes]:
    if not root.exists():
        return {}
    result: dict[Path, bytes] = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and not (set(rel.parts) & SKIP_PARTS):
            result[rel] = p.read_bytes().replace(b"\r\n", b"\n")
    return result


def sync_flat_agent(
    agent: str,
    rule_path: Path,
    skills_dst_root: Path,
    managed_block: str,
    skills_src_root: Path,
    check_only: bool,
) -> list[str]:
    drift: list[str] = []
    existing = (
        rule_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if rule_path.exists()
        else None
    )
    desired_rules = merge_rules(existing, managed_block)
    if existing != desired_rules:
        drift.append(f"[{agent}] rule out of sync: {rule_path}")
        if not check_only:
            rule_path.parent.mkdir(parents=True, exist_ok=True)
            rule_path.write_text(desired_rules, encoding="utf-8", newline="\n")

    for skill_dir in sorted(p for p in skills_src_root.iterdir() if p.is_dir()):
        dst_dir = skills_dst_root / skill_dir.name
        src_tree = iter_files(skill_dir)
        dst_tree = iter_files(dst_dir)
        if src_tree != dst_tree:
            drift.append(f"[{agent}] skill out of sync: {dst_dir}")
            if not check_only:
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                for rel, data in src_tree.items():
                    out = dst_dir / rel
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(data)
    return drift


def cleanup_loose_antigravity(
    home: Path, skills_src_root: Path, check_only: bool
) -> list[str]:
    drift: list[str] = []
    loose_rule = home / ".gemini" / "AGENTS.md"
    if loose_rule.exists():
        existing = loose_rule.read_text(encoding="utf-8").replace("\r\n", "\n")
        if BEGIN_MARKER in existing:
            drift.append(f"[antigravity] duplicate loose rule block: {loose_rule}")
            if not check_only:
                remaining = remove_rules_block(existing)
                if remaining:
                    loose_rule.write_text(remaining, encoding="utf-8", newline="\n")
                else:
                    loose_rule.unlink()

    loose_skills_root = home / ".gemini" / "config" / "skills"
    for skill_dir in sorted(p for p in skills_src_root.iterdir() if p.is_dir()):
        dup_skill = loose_skills_root / skill_dir.name
        if dup_skill.exists():
            drift.append(f"[antigravity] duplicate loose skill: {dup_skill}")
            if not check_only:
                shutil.rmtree(dup_skill)
    return drift


def sync_antigravity_plugin(
    home: Path, repo_root: Path, skills_src_root: Path, check_only: bool
) -> list[str]:
    drift = cleanup_loose_antigravity(home, skills_src_root, check_only)
    plugin_dst = home / ".gemini" / "config" / "plugins" / PLUGIN_NAME
    if repo_root.resolve() == plugin_dst.resolve():
        return drift

    src_tree = iter_files(repo_root)
    dst_tree = iter_files(plugin_dst)
    if src_tree != dst_tree:
        drift.append(f"[antigravity] plugin out of sync: {plugin_dst}")
        if not check_only:
            if plugin_dst.exists():
                for child in plugin_dst.iterdir():
                    if child.name == ".git":
                        continue
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
            for rel, data in src_tree.items():
                out = plugin_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
    return drift


def uninstall_all(
    home: Path, repo_root: Path, skills_src_root: Path, agents: list[str]
) -> None:
    flat_targets = {
        "claude": (home / ".claude" / "CLAUDE.md", home / ".claude" / "skills"),
        "codex": (home / ".codex" / "AGENTS.md", home / ".codex" / "skills"),
    }
    for agent in agents:
        if agent in flat_targets:
            rule_path, skills_dst = flat_targets[agent]
            if rule_path.exists():
                existing = rule_path.read_text(encoding="utf-8").replace("\r\n", "\n")
                remaining = remove_rules_block(existing)
                if remaining:
                    rule_path.write_text(remaining, encoding="utf-8", newline="\n")
                else:
                    rule_path.unlink()
            for skill_dir in sorted(p for p in skills_src_root.iterdir() if p.is_dir()):
                dst_dir = skills_dst / skill_dir.name
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
            print(f"[{agent}] removed managed rules and skills.")
        elif agent == "antigravity":
            cleanup_loose_antigravity(home, skills_src_root, check_only=False)
            plugin_dst = home / ".gemini" / "config" / "plugins" / PLUGIN_NAME
            if plugin_dst.exists() and repo_root.resolve() != plugin_dst.resolve():
                shutil.rmtree(plugin_dst)
            print(f"[antigravity] removed plugin at {plugin_dst}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agents",
        nargs="+",
        choices=["antigravity", "claude", "codex"],
        default=["antigravity", "claude", "codex"],
        help="Target agent surfaces to manage.",
    )
    parser.add_argument(
        "--home",
        type=Path,
        default=Path.home(),
        help="Override home directory for testing.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Verify installed targets match canonical sources without writing.",
    )
    mode.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove managed rules, skills, and plugin directories.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    core_rules = (repo_root / "rules" / "AGENTS.md").read_text(encoding="utf-8")
    skills_src_root = repo_root / "skills"
    managed_block = build_managed_block(core_rules)
    home = args.home.resolve()

    if args.uninstall:
        uninstall_all(home, repo_root, skills_src_root, args.agents)
        return 0

    all_drift: list[str] = []
    flat_targets = {
        "claude": (home / ".claude" / "CLAUDE.md", home / ".claude" / "skills"),
        "codex": (home / ".codex" / "AGENTS.md", home / ".codex" / "skills"),
    }
    for agent in args.agents:
        if agent == "antigravity":
            drift = sync_antigravity_plugin(
                home, repo_root, skills_src_root, check_only=args.check
            )
            all_drift.extend(drift)
            if not args.check:
                print(
                    f"[antigravity] synced plugin -> {home / '.gemini/config/plugins' / PLUGIN_NAME}"
                )
        else:
            rule_path, skills_dst = flat_targets[agent]
            drift = sync_flat_agent(
                agent,
                rule_path,
                skills_dst,
                managed_block,
                skills_src_root,
                check_only=args.check,
            )
            all_drift.extend(drift)
            if not args.check:
                print(f"[{agent}] synced -> {rule_path} & {skills_dst}")

    if args.check:
        if all_drift:
            for item in all_drift:
                print(item)
            return 1
        print("All targets match canonical sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
