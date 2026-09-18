"""Exploratory synthesis only: find a standard-start E15 path into region 2."""
from __future__ import annotations

import itertools
import json
import argparse
from concurrent.futures import ProcessPoolExecutor

import malbolge
from e15_vm_probe import crazy_width, load_full
from offset_epoch_ladder import encode

DIMENSION = 15
SIZE = 3 ** DIMENSION
THIRD = 3 ** (DIMENSION - 1)
OFFSETS = (0, 105, 116)
OPS = (4, 5, 23, 39, 40, 62, 68, 81)


def search_one(suffix: tuple[int, int]) -> dict:
    plan = (40, 4) + suffix
    source = "".join(encode(op, position, DIMENSION, OFFSETS)
                     for position, op in enumerate(plan))
    tape, reason, _ = load_full(source, DIMENSION, OFFSETS)
    if tape is None:
        return {"plan": plan, "source": source, "status": reason, "regions": []}
    a = c = d = 0
    regions = []
    trace = []
    for step in range(1, 513):
        region = c // THIRD
        if region not in regions:
            regions.append(region)
            trace.append({"event": "ENTER_REGION", "step": step,
                          "region": region, "a": a, "c": c, "d": d})
        opcode = (tape[c] + c + OFFSETS[region]) % 94
        if opcode == 4:
            target = tape[d]
            trace.append({"event": "JUMP", "step": step, "from_c": c,
                          "d": d, "target": target, "target_region": target // THIRD})
            c = target
        elif opcode == 5:
            pass
        elif opcode == 23:
            a = SIZE - 1
        elif opcode == 39:
            tape[d] = tape[d] // 3 + (tape[d] % 3) * THIRD
            a = tape[d]
            if a >= 2 * THIRD:
                trace.append({"event": "WRITE_REGION2_VALUE", "step": step,
                              "address": d, "value": a})
        elif opcode == 40:
            d = tape[d]
        elif opcode == 62:
            tape[d] = crazy_width(a, tape[d], DIMENSION)
            a = tape[d]
            if a >= 2 * THIRD:
                trace.append({"event": "WRITE_REGION2_VALUE", "step": step,
                              "address": d, "value": a})
        elif opcode == 81:
            return {"plan": plan, "source": source, "status": "HALTED",
                    "steps": step, "regions": regions, "trace": trace,
                    "final": {"a": a, "c": c, "d": d}}
        if 33 <= tape[c] <= 126:
            tape[c] = malbolge._ENCRYPT[tape[c]]
        c = (c + 1) % SIZE
        d = (d + 1) % SIZE
    return {"plan": plan, "source": source, "status": "OUT_OF_FUEL",
            "steps": 512, "regions": regions, "trace": trace,
            "final": {"a": a, "c": c, "d": d}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suffix-length", type=int, default=2)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    candidates = list(itertools.product(OPS, repeat=args.suffix_length))
    if args.limit is not None:
        candidates = candidates[:args.limit]
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(search_one, candidates))
    hits = [result for result in results if 2 in result["regions"]]
    summary = {"format": "e15-natural-region-search/1",
               "exploratory_not_confirmatory": True,
               "suffix_length": args.suffix_length,
               "candidate_count": len(results), "hits": hits,
               "region_patterns": {str(pattern): sum(r["regions"] == list(pattern)
                                                       for r in results)
                                   for pattern in ((0,), (0, 1), (0, 1, 2))}}
    print(json.dumps(summary, sort_keys=True))
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
