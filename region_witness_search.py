"""Exploratory synthesis of a natural all-region witness at an arbitrary width.

NOT confirmatory evidence. Protocol frozen 2026-10-02 for the E11-E18
follow-up of the E15 region experiment:

- prefix plan (40, 4) = [MOVD, JMP], as in the E15 exploratory search;
- suffix of length 3 over the 8 canonical opcodes, enumerated
  lexicographically, bounded to the first 128 candidates (same bound the E15
  search used);
- standard start a=c=d=0, empty stdin, max_steps=512;
- instrument: native rebuild of intermediate_vm_runner.zig (ReleaseSafe,
  Zig 0.16.0) from the repo source, so the runner semantics are identical to
  the recorded .exe used by the sweep;
- hit: runner reports visited & 0b111 == 0b111. A selectable witness must
  additionally be HALTED at or before max_steps.

Searches are exploratory and are never counted as confirmatory evidence; the
selected source at each width is frozen in a pre-registration before the
confirmatory gate runs. If a bounded search finds no selectable witness, the
result is recorded as is (first failing width preserved, per the frozen
failure policy of the sweep).
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from offset_epoch_ladder import encode, offsets_for  # noqa: E402

OPS = (4, 5, 23, 39, 40, 62, 68, 81)
PREFIX = (40, 4)
MAX_STEPS = 512

_RUNNER = None
_DIM = None
_OFFSETS = None


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_result(text: str) -> dict:
    line = next((ln for ln in text.splitlines() if ln.startswith("RESULT ")), None)
    if line is None:
        raise ValueError("no RESULT line in runner output")
    fields = {}
    for token in line.split()[1:]:
        key, _, value = token.partition("=")
        fields[key] = value
    return fields


def search_one(suffix: tuple[int, ...]) -> dict:
    plan = PREFIX + suffix
    source = "".join(encode(op, position, _DIM, _OFFSETS)
                     for position, op in enumerate(plan))
    cmd = [_RUNNER, str(_DIM), source.encode("ascii").hex(), "", str(MAX_STEPS),
           *[str(o) for o in _OFFSETS]]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    record = {"plan": list(plan), "source": source}
    if proc.returncode != 0 and not proc.stderr:
        record["status"] = f"runner_exit_{proc.returncode}"
        return record
    try:
        fields = parse_result(proc.stderr + proc.stdout)
    except ValueError as exc:
        record["status"] = f"parse_error: {exc}"
        return record
    visited = int(fields.get("visited", "0"))
    status = fields.get("status", "UNKNOWN")
    record.update({
        "status": status,
        "visited_mask": visited,
        "visited_regions": [r for r in range(3) if visited & (1 << r)],
        "steps": int(fields.get("steps", "0")),
        "entry_steps": [int(fields.get(f"e{r}step", "0")) for r in range(3)],
        "entry_ops": [int(fields.get(f"e{r}op", "0")) for r in range(3)],
        "initial_tape_sha256": fields.get("initial_tape_sha256", ""),
        "final_tape_sha256": fields.get("final_tape_sha256", ""),
        "out_hex": fields.get("out_hex", "-"),
        "final": {"a": int(fields.get("a", "0")), "c": int(fields.get("c", "0")),
                  "d": int(fields.get("d", "0"))},
    })
    return record


def main() -> int:
    global _RUNNER, _DIM, _OFFSETS
    parser = argparse.ArgumentParser()
    parser.add_argument("--dimension", type=int, required=True)
    parser.add_argument("--limit", type=int, default=128)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--runner", default="/tmp/ivm_runner_native")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    _RUNNER = args.runner
    _DIM = args.dimension
    _OFFSETS = offsets_for(args.dimension)
    candidates = list(itertools.product(OPS, repeat=3))[:args.limit]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(search_one, candidates))
    hits = [r for r in results if r.get("visited_mask", 0) == 0b111]
    selectable = [r for r in hits if r.get("status") == "HALTED"]
    summary = {
        "format": "malbolge-region-witness-search/1",
        "exploratory_not_confirmatory": True,
        "protocol": {"prefix": list(PREFIX), "suffix_length": 3,
                     "limit": args.limit, "ops": list(OPS),
                     "max_steps": MAX_STEPS, "stdin_hex": ""},
        "dimension": args.dimension,
        "offsets": list(_OFFSETS),
        "instrument": {"runner": args.runner, "sha256": sha256_file(args.runner),
                       "source_sha256": sha256_file(str(HERE / "intermediate_vm_runner.zig"))},
        "candidate_count": len(results),
        "hits": hits,
        "selectable_count": len(selectable),
        "selected": selectable[0] if selectable else None,
        "patterns": {},
        "errors": [r for r in results if "status" not in r or r["status"].startswith(("runner_exit", "parse_error"))],
    }
    for r in results:
        key = ",".join(str(x) for x in r.get("visited_regions", []))
        summary["patterns"][key] = summary["patterns"].get(key, 0) + 1
    text = json.dumps(summary, sort_keys=True, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if selectable else 1


if __name__ == "__main__":
    raise SystemExit(main())
