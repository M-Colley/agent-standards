#!/usr/bin/env python3
"""Cross-agent Stop hook (Antigravity and Claude Code) enforcing manuscript prose and mechcheck gates."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Iterator
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
# Directory levels the non-git fallback scans below a workspace root. Bounds Stop latency in
# large non-repository folders such as a home directory.
MAX_SCAN_DEPTH = 4
# mechcheck's config names and main-document test (mechcheck.config, mechcheck.texsource).
MECHCHECK_CONFIGS = ("mechcheck.yaml", "mechcheck.yml", ".mechcheck.yaml", ".mechcheck.yml")
DOCUMENTCLASS_RE = re.compile(
    r"^[^%\n]*\\documentclass\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", flags=re.MULTILINE
)
MECHCHECK_EXIT_FINDINGS = 1  # 0 clean, 2 usage error such as no main document, 3 internal error
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


def iter_tex_files(root: Path) -> Iterator[Path]:
    """Yield .tex files under root, pruning SKIP_DIRS and stopping MAX_SCAN_DEPTH levels down."""
    base_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if len(current.parts) - base_depth >= MAX_SCAN_DEPTH:
            dirnames.clear()
        else:
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.lower().endswith(".tex"):
                yield current / name


def discover_modified_tex(roots: list[Path]) -> list[Path]:
    found: dict[Path, None] = {}
    cutoff = time.time() - 900.0
    for raw_root in roots:
        if not raw_root.exists():
            continue
        root = raw_root if raw_root.is_dir() else raw_root.parent
        try:
            # -z emits raw UTF-8 paths; without it git quotes non-ASCII names as octal escapes.
            proc = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain", "-z", "-uall"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            proc = None

        if proc and proc.returncode == 0:
            top = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            # Git prints paths in UTF-8; os.fsdecode decodes them on every platform.
            top_dir = os.fsdecode(top.stdout).strip()
            repo_base = Path(top_dir) if top.returncode == 0 and top_dir else root
            skip_source = False
            for record in os.fsdecode(proc.stdout).split("\0"):
                if skip_source:  # source path that follows a rename or copy record
                    skip_source = False
                    continue
                if len(record) < 4:
                    continue
                status, rel_raw = record[:2], record[3:]
                skip_source = "R" in status or "C" in status
                if "D" in status:
                    continue
                candidate = (repo_base / rel_raw).resolve()
                if (
                    candidate.suffix.lower() == ".tex"
                    and candidate.is_file()
                    and not (set(candidate.parts) & SKIP_DIRS)
                ):
                    found[candidate] = None
        else:
            for candidate in iter_tex_files(root):
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
            issues.append(f"{path.name}:{idx}: prose dash {dash_hit.group(0)!r} prohibited")
        phrase_hit = BANNED_RE.search(line)
        if phrase_hit:
            issues.append(f"{path.name}:{idx}: banned phrase {phrase_hit.group(0)!r} prohibited")
    return issues


def is_project_root(folder: Path) -> bool:
    """True if folder holds a mechcheck config or a main document by mechcheck's criteria."""
    if any((folder / name).is_file() for name in MECHCHECK_CONFIGS):
        return True
    try:
        entries = list(folder.iterdir())
    except OSError:
        return False
    for tex in entries:
        if tex.suffix.lower() != ".tex" or not tex.is_file():
            continue
        try:
            head = tex.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "\\documentclass" not in head or "\\begin{document}" not in head:
            continue
        cls = DOCUMENTCLASS_RE.search(head)
        if not (cls and cls.group(1).strip() in ("standalone", "subfiles")):
            return True
    return False


def find_project_root(tex: Path, roots: list[Path]) -> Path | None:
    """Nearest folder from tex up to its git or workspace root that holds a mechcheck project."""
    chain = [tex.parent, *tex.parent.parents]
    boundary = next((d for d in chain if (d / ".git").exists()), None)
    if boundary is None:
        boundary = next((d for d in chain if d in roots), tex.parent)
    for folder in chain:
        if is_project_root(folder):
            return folder
        if folder == boundary:
            break
    return None


def run_mechcheck(tex_files: list[Path], roots: list[Path]) -> list[str]:
    """Run mechcheck once per project that contains a modified .tex file."""
    if importlib.util.find_spec("mechcheck") is None:
        return []
    resolved_roots = [r.resolve() for r in roots]
    checked_dirs: set[Path] = set()
    errors: list[str] = []
    for tex in tex_files:
        project = find_project_root(tex, resolved_roots)
        if project is None or project in checked_dirs:
            continue
        checked_dirs.add(project)
        try:
            # mechcheck reconfigures its output streams to UTF-8.
            proc = subprocess.run(
                [sys.executable, "-m", "mechcheck", "check", str(project), "--offline"],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=12,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode == MECHCHECK_EXIT_FINDINGS:
            lines = [
                ln.strip()
                for ln in (proc.stdout + "\n" + proc.stderr).splitlines()
                if ln.strip() and ("error" in ln.lower() or re.match(r"^[A-Z]{3}\d{3}", ln.strip()))
            ]
            errors.extend(lines[:8] or [f"mechcheck failed in {project.name}"])
    return errors


def evaluate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    is_claude = "stop_hook_active" in payload
    if payload.get("continuationActive") or payload.get("stop_hook_active"):
        return {}
    if not is_claude and payload.get("terminationReason", "NO_TOOL_CALL") != "NO_TOOL_CALL":
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
    findings.extend(run_mechcheck(tex_files, roots))

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
    # Read bytes: hosts send UTF-8 JSON, and text-mode stdin uses the ANSI code page on Windows.
    raw = sys.stdin.buffer.read()
    if not raw.strip():
        return emit({})
    try:
        payload = json.loads(raw)
    except ValueError:  # invalid JSON or invalid UTF-8
        return emit({})
    if not isinstance(payload, dict):
        return emit({})
    return emit(evaluate_payload(payload))


if __name__ == "__main__":
    sys.exit(main())
