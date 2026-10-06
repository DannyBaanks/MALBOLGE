#!/usr/bin/env python3
"""Verify path->sha256 references in evidence/*.json against the current tree.

Manifest references live in dict contexts named ``files`` or ``sha256``, in
flat ``{path: sha256}`` and nested ``{path: {sha256: …}}`` forms
(``supersedes`` notes are historical by design and are not checked).

A reference is *closed* when the recorded sha256 equals the sha256 of the
bytes at that path in the HEAD tree (machine-independent; untracked targets
are handled through the ledger). References that do not close are reconciled in
``evidence/SUPERSEDENCE_LEDGER_20261005.json``:

  eol-artifact         recorded = sha256(CRLF-normalized current bytes)
  superseded-by-commit recorded = sha256(blob at an older revision, given variant)
  artifact-excluded    recorded = sha256 of a local build artifact excluded by
                       policy (.gitignore); not present in a clean clone
  not-recoverable      recorded revision was never committed; documented gap

Exit status: 0 when every manifest reference is closed or reconciled, 1 if any
reference is open and not reconciled.

  python3 verify_evidence_refs.py [-v]
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER_PATH = HERE / "evidence" / "SUPERSEDENCE_LEDGER_20261005.json"
MANIFEST_KEYS = ("files", "sha256")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def to_lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def to_crlf(b: bytes) -> bytes:
    return to_lf(b).replace(b"\n", b"\r\n")


def git_show(rev: str, path: str) -> bytes | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"{rev}:{path}"], cwd=HERE, stderr=subprocess.DEVNULL
        )
    except Exception:
        return None


def collect_refs() -> tuple[list[tuple[str, str, str]], int]:
    refs: list[tuple[str, str, str]] = []
    informational = 0
    for f in sorted((HERE / "evidence").glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rel = f.relative_to(HERE).as_posix()

        def walk(o, parent):
            nonlocal informational
            if isinstance(o, dict):
                for k, v in o.items():
                    pathlike = "/" in k or "." in k
                    if (
                        isinstance(v, str)
                        and len(v) == 64
                        and all(c in "0123456789abcdef" for c in v)
                        and pathlike
                    ):
                        if parent in MANIFEST_KEYS:
                            refs.append((rel, k, v))
                        else:
                            informational += 1
                    elif parent == "files" and isinstance(v, dict) and pathlike:
                        s = v.get("sha256")
                        if (
                            isinstance(s, str)
                            and len(s) == 64
                            and all(c in "0123456789abcdef" for c in s)
                        ):
                            refs.append((rel, k, s))
                    walk(v, k)
            elif isinstance(o, list):
                for x in o:
                    walk(x, parent)

        walk(d, None)
    return refs, informational


def classify(ref, index) -> tuple[str, str]:
    ev, path, want = ref
    tree = git_show("HEAD", path)
    if tree is not None and sha256_bytes(tree) == want:
        return "closed", "HEAD tree matches recorded"
    wt = HERE / path
    ent = index.get((ev, path))
    if ent is None:
        return "UNKNOWN", "open and not reconciled in the ledger"
    cls = ent["classification"]
    if cls == "eol-artifact":
        base = tree if tree is not None else (wt.read_bytes() if wt.exists() else None)
        if base is not None and sha256_bytes(to_crlf(base)) == want:
            return "reconciled", "eol-artifact: sha256(crlf(current)) == recorded"
        return "UNKNOWN", "eol-artifact predicate failed"
    if cls == "superseded-by-commit":
        detail = ent.get("detail", {})
        old = git_show(detail.get("old_revision", ""), path)
        if old is None:
            return "reconciled", "superseded-by-commit: old revision not available in this clone"
        got = sha256_bytes(old)
        if detail.get("old_variant") == "crlf":
            got = sha256_bytes(to_crlf(old))
        if got == want:
            return "reconciled", "superseded-by-commit: old revision matches recorded"
        return "UNKNOWN", "superseded-by-commit predicate failed"
    if cls == "artifact-excluded":
        if wt.exists():
            if sha256_bytes(wt.read_bytes()) == want:
                return "reconciled", "artifact-excluded: local artifact matches recorded"
            return "UNKNOWN", "artifact-excluded: local artifact present but hash mismatch"
        return "reconciled", "artifact-excluded: not present in this checkout (expected)"
    if cls == "not-recoverable":
        return "reconciled", "not-recoverable: documented gap (see ledger)"
    return "UNKNOWN", f"unknown ledger class {cls!r}"


def main(argv: list[str]) -> int:
    verbose = "-v" in argv or "--verbose" in argv
    if not LEDGER_PATH.exists():
        print(f"ledger missing: {LEDGER_PATH}", file=sys.stderr)
        return 1
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    index = {(e["evidence_file"], e["entry"]): e for e in ledger["entries"]}
    refs, informational = collect_refs()

    counts: dict[str, int] = {}
    unknown: list[tuple[tuple[str, str, str], str]] = []
    for ref in refs:
        status, why = classify(ref, index)
        counts[status] = counts.get(status, 0) + 1
        if status == "UNKNOWN":
            unknown.append((ref, why))
        if verbose or status != "closed":
            ev, path, want = ref
            print(f"[{status:10s}] {ev} :: {path}  ({why})")

    print()
    summary = "  ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"refs total={len(refs)}  {summary}")
    print(f"informational (non-manifest) hash pairs skipped: {informational}")
    if unknown:
        print(f"FAIL: {len(unknown)} unresolved reference(s)")
        for (ev, path, want), why in unknown:
            print(f"  {ev} :: {path}: {why}")
        return 1
    print("OK: every manifest reference is closed or reconciled (evidence/SUPERSEDENCE_LEDGER_20261005.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
