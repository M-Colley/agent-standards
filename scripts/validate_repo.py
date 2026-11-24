#!/usr/bin/env python3
"""Self-validation and regression test suite for agent-standards."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import stop_prose_gate  # noqa: E402

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DASH_PUNCT_RE = re.compile(r"(\u2014|\u2013| - )")


def check_manifests() -> list[str]:
    errors: list[str] = []
    manifests = {
        "antigravity": REPO_ROOT / ".antigravity-plugin" / "plugin.json",
        "claude": REPO_ROOT / ".claude-plugin" / "plugin.json",
        "codex": REPO_ROOT / ".codex-plugin" / "plugin.json",
    }
    versions: set[str] = set()
    for label, path in manifests.items():
        if not path.is_file():
            errors.append(f"Missing {label} manifest: {path}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data.get("name", "")
        if not KEBAB_RE.match(name):
            errors.append(f"{label} manifest invalid kebab-case name: {name!r}")
        versions.add(str(data.get("version", "")))
        if label == "antigravity":
            logo = REPO_ROOT / data.get("logo", "")
            if not logo.is_file():
                errors.append(f"Antigravity logo missing: {logo}")
            prompts = data.get("suggestedPrompts", [])
            if not (1 <= len(prompts) <= 3):
                errors.append("Antigravity suggestedPrompts must have 1 to 3 items.")
    if len(versions) != 1:
        errors.append(f"Manifest version mismatch across providers: {sorted(versions)}")

    marketplace_path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.is_file():
        errors.append(f"Missing Claude marketplace manifest: {marketplace_path}")
    else:
        mkt = json.loads(marketplace_path.read_text(encoding="utf-8"))
        plugins = mkt.get("plugins", [])
        if not plugins or plugins[0].get("name") != "agent-standards":
            errors.append("Invalid .claude-plugin/marketplace.json plugins entry.")

    hooks_path = REPO_ROOT / "hooks.json"
    hooks_data = json.loads(hooks_path.read_text(encoding="utf-8"))
    if "manuscript-prose-gate" not in hooks_data:
        errors.append("hooks.json missing 'manuscript-prose-gate'.")

    for skill_dir in sorted((REPO_ROOT / "skills").iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"Missing SKILL.md in {skill_dir}")
            continue
        text = skill_md.read_text(encoding="utf-8")
        name_match = re.search(r"^name:\s*(\S+)\s*$", text, flags=re.MULTILINE)
        if not name_match or name_match.group(1) != skill_dir.name:
            errors.append(f"Skill name mismatch in {skill_md}")
    return errors


def check_markdown_hygiene() -> list[str]:
    errors: list[str] = []
    for md in sorted(REPO_ROOT.rglob("*.md")):
        for idx, line in enumerate(md.read_text(encoding="utf-8").splitlines(), start=1):
            hit = DASH_PUNCT_RE.search(line)
            if hit:
                errors.append(
                    f"{md.relative_to(REPO_ROOT)}:{idx}: contains banned dash {hit.group(0)!r}"
                )
    return errors


def check_hooks_behavior() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        clean_tex = ws / "paper.tex"
        clean_tex.write_text(
            "\\section{Introduction}\\label{sec:intro}\n"
            "We evaluate the prototype (N=32) as shown in \\autoref{sec:intro}.\n",
            encoding="utf-8",
        )
        res_clean = stop_prose_gate.evaluate_payload(
            {"terminationReason": "NO_TOOL_CALL", "workspacePaths": [str(ws)]}
        )
        if res_clean != {}:
            errors.append(f"Expected clean .tex to pass, got: {res_clean}")

        bad_tex = ws / "paper.tex"
        bad_tex.write_text(
            "In order to test this \u2014 see \\ref{sec:intro}.\n",
            encoding="utf-8",
        )
        res_agy = stop_prose_gate.evaluate_payload(
            {"terminationReason": "NO_TOOL_CALL", "workspacePaths": [str(ws)]}
        )
        if res_agy.get("decision") != "continue":
            errors.append(f"Expected Antigravity Stop gate 'continue', got: {res_agy}")

        res_claude = stop_prose_gate.evaluate_payload({"stop_hook_active": False, "cwd": str(ws)})
        if res_claude.get("decision") != "block":
            errors.append(f"Expected Claude Stop gate 'block', got: {res_claude}")

        res_loop_guard = stop_prose_gate.evaluate_payload(
            {
                "terminationReason": "NO_TOOL_CALL",
                "continuationActive": True,
                "workspacePaths": [str(ws)],
            }
        )
        if res_loop_guard != {}:
            errors.append(f"Expected continuationActive loop guard {{}}, got: {res_loop_guard}")

        empty_claude_dir = ws / "empty_claude"
        empty_claude_dir.mkdir()
        env = dict(**os.environ, CLAUDE_CONFIG_DIR=str(empty_claude_dir))
        start_script = REPO_ROOT / "scripts" / "claude_session_start.py"
        p_main = subprocess.run(
            [sys.executable, str(start_script)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if p_main.returncode != 0 or "Global Operating Rules" not in p_main.stdout:
            errors.append("Expected claude_session_start.py to emit rules.")

        p_sub = subprocess.run(
            [sys.executable, str(start_script), "--subagent"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        sub_json = json.loads(p_sub.stdout or "{}")
        if sub_json.get("hookSpecificOutput", {}).get("hookEventName") != "SubagentStart":
            errors.append("Expected SubagentStart JSON output from claude_session_start.py.")
    return errors


def init_repo_with_tex(repo: Path, rel_tex: str, text: str) -> None:
    """Create a git repository containing one untracked .tex file."""
    subprocess.run(["git", "init", "-q", str(repo)], capture_output=True, check=True)
    tex = repo / rel_tex
    tex.parent.mkdir(parents=True, exist_ok=True)
    tex.write_text(text, encoding="utf-8")


def run_hook(
    payload: dict[str, object], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Pipe a payload to the hook as raw UTF-8 JSON, as Claude Code and Antigravity do."""
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stop_prose_gate.py")],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        env=env,
        check=False,
    )


def check_hook_unicode_paths() -> list[str]:
    """Non-ASCII paths and UTF-8 mechcheck output must not bypass the Stop gate."""
    errors: list[str] = []
    bad = "In order to test this \u2014 see \\ref{sec:intro}.\n"
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        repos = {
            "non-ASCII repository": (base / "J\u00fcrgen", "paper.tex"),
            "non-ASCII file name": (base / "names", "\u00dcbersicht.tex"),
            "non-ASCII subdirectory": (base / "subdirs", "Kapitel_\u00e4/intro.tex"),
        }
        for label, (repo, rel_tex) in repos.items():
            init_repo_with_tex(repo, rel_tex, bad)
            res = stop_prose_gate.evaluate_payload({"stop_hook_active": False, "cwd": str(repo)})
            if res.get("decision") != "block":
                errors.append(f"Expected 'block' for {label}, got: {res}")

        proc = run_hook({"stop_hook_active": False, "cwd": str(base / "J\u00fcrgen")})
        if b'"decision": "block"' not in proc.stdout:
            errors.append(f"Expected 'block' for UTF-8 stdin, got: {proc.stdout!r} {proc.stderr!r}")

        # The mechcheck CLI reconfigures stdout to UTF-8; this stub does the same.
        stub = base / "stub" / "mechcheck"
        stub.mkdir(parents=True)
        (stub / "__init__.py").write_text("", encoding="utf-8")
        (stub / "__main__.py").write_text(
            "import sys\n"
            "sys.stdout.reconfigure(encoding='utf-8')\n"
            "print('MCK001 error: stray \\u201d quote')\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        clean = base / "clean"
        init_repo_with_tex(clean, "paper.tex", "We evaluate the prototype.\n")
        env = {**os.environ, "PYTHONPATH": str(stub.parent)}
        proc = run_hook({"stop_hook_active": False, "cwd": str(clean)}, env=env)
        if b"MCK001" not in proc.stdout:
            errors.append(f"Expected stub mechcheck to block, got: {proc.stdout!r} {proc.stderr!r}")
    return errors


def check_fallback_scan_bounds() -> list[str]:
    """Non-git fallback must prune SKIP_DIRS and stop MAX_SCAN_DEPTH levels below the root."""
    depth = stop_prose_gate.MAX_SCAN_DEPTH
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for tex in (
            root.joinpath(*["d"] * depth, "within.tex"),
            root.joinpath(*["d"] * (depth + 1), "beyond.tex"),
            root / "node_modules" / "vendored.tex",
        ):
            tex.parent.mkdir(parents=True, exist_ok=True)
            tex.write_text("x\n", encoding="utf-8")
        found = sorted(p.name for p in stop_prose_gate.discover_modified_tex([root]))
    if found != ["within.tex"]:
        return [f"Expected the non-git scan to find only within.tex, got: {found}"]
    return []


def check_installer_roundtrip() -> list[str]:
    errors: list[str] = []
    installer = REPO_ROOT / "scripts" / "install.py"
    with tempfile.TemporaryDirectory() as tmp_home:
        home = Path(tmp_home)
        loose = home / ".gemini" / "config" / "rules"
        loose.mkdir(parents=True)
        (loose / "ci-verification.md").write_text("old", encoding="utf-8")
        claude_settings = home / ".claude" / "settings.json"
        claude_settings.parent.mkdir(parents=True)
        claude_settings.write_text('{"skipWorkflowUsageWarning": true}\n', encoding="utf-8")

        p_install = subprocess.run(
            [sys.executable, str(installer), "--home", str(home)],
            capture_output=True,
            text=True,
            check=False,
        )
        if p_install.returncode != 0:
            errors.append(f"install.py failed: {p_install.stdout} {p_install.stderr}")

        installed_settings = json.loads(claude_settings.read_text(encoding="utf-8"))
        if not installed_settings.get("hooks", {}).get("Stop"):
            errors.append("Expected Claude settings.json to register Stop hook.")

        for extra_args in (["--check"], ["--uninstall"]):
            proc = subprocess.run(
                [sys.executable, str(installer), "--home", str(home), *extra_args],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                errors.append(
                    f"install.py {' '.join(extra_args)} failed: {proc.stdout} {proc.stderr}"
                )
        if (loose / "ci-verification.md").exists():
            errors.append("Expected migrated loose rule to be cleaned up.")
        uninstalled_settings = json.loads(claude_settings.read_text(encoding="utf-8"))
        if "hooks" in uninstalled_settings or not uninstalled_settings.get(
            "skipWorkflowUsageWarning"
        ):
            errors.append("Expected clean Claude settings.json after uninstall.")
    return errors


def main() -> int:
    failures = (
        check_manifests()
        + check_markdown_hygiene()
        + check_hooks_behavior()
        + check_hook_unicode_paths()
        + check_fallback_scan_bounds()
        + check_installer_roundtrip()
    )
    if failures:
        for item in failures:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    print("All manifest, prose-hygiene, hook, and installer checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
