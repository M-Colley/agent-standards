#!/usr/bin/env python3
"""Self-validation and regression test suite for agent-standards."""

from __future__ import annotations

import json
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
        for idx, line in enumerate(
            md.read_text(encoding="utf-8").splitlines(), start=1
        ):
            hit = DASH_PUNCT_RE.search(line)
            if hit:
                errors.append(
                    f"{md.relative_to(REPO_ROOT)}:{idx}: contains banned dash {hit.group(0)!r}"
                )
    return errors


def check_stop_hook_behavior() -> list[str]:
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

        res_claude = stop_prose_gate.evaluate_payload(
            {"stop_hook_active": False, "cwd": str(ws)}
        )
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
            errors.append(
                f"Expected continuationActive loop guard {{}}, got: {res_loop_guard}"
            )
    return errors


def check_installer_roundtrip() -> list[str]:
    errors: list[str] = []
    installer = REPO_ROOT / "scripts" / "install.py"
    with tempfile.TemporaryDirectory() as tmp_home:
        home = Path(tmp_home)
        loose = home / ".gemini" / "config" / "rules"
        loose.mkdir(parents=True)
        (loose / "ci-verification.md").write_text("old", encoding="utf-8")

        for extra_args in ([], ["--check"], ["--uninstall"]):
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
    return errors


def main() -> int:
    failures = (
        check_manifests()
        + check_markdown_hygiene()
        + check_stop_hook_behavior()
        + check_installer_roundtrip()
    )
    if failures:
        for item in failures:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    print("All manifest, prose-hygiene, stop-hook, and installer checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
