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
MAIN_DOC = (
    "\\documentclass{article}\n\\begin{document}\nWe evaluate the prototype.\n\\end{document}\n"
)


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


def run_git(repo: Path, *args: str) -> None:
    """Run git in repo with a throwaway identity for fixture commits."""
    base = ["git", "-C", str(repo), "-c", "user.name=ci", "-c", "user.email=ci@example.invalid"]
    subprocess.run([*base, *args], capture_output=True, check=True)


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
        init_repo_with_tex(clean, "paper.tex", MAIN_DOC)
        env = {**os.environ, "PYTHONPATH": str(stub.parent)}
        proc = run_hook({"stop_hook_active": False, "cwd": str(clean)}, env=env)
        if b"MCK001" not in proc.stdout:
            errors.append(f"Expected stub mechcheck to block, got: {proc.stdout!r} {proc.stderr!r}")
    return errors


def check_hook_staged_rename() -> list[str]:
    """A staged rename must report the new path, which git -z lists before the source path."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        init_repo_with_tex(repo, "old.tex", "We evaluate the prototype.\n")
        for args in (
            ["add", "old.tex"],
            ["commit", "-q", "-m", "init"],
            ["mv", "old.tex", "new.tex"],
        ):
            run_git(repo, *args)
        (repo / "new.tex").write_text("In order to test this.\n", encoding="utf-8")
        found = sorted(p.name for p in stop_prose_gate.discover_modified_tex([repo]))
    if found != ["new.tex"]:
        return [f"Expected the staged rename to report new.tex, got: {found}"]
    return []


def check_hook_mechcheck_project_root() -> list[str]:
    """mechcheck must run from the main document's folder and skip files outside any project."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        # Stub with mechcheck's exit codes: 2 without a main document, 1 for findings.
        stub = base / "stub" / "mechcheck"
        stub.mkdir(parents=True)
        (stub / "__init__.py").write_text("", encoding="utf-8")
        (stub / "__main__.py").write_text(
            "import sys\n"
            "from pathlib import Path\n"
            "root = Path(sys.argv[2])\n"
            "if not (root / 'main.tex').is_file():\n"
            "    sys.exit(2)\n"
            "print(f'MCK001 error: checked {root.name}')\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        env = {**os.environ, "PYTHONPATH": str(stub.parent)}

        paper = base / "paper"
        init_repo_with_tex(paper, "sections/intro.tex", "We evaluate it.\n")
        (paper / "main.tex").write_text(MAIN_DOC, encoding="utf-8")
        run_git(paper, "add", "-A")
        run_git(paper, "commit", "-q", "-m", "init")
        (paper / "sections" / "intro.tex").write_text("We evaluate it twice.\n", encoding="utf-8")
        proc = run_hook({"stop_hook_active": False, "cwd": str(paper)}, env=env)
        if b"checked paper" not in proc.stdout:
            errors.append(f"Expected mechcheck in paper/, got: {proc.stdout!r} {proc.stderr!r}")

        notes = base / "notes"
        init_repo_with_tex(notes, "fragment.tex", "We list open questions.\n")
        proc = run_hook({"stop_hook_active": False, "cwd": str(notes)}, env=env)
        if proc.stdout.strip() != b"{}":
            errors.append(
                f"Expected no mechcheck run without a main document, got: {proc.stdout!r}"
            )
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


def build_mattpocock_fixture(root: Path) -> Path:
    mp = root / "mattpocock-fixture"
    manifest = mp / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "name": "mattpocock-skills",
                "version": "1.3.2",
                "description": "Fixture engineering and productivity skills.",
                "skills": [
                    "./skills/engineering/tdd",
                    "./skills/productivity/grill-me",
                ],
            }
        ),
        encoding="utf-8",
    )
    for rel, name in (
        ("skills/engineering/tdd", "tdd"),
        ("skills/productivity/grill-me", "grill-me"),
        ("skills/in-progress/draft-skill", "draft-skill"),
    ):
        skill_dir = mp / rel
        (skill_dir / "agents").mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Fixture {name}.\n---\n",
            encoding="utf-8",
        )
        (skill_dir / "agents" / "openai.yaml").write_text(
            f'interface:\n  display_name: "{name}"\n',
            encoding="utf-8",
        )
    return mp


def check_installer_roundtrip() -> list[str]:
    errors: list[str] = []
    installer = REPO_ROOT / "scripts" / "install.py"
    with tempfile.TemporaryDirectory() as tmp_home:
        home = Path(tmp_home)
        mp_fixture = build_mattpocock_fixture(home)
        base_cmd = [
            sys.executable,
            str(installer),
            "--home",
            str(home),
            "--mattpocock-source",
            str(mp_fixture),
        ]
        loose = home / ".gemini" / "config" / "rules"
        loose.mkdir(parents=True)
        (loose / "ci-verification.md").write_text("old", encoding="utf-8")
        claude_settings = home / ".claude" / "settings.json"
        claude_settings.parent.mkdir(parents=True)
        claude_settings.write_text('{"skipWorkflowUsageWarning": true}\n', encoding="utf-8")

        p_install = subprocess.run(base_cmd, capture_output=True, text=True, check=False)
        if p_install.returncode != 0:
            errors.append(f"install.py failed: {p_install.stdout} {p_install.stderr}")

        mp_agy = home / ".gemini" / "config" / "plugins" / "mattpocock-skills"
        for expected in (
            mp_agy / "plugin.json",
            mp_agy / "assets" / "logo.svg",
            mp_agy / "skills" / "tdd" / "SKILL.md",
            mp_agy / "skills" / "grill-me" / "SKILL.md",
            home / ".claude" / "skills" / "tdd" / "SKILL.md",
            home / ".codex" / "skills" / "tdd" / "agents" / "openai.yaml",
        ):
            if not expected.is_file():
                errors.append(f"Expected installed companion skill file: {expected}")
        if (mp_agy / "skills" / "draft-skill").exists() or (
            home / ".claude" / "skills" / "draft-skill"
        ).exists():
            errors.append("Unpromoted in-progress skill must not be installed.")

        installed_settings = json.loads(claude_settings.read_text(encoding="utf-8"))
        if not installed_settings.get("hooks", {}).get("Stop"):
            errors.append("Expected Claude settings.json to register Stop hook.")

        p_check = subprocess.run(
            [*base_cmd, "--check"], capture_output=True, text=True, check=False
        )
        if p_check.returncode != 0:
            errors.append(f"install.py --check failed: {p_check.stdout} {p_check.stderr}")

        # Verify native plugin deduplication in Claude and Codex.
        installed_settings["enabledPlugins"] = {"mattpocock-skills@claude-plugins-official": True}
        claude_settings.write_text(json.dumps(installed_settings) + "\n", encoding="utf-8")
        codex_cfg = home / ".codex" / "config.toml"
        codex_cfg.write_text('[plugins."mattpocock-skills@mattpocock"]\nenabled = true\n', "utf-8")
        p_dedup = subprocess.run(base_cmd, capture_output=True, text=True, check=False)
        if p_dedup.returncode != 0:
            errors.append(f"install.py dedup failed: {p_dedup.stdout} {p_dedup.stderr}")
        if (home / ".claude" / "skills" / "tdd").exists() or (
            home / ".codex" / "skills" / "tdd"
        ).exists():
            errors.append(
                "Expected flat mattpocock skills to deduplicate when native plugin is on."
            )
        if not (home / ".claude" / "skills" / "hci-paper-writing" / "SKILL.md").is_file():
            errors.append("Expected hci-paper-writing to remain after mattpocock deduplication.")

        p_uninstall = subprocess.run(
            [*base_cmd, "--uninstall"], capture_output=True, text=True, check=False
        )
        if p_uninstall.returncode != 0:
            errors.append(
                f"install.py --uninstall failed: {p_uninstall.stdout} {p_uninstall.stderr}"
            )
        if mp_agy.exists():
            errors.append("Expected Antigravity mattpocock-skills plugin removed on uninstall.")
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
        + check_hook_staged_rename()
        + check_hook_mechcheck_project_root()
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
