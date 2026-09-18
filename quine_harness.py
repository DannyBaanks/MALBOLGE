"""Reproduce and seal a Classic Malbolge quine run.

This harness records only deterministic metadata by default.  It does not
promote the result to an E11--E19 semantic claim: the witness is Classic E10.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import malbolge


FORMAT = "malbolge-classic-quine-witness/1"
DEFAULT_MAX_STEPS = 70_000_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reproduce(source_path: Path, max_steps: int = DEFAULT_MAX_STEPS) -> dict:
    source_bytes = source_path.read_bytes()
    source = source_bytes.decode("ascii")
    status, steps, output = malbolge.run(source, max_steps=max_steps)
    return {
        "format": FORMAT,
        "epoch": "E10",
        "semantic_profile": "CLASSIC_MALBOLGE",
        "source_path": str(source_path),
        "source_bytes": len(source_bytes),
        "source_cells": len("".join(source.split())),
        "source_sha256": sha256(source_bytes),
        "status": status,
        "steps": steps,
        "output_bytes": len(output),
        "output_sha256": sha256(output),
        "quine": output == source_bytes,
        "equivalence": "EXACT_SOURCE_BYTES" if output == source_bytes else "MISMATCH",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = reproduce(args.source, args.max_steps)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "HALTED" and report["quine"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
