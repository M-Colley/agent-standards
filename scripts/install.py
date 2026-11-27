#!/usr/bin/env python3
"""Sync default-on rules, skills, companion mattpocock/skills, and hooks across agents."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

PLUGIN_NAME = "agent-standards"
MATTPOCOCK_PLUGIN_NAME = "mattpocock-skills"
MATTPOCOCK_REPO_URL = "https://github.com/mattpocock/skills.git"
MATTPOCOCK_FALLBACK_BUCKETS = ("engineering", "productivity")
MATTPOCOCK_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128" fill="none">
  <rect x="16" y="16" width="96" height="96" rx="20" fill="#0F172A" stroke="#F59E0B" stroke-width="6"/>
  <path d="M40 48L56 64L40 80" stroke="#F59E0B" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M64 80H88" stroke="#F8FAFC" stroke-width="8" stroke-linecap="round"/>
</svg>
"""
CLAUDE_STOP_SCRIPT = "agent-standards-stop.py"
BEGIN_MARKER = "<!-- BEGIN AGENT-STANDARDS -->"
END_MARKER = "<!-- END AGENT-STANDARDS -->"
BLOCK_RE = re.compile(
    rf"{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}\n?",
    flags=re.DOTALL,
)
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
MIGRATED_LOOSE_RULES = (
    "ci-verification.md",
    "git-pr-hygiene.md",
    "upstream-prs.md",
)


def remove_tree(path: Path) -> None:
    def handle_readonly(func: Any, target: str, _exc: BaseException) -> None:
        os.chmod(target, 0o700)
        func(target)

    if path.exists():
        shutil.rmtree(path, onexc=handle_readonly)


def resolve_claude_dir(home: Path, custom_home: bool) -> Path:
    if not custom_home and os.environ.get("CLAUDE_CONFIG_DIR"):
        return Path(os.environ["CLAUDE_CONFIG_DIR"]).resolve()
    return home / ".claude"


def resolve_codex_dir(home: Path, custom_home: bool) -> Path:
    if not custom_home and os.environ.get("CODEX_HOME"):
        return Path(os.environ["CODEX_HOME"]).resolve()
    return home / ".codex"


def resolve_cache_dir(home: Path) -> Path:
    return home / ".cache" / "agent-standards"


def load_installed_state(cache_dir: Path) -> set[str]:
    state_file = cache_dir / "state.json"
    if not state_file.is_file():
        return set()
    try:
        doc = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(doc, dict):
        return set()
    skills = doc.get("mattpocock_skills")
    if not isinstance(skills, list):
        return set()
    return {s for s in skills if isinstance(s, str)}


def save_installed_state(cache_dir: Path, skill_names: list[str]) -> None:
    state_file = cache_dir / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"mattpocock_skills": sorted(set(skill_names))}
    state_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def ensure_mattpocock_repo(
    cache_dir: Path, override_source: Path | None, check_only: bool
) -> tuple[Path | None, list[str]]:
    if override_source is not None:
        resolved = override_source.resolve()
        if not resolved.is_dir():
            return None, [f"[external] mattpocock source missing: {resolved}"]
        return resolved, []

    env_source = os.environ.get("MATTPOCOCK_SKILLS_SOURCE")
    if env_source:
        resolved = Path(env_source).resolve()
        if not resolved.is_dir():
            return None, [f"[external] MATTPOCOCK_SKILLS_SOURCE missing: {resolved}"]
        return resolved, []

    repo_dir = cache_dir / MATTPOCOCK_PLUGIN_NAME
    if check_only:
        if not (repo_dir / ".git").exists():
            return None, [f"[external] cached mattpocock/skills clone missing: {repo_dir}"]
        return repo_dir, []

    if (repo_dir / ".git").exists():
        subprocess.run(
            ["git", "-C", str(repo_dir), "pull", "--ff-only", "--quiet"],
            capture_output=True,
            timeout=60,
            check=False,
        )
        return repo_dir, []

    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", MATTPOCOCK_REPO_URL, str(repo_dir)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"Failed to clone {MATTPOCOCK_REPO_URL}: {detail}")
    return repo_dir, []


def load_mattpocock_bundle(source_root: Path) -> tuple[dict[str, Any], list[Path]]:
    manifest_path = source_root / ".claude-plugin" / "plugin.json"
    meta: dict[str, Any] = {}
    seen: dict[str, Path] = {}
    if manifest_path.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                meta = raw
                raw_skills = raw.get("skills")
                if isinstance(raw_skills, list):
                    for rel in raw_skills:
                        if isinstance(rel, str):
                            candidate = (source_root / rel).resolve()
                            if (candidate / "SKILL.md").is_file():
                                seen[candidate.name] = candidate
    if not seen:
        for bucket in MATTPOCOCK_FALLBACK_BUCKETS:
            bucket_dir = source_root / "skills" / bucket
            if bucket_dir.is_dir():
                for candidate in sorted(p for p in bucket_dir.iterdir() if p.is_dir()):
                    if (candidate / "SKILL.md").is_file():
                        seen[candidate.name] = candidate
    return meta, [seen[name] for name in sorted(seen)]


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


def sync_tree_inplace(
    src_tree: dict[Path, bytes], dst_tree: dict[Path, bytes], dst_root: Path
) -> None:
    for stale_rel in sorted(dst_tree.keys() - src_tree.keys(), reverse=True):
        stale_file = dst_root / stale_rel
        with contextlib.suppress(OSError):
            stale_file.unlink()
        parent = stale_file.parent
        while parent != dst_root and parent.exists():
            with contextlib.suppress(OSError):
                parent.rmdir()
            parent = parent.parent

    for rel, data in src_tree.items():
        if dst_tree.get(rel) == data:
            continue
        out = dst_root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)


def claude_plugin_enabled(claude_dir: Path, plugin_prefix: str) -> bool:
    settings_path = claude_dir / "settings.json"
    if not settings_path.is_file():
        return False
    try:
        doc = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(doc, dict):
        return False
    enabled_plugins = doc.get("enabledPlugins")
    return isinstance(enabled_plugins, dict) and any(
        k.startswith(f"{plugin_prefix}@") and bool(v) for k, v in enabled_plugins.items()
    )


def codex_plugin_enabled(codex_dir: Path, plugin_prefix: str) -> bool:
    config_path = codex_dir / "config.toml"
    if not config_path.is_file():
        return False
    try:
        doc = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    plugins_cfg = doc.get("plugins")
    if not isinstance(plugins_cfg, dict):
        return False
    return any(
        k.startswith(f"{plugin_prefix}@") and isinstance(v, dict) and bool(v.get("enabled"))
        for k, v in plugins_cfg.items()
    )


def sync_skill_dirs(
    agent: str,
    skills_dst_root: Path,
    skill_dirs: list[Path],
    stale_names: set[str],
    check_only: bool,
) -> list[str]:
    drift: list[str] = []
    active_names = {d.name for d in skill_dirs}
    for stale_name in sorted(stale_names - active_names):
        stale_dir = skills_dst_root / stale_name
        if stale_dir.exists():
            drift.append(f"[{agent}] stale external skill present: {stale_dir}")
            if not check_only:
                remove_tree(stale_dir)

    for skill_dir in skill_dirs:
        dst_dir = skills_dst_root / skill_dir.name
        src_tree = iter_files(skill_dir)
        dst_tree = iter_files(dst_dir)
        if src_tree != dst_tree:
            drift.append(f"[{agent}] skill out of sync: {dst_dir}")
            if not check_only:
                sync_tree_inplace(src_tree, dst_tree, dst_dir)
    return drift


def sync_flat_agent(
    agent: str,
    rule_path: Path,
    skills_dst_root: Path,
    managed_block: str,
    skills_src_root: Path,
    external_skill_dirs: list[Path],
    previous_external_names: set[str],
    skip_external_copies: bool,
    check_only: bool,
) -> list[str]:
    drift: list[str] = []
    existing = (
        rule_path.read_text(encoding="utf-8").replace("\r\n", "\n") if rule_path.exists() else None
    )
    desired_rules = merge_rules(existing, managed_block)
    if existing != desired_rules:
        drift.append(f"[{agent}] rule out of sync: {rule_path}")
        if not check_only:
            rule_path.parent.mkdir(parents=True, exist_ok=True)
            rule_path.write_text(desired_rules, encoding="utf-8", newline="\n")

    local_skill_dirs = sorted(p for p in skills_src_root.iterdir() if p.is_dir())
    drift.extend(sync_skill_dirs(agent, skills_dst_root, local_skill_dirs, set(), check_only))

    known_external = previous_external_names | {d.name for d in external_skill_dirs}
    if skip_external_copies:
        for dup_name in sorted(known_external):
            dup_dir = skills_dst_root / dup_name
            if dup_dir.exists():
                drift.append(f"[{agent}] duplicate external skill alongside plugin: {dup_dir}")
                if not check_only:
                    remove_tree(dup_dir)
    else:
        drift.extend(
            sync_skill_dirs(
                agent, skills_dst_root, external_skill_dirs, previous_external_names, check_only
            )
        )
    return drift


def claude_stop_command(hook_script: Path) -> str:
    posix_path = hook_script.as_posix()
    return f'python "{posix_path}"'


def is_our_claude_hook(handler: Any) -> bool:
    return (
        isinstance(handler, dict)
        and isinstance(handler.get("command"), str)
        and CLAUDE_STOP_SCRIPT in handler["command"]
    )


def strip_claude_stop_groups(stop_groups: list[Any]) -> list[Any]:
    cleaned: list[Any] = []
    for group in stop_groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            cleaned.append(group)
            continue
        kept = [h for h in group["hooks"] if not is_our_claude_hook(h)]
        if kept:
            updated = dict(group)
            updated["hooks"] = kept
            cleaned.append(updated)
    return cleaned


def sync_claude_stop_hook(claude_dir: Path, repo_root: Path, check_only: bool) -> list[str]:
    drift: list[str] = []
    src_script = (repo_root / "scripts" / "stop_prose_gate.py").read_bytes().replace(b"\r\n", b"\n")
    dst_script = claude_dir / "hooks" / CLAUDE_STOP_SCRIPT
    dst_bytes = dst_script.read_bytes().replace(b"\r\n", b"\n") if dst_script.is_file() else b""
    if src_script != dst_bytes:
        drift.append(f"[claude] stop hook script out of sync: {dst_script}")
        if not check_only:
            dst_script.parent.mkdir(parents=True, exist_ok=True)
            dst_script.write_bytes(src_script)

    settings_path = claude_dir / "settings.json"
    raw_settings = (
        settings_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if settings_path.is_file()
        else "{}\n"
    )
    try:
        doc = json.loads(raw_settings)
    except json.JSONDecodeError:
        return drift
    if not isinstance(doc, dict):
        return drift

    plugin_enabled = claude_plugin_enabled(claude_dir, PLUGIN_NAME)

    desired_doc = json.loads(json.dumps(doc))
    hooks_obj = desired_doc.get("hooks")
    if not isinstance(hooks_obj, dict):
        hooks_obj = {}
    stop_list = hooks_obj.get("Stop")
    if not isinstance(stop_list, list):
        stop_list = []

    base_stop = strip_claude_stop_groups(stop_list)
    if not plugin_enabled:
        base_stop.append(
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": claude_stop_command(dst_script),
                        "timeout": 20,
                    }
                ]
            }
        )

    if base_stop:
        hooks_obj["Stop"] = base_stop
    else:
        hooks_obj.pop("Stop", None)

    if hooks_obj:
        desired_doc["hooks"] = hooks_obj
    else:
        desired_doc.pop("hooks", None)

    if desired_doc != doc:
        drift.append(f"[claude] Stop hook config out of sync: {settings_path}")
        if not check_only:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(
                json.dumps(desired_doc, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
    return drift


def uninstall_claude_stop_hook(claude_dir: Path) -> None:
    dst_script = claude_dir / "hooks" / CLAUDE_STOP_SCRIPT
    if dst_script.exists():
        dst_script.unlink()
    settings_path = claude_dir / "settings.json"
    if not settings_path.is_file():
        return
    try:
        doc = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(doc, dict) or not isinstance(doc.get("hooks"), dict):
        return
    hooks_obj = dict(doc["hooks"])
    if isinstance(hooks_obj.get("Stop"), list):
        cleaned = strip_claude_stop_groups(hooks_obj["Stop"])
        if cleaned:
            hooks_obj["Stop"] = cleaned
        else:
            hooks_obj.pop("Stop", None)
    if hooks_obj:
        doc["hooks"] = hooks_obj
    else:
        doc.pop("hooks", None)
    settings_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")


def cleanup_loose_antigravity(
    home: Path,
    skills_src_root: Path,
    external_skill_names: set[str],
    check_only: bool,
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

    loose_rules_dir = home / ".gemini" / "config" / "rules"
    for fname in MIGRATED_LOOSE_RULES:
        dup_rule = loose_rules_dir / fname
        if dup_rule.exists():
            drift.append(f"[antigravity] migrated loose rule present: {dup_rule}")
            if not check_only:
                dup_rule.unlink()

    loose_skills_root = home / ".gemini" / "config" / "skills"
    managed_names = {p.name for p in skills_src_root.iterdir() if p.is_dir()} | external_skill_names
    for skill_name in sorted(managed_names):
        dup_skill = loose_skills_root / skill_name
        if dup_skill.exists():
            drift.append(f"[antigravity] duplicate loose skill: {dup_skill}")
            if not check_only:
                remove_tree(dup_skill)
    return drift


def build_mattpocock_antigravity_tree(
    meta: dict[str, Any], skill_dirs: list[Path]
) -> dict[Path, bytes]:
    author = meta.get("author")
    if not isinstance(author, (str, dict)):
        author = {"name": "Matt Pocock", "url": "https://www.aihero.dev"}
    manifest = {
        "name": MATTPOCOCK_PLUGIN_NAME,
        "displayName": "Matt Pocock Skills",
        "version": str(meta.get("version") or "1.0.0"),
        "description": str(
            meta.get("description")
            or "Matt Pocock's agent skills for engineering, grilling, specs, TDD, and review."
        ),
        "logo": "assets/logo.svg",
        "suggestedPrompts": [
            "Use grill-me to interview me about this plan until design trade-offs are resolved",
            "Break this specification into vertical-slice implementation tickets with to-tickets",
            "Drive this feature or bug fix through red-green-refactor cycles using the tdd skill",
        ],
        "author": author,
        "homepage": str(meta.get("homepage") or "https://github.com/mattpocock/skills"),
        "repository": "https://github.com/mattpocock/skills",
    }
    tree: dict[Path, bytes] = {
        Path("plugin.json"): (json.dumps(manifest, indent=2) + "\n").encode("utf-8"),
        Path("assets/logo.svg"): MATTPOCOCK_LOGO_SVG.encode("utf-8"),
    }
    for skill_dir in skill_dirs:
        for rel, data in iter_files(skill_dir).items():
            tree[Path("skills") / skill_dir.name / rel] = data
    return tree


def sync_antigravity_plugins(
    home: Path,
    repo_root: Path,
    skills_src_root: Path,
    mp_meta: dict[str, Any],
    mp_skill_dirs: list[Path],
    previous_external_names: set[str],
    check_only: bool,
) -> list[str]:
    external_names = previous_external_names | {d.name for d in mp_skill_dirs}
    drift = cleanup_loose_antigravity(home, skills_src_root, external_names, check_only)

    plugins_root = home / ".gemini" / "config" / "plugins"
    plugin_dst = plugins_root / PLUGIN_NAME
    if repo_root.resolve() != plugin_dst.resolve():
        src_tree = iter_files(repo_root)
        dst_tree = iter_files(plugin_dst)
        if src_tree != dst_tree:
            drift.append(f"[antigravity] plugin out of sync: {plugin_dst}")
            if not check_only:
                sync_tree_inplace(src_tree, dst_tree, plugin_dst)

    if mp_skill_dirs:
        mp_dst = plugins_root / MATTPOCOCK_PLUGIN_NAME
        mp_src_tree = build_mattpocock_antigravity_tree(mp_meta, mp_skill_dirs)
        mp_dst_tree = iter_files(mp_dst)
        if mp_src_tree != mp_dst_tree:
            drift.append(f"[antigravity] plugin out of sync: {mp_dst}")
            if not check_only:
                sync_tree_inplace(mp_src_tree, mp_dst_tree, mp_dst)
    return drift


def collect_uninstall_external_names(
    home: Path, cache_dir: Path, override_source: Path | None
) -> set[str]:
    names = load_installed_state(cache_dir)
    candidates = [cache_dir / MATTPOCOCK_PLUGIN_NAME]
    if override_source is not None:
        candidates.append(override_source.resolve())
    env_source = os.environ.get("MATTPOCOCK_SKILLS_SOURCE")
    if env_source:
        candidates.append(Path(env_source).resolve())
    for candidate in candidates:
        if candidate.is_dir():
            _, dirs = load_mattpocock_bundle(candidate)
            names.update(d.name for d in dirs)
    mp_agy_skills = home / ".gemini" / "config" / "plugins" / MATTPOCOCK_PLUGIN_NAME / "skills"
    if mp_agy_skills.is_dir():
        names.update(p.name for p in mp_agy_skills.iterdir() if p.is_dir())
    return names


def uninstall_all(
    home: Path,
    claude_dir: Path,
    codex_dir: Path,
    cache_dir: Path,
    repo_root: Path,
    skills_src_root: Path,
    override_source: Path | None,
    agents: list[str],
) -> None:
    external_names = collect_uninstall_external_names(home, cache_dir, override_source)
    managed_skill_names = {p.name for p in skills_src_root.iterdir() if p.is_dir()} | external_names
    flat_targets = {
        "claude": (claude_dir / "CLAUDE.md", claude_dir / "skills"),
        "codex": (codex_dir / "AGENTS.md", codex_dir / "skills"),
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
            for skill_name in sorted(managed_skill_names):
                dst_dir = skills_dst / skill_name
                if dst_dir.exists():
                    remove_tree(dst_dir)
            if agent == "claude":
                uninstall_claude_stop_hook(claude_dir)
            print(f"[{agent}] removed managed rules, skills, and hooks.")
        elif agent == "antigravity":
            cleanup_loose_antigravity(home, skills_src_root, external_names, check_only=False)
            plugins_root = home / ".gemini" / "config" / "plugins"
            plugin_dst = plugins_root / PLUGIN_NAME
            if plugin_dst.exists() and repo_root.resolve() != plugin_dst.resolve():
                remove_tree(plugin_dst)
            mp_dst = plugins_root / MATTPOCOCK_PLUGIN_NAME
            if mp_dst.exists():
                remove_tree(mp_dst)
            print(f"[antigravity] removed plugins at {plugin_dst} and {mp_dst}.")

    if set(agents) == {"antigravity", "claude", "codex"} and cache_dir.exists():
        remove_tree(cache_dir)


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
        default=None,
        help="Override home directory for testing.",
    )
    parser.add_argument(
        "--mattpocock-source",
        type=Path,
        default=None,
        help="Override local directory for mattpocock/skills instead of cloning from GitHub.",
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
        help="Remove managed rules, skills, hooks, and plugin directories.",
    )
    args = parser.parse_args()

    custom_home = args.home is not None
    home = (args.home or Path.home()).resolve()
    claude_dir = resolve_claude_dir(home, custom_home)
    codex_dir = resolve_codex_dir(home, custom_home)
    cache_dir = resolve_cache_dir(home)

    repo_root = Path(__file__).resolve().parent.parent
    core_rules = (repo_root / "rules" / "AGENTS.md").read_text(encoding="utf-8")
    skills_src_root = repo_root / "skills"
    managed_block = build_managed_block(core_rules)

    if args.uninstall:
        uninstall_all(
            home,
            claude_dir,
            codex_dir,
            cache_dir,
            repo_root,
            skills_src_root,
            args.mattpocock_source,
            args.agents,
        )
        return 0

    previous_external_names = load_installed_state(cache_dir)
    mp_source, all_drift = ensure_mattpocock_repo(
        cache_dir, args.mattpocock_source, check_only=args.check
    )
    mp_meta: dict[str, Any] = {}
    mp_skill_dirs: list[Path] = []
    if mp_source is not None:
        mp_meta, mp_skill_dirs = load_mattpocock_bundle(mp_source)

    flat_targets = {
        "claude": (
            claude_dir / "CLAUDE.md",
            claude_dir / "skills",
            claude_plugin_enabled(claude_dir, MATTPOCOCK_PLUGIN_NAME),
        ),
        "codex": (
            codex_dir / "AGENTS.md",
            codex_dir / "skills",
            codex_plugin_enabled(codex_dir, MATTPOCOCK_PLUGIN_NAME),
        ),
    }
    for agent in args.agents:
        if agent == "antigravity":
            drift = sync_antigravity_plugins(
                home,
                repo_root,
                skills_src_root,
                mp_meta,
                mp_skill_dirs,
                previous_external_names,
                check_only=args.check,
            )
            all_drift.extend(drift)
            if not args.check:
                plugins_root = home / ".gemini/config/plugins"
                print(
                    f"[antigravity] synced plugins -> {plugins_root / PLUGIN_NAME} "
                    f"& {plugins_root / MATTPOCOCK_PLUGIN_NAME}"
                )
        else:
            rule_path, skills_dst, skip_ext = flat_targets[agent]
            drift = sync_flat_agent(
                agent,
                rule_path,
                skills_dst,
                managed_block,
                skills_src_root,
                mp_skill_dirs,
                previous_external_names,
                skip_external_copies=skip_ext,
                check_only=args.check,
            )
            if agent == "claude":
                drift.extend(sync_claude_stop_hook(claude_dir, repo_root, check_only=args.check))
            all_drift.extend(drift)
            if not args.check:
                print(f"[{agent}] synced -> {rule_path} & {skills_dst}")

    if not args.check and mp_skill_dirs:
        save_installed_state(cache_dir, [d.name for d in mp_skill_dirs])

    if args.check:
        if all_drift:
            for item in all_drift:
                print(item)
            return 1
        print("All targets match canonical sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
