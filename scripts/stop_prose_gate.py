#!/usr/bin/env python3
"""Cross-agent Stop hook (Antigravity and Claude Code) enforcing manuscript prose and mechcheck gates."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git",
    "node_modules",
    "build",
    "dist",
    "out",
    "venv",
    ".venv",
    "__pycache__",
    "fixtures",
    "demo",
}
SKIP_ENV_RE = re.compile(
    r"\\begin\{(verbatim|lstlisting|minted|tabular\*?|tabularx|longtable|thebibliography|equation\*?|align\*?|gather\*?|tikzpicture)\}"
    r".*?\\end\{\1\}",
    flags=re.DOTALL,
)
COMMENT_RE = re.compile(r"(?<!\\)%.*$", flags=re.MULTILINE)
INLINE_CODE_MATH_RE = re.compile(
    r"(\$\$.*?\$\$|\$[^$\n]+\$|\\\[.*?\\\]|\\\(.*?\\\)"
    r"|\\(?:url|href|texttt|verb|label|autoref|ref|cite[a-zA-Z]*|includegraphics|input|include)\*?(?:\[[^\]]*\])?\{[^}]*\})",
    flags=re.DOTALL,
)
RAW_REF_RE = re.compile(r"(?<![a-zA-Z\\])\\ref\{([^}]+)\}")
PROSE_DASH_RE = re.compile(r"(\u2014|\u2013|---|(?<=\s)--(?=\s)|(?<=\s)-(?=\s))")
BANNED_PHRASES = (
    "in order to",
    "it is important to note",
    "we would like to",
    "moreover",
    "we state this rather than obscure it",
    "game-changing",
    "game changing",
    "at scale",
    "headline result",
    "shippable",
    "free lunch",
    "anonymous knob",
)
BANNED_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in BANNED_PHRASES) + r")\b",
    flags=re.IGNORECASE,
)


def emit(obj: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()
    return 0


def discover_modified_tex(roots: list[Path]) -> list[Path]:
    found: dict[Path, None] = {}
    cutoff = time.time() - 900.0
    for raw_root in roots:
        if not raw_root.exists():
            continue
        root = raw_root if raw_root.is_dir() else raw_root.parent
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain", "-uall"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            proc = None

        if proc and proc.returncode == 0:
            top = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            repo_base = (
                Path(top.stdout.strip())
                if top.returncode == 0 and top.stdout.strip()
                else root
            )
            for line in proc.stdout.splitlines():
                if len(line) < 4:
                    continue
                status, rel_raw = line[:2], line[3:].strip().strip('"')
                if "D" in status:
                    continue
                if " -> " in rel_raw:
                    rel_raw = rel_raw.split(" -> ", 1)[1].strip('"')
                candidate = (repo_base / rel_raw).resolve()
                if (
                    candidate.suffix.lower() == ".tex"
                    and candidate.is_file()
                    and not (set(candidate.parts) & SKIP_DIRS)
                ):
                    found[candidate] = None
        else:
            for candidate in root.rglob("*.tex"):
                if set(candidate.parts) & SKIP_DIRS:
                    continue
                try:
                    if candidate.stat().st_mtime >= cutoff:
                        found[candidate.resolve()] = None
                except OSError:
                    continue
    return sorted(found)


def check_tex_file(path: Path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    issues: list[str] = []
    uncommented = COMMENT_RE.sub("", raw)
    stripped_envs = SKIP_ENV_RE.sub("", uncommented)

    for match in RAW_REF_RE.finditer(stripped_envs):
        issues.append(
            f"{path.name}: use \\autoref{{{match.group(1)}}} instead of \\ref{{{match.group(1)}}}"
        )

    prose = INLINE_CODE_MATH_RE.sub(" ", stripped_envs)
    for idx, line in enumerate(prose.splitlines(), start=1):
        dash_hit = PROSE_DASH_RE.search(line)
        if dash_hit:
            issues.append(
                f"{path.name}:{idx}: prose dash {dash_hit.group(0)!r} prohibited"
            )
        phrase_hit = BANNED_RE.search(line)
        if phrase_hit:
            issues.append(
                f"{path.name}:{idx}: banned phrase {phrase_hit.group(0)!r} prohibited"
            )
    return issues


def run_mechcheck(tex_files: list[Path]) -> list[str]:
    if importlib.util.find_spec("mechcheck") is None:
        return []
    checked_dirs: set[Path] = set()
    errors: list[str] = []
    for tex in tex_files:
        parent = tex.parent
        if parent in checked_dirs:
            continue
        checked_dirs.add(parent)
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "mechcheck", "check", str(parent), "--offline"],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            lines = [
                ln.strip()
                for ln in (proc.stdout + "\n" + proc.stderr).splitlines()
                if ln.strip()
                and ("error" in ln.lower() or re.match(r"^[A-Z]{3}\d{3}", ln.strip()))
            ]
            errors.extend(lines[:8] or [f"mechcheck failed in {parent.name}"])
    return errors


def evaluate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    is_claude = "stop_hook_active" in payload
    if payload.get("continuationActive") or payload.get("stop_hook_active"):
        return {}
    if (
        not is_claude
        and payload.get("terminationReason", "NO_TOOL_CALL") != "NO_TOOL_CALL"
    ):
        return {}

    raw_paths: list[str] = list(payload.get("workspacePaths") or [])
    if payload.get("cwd"):
        raw_paths.append(str(payload["cwd"]))
    roots = [Path(p) for p in raw_paths if p]
    if not roots:
        return {}

    tex_files = discover_modified_tex(roots)
    if not tex_files:
        return {}

    findings: list[str] = []
    for tex in tex_files:
        findings.extend(check_tex_file(tex))
    findings.extend(run_mechcheck(tex_files))

    if not findings:
        return {}

    summary = "; ".join(findings[:10])
    if len(findings) > 10:
        summary += f" (+{len(findings) - 10} more)"
    return {
        "decision": "block" if is_claude else "continue",
        "reason": f"Manuscript verification failed ({summary}). Run `python -m mechcheck fix .` and fix remaining violations before concluding.",
    }


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        return emit({})
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return emit({})
    if not isinstance(payload, dict):
        return emit({})
    return emit(evaluate_payload(payload))


if __name__ == "__main__":
    sys.exit(main())
