"""Independent Python reference for the frozen width-k parametric VM profile.

Written from the `vm_profile` block of
`evidence/intermediate_vm_sweep_preregistration.json`, not from
`intermediate_vm_runner.zig`, so the two can be compared differentially:

    memory           exactly 3^k unsigned-32 cells
    fill             complete k-trit crazy-fill, mem[i] = crazy(mem[i-1], mem[i-2])
    registers        a = c = d = 0
    dispatch         (mem[c] + c + offset[c // 3^(k-1)]) mod 94
    rotation         k-trit rotate-right
    self-encryption  Classic printable-ASCII XLAT after non-halting steps
    eof              3^k - 1

Deliberate algorithmic difference from the Zig runner: crazy is split into
5-trit chunks, and the remaining k mod 5 top trits use a SECOND table built
trit by trit for exactly that many trits. The Zig runner instead reuses the
5-trit table and reduces modulo 3^take. Same function, different route.

The chunk tables are built from the crazy definition in `malbolge.py`.
Tape hashes use the same bytes as the Python E15 probes (array('I'),
little-endian) so full-tape results are directly comparable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from array import array

import malbolge

VALID = frozenset({4, 5, 23, 39, 40, 62, 68, 81})
CHUNK_TRITS = 5
CHUNK_BASE = 3 ** CHUNK_TRITS


def _crazy_trits(a: int, b: int, trits: int) -> int:
    value, place = 0, 1
    for _ in range(trits):
        value += malbolge._CRAZY[b % 3][a % 3] * place
        a //= 3
        b //= 3
        place *= 3
    return value


def _table(trits: int) -> list[int]:
    base = 3 ** trits
    return [_crazy_trits(a, b, trits) for a in range(base) for b in range(base)]


FULL_TABLE = _table(CHUNK_TRITS)
REM_TABLES = {r: _table(r) for r in range(1, CHUNK_TRITS)}


def crazy_k(a: int, b: int, k: int) -> int:
    full, rem = divmod(k, CHUNK_TRITS)
    value, place = 0, 1
    for _ in range(full):
        value += FULL_TABLE[(a % CHUNK_BASE) * CHUNK_BASE + b % CHUNK_BASE] * place
        a //= CHUNK_BASE
        b //= CHUNK_BASE
        place *= CHUNK_BASE
    if rem:
        rb = 3 ** rem
        value += REM_TABLES[rem][(a % rb) * rb + b % rb] * place
    return value


def tape_sha256(tape: array) -> str:
    return hashlib.sha256(memoryview(tape).cast("B")).hexdigest()


def load(source: str, k: int, offsets: tuple[int, int, int]):
    chars = [ch for ch in source if not ch.isspace()]
    size, third = 3 ** k, 3 ** (k - 1)
    if len(chars) < 2:
        return None, "program_too_short"
    if len(chars) > size:
        return None, "program_too_long"
    # array('I', [0]) * size allocates the cells once; bytes(4*size) would
    # double the peak (3.1 GB at E18) through an intermediate buffer.
    tape = array("I", [0]) * size
    for pos, ch in enumerate(chars):
        v = ord(ch)
        if not 33 <= v <= 126:
            return None, f"non_printable_at_{pos}"
        op = (v + pos + offsets[pos // third]) % 94
        if op not in VALID:
            return None, f"invalid_opcode_{op}_at_{pos}"
        tape[pos] = v

    # Crazy-fill, specialised per (full chunks, remainder) with locals only;
    # it is the dominant cost (3^18 cells at E18).
    full, rem = divmod(k, CHUNK_TRITS)
    ft, base = FULL_TABLE, CHUNK_BASE
    rt = REM_TABLES.get(rem)
    rb = 3 ** rem if rem else 1
    p1, p2 = base, base * base
    p3 = p2 * base
    x2, x1 = tape[len(chars) - 2], tape[len(chars) - 1]
    for pos in range(len(chars), size):
        a, b = x1, x2
        value = ft[(a % base) * base + b % base]
        if full >= 2:
            a //= base; b //= base
            value += ft[(a % base) * base + b % base] * p1
        if full >= 3:
            a //= base; b //= base
            value += ft[(a % base) * base + b % base] * p2
        if rem:
            a //= base; b //= base
            value += rt[(a % rb) * rb + b % rb] * (p1 if full == 1 else p2 if full == 2 else p3)
        tape[pos] = value
        x2, x1 = x1, value
    return tape, None


def run(source: str, k: int, offsets, stdin: bytes = b"", max_steps: int = 512) -> dict:
    t0 = time.perf_counter()
    tape, reason = load(source, k, tuple(offsets))
    load_s = time.perf_counter() - t0
    if tape is None:
        return {"status": "INVALID", "reason": reason, "dimension": k}
    size, third = 3 ** k, 3 ** (k - 1)
    initial = tape_sha256(tape)
    a = c = d = steps = inp = 0
    out = bytearray()
    entries: dict[str, dict] = {}
    status = "OUT_OF_FUEL"
    while steps < max_steps:
        steps += 1
        region = c // third
        op = (tape[c] + c + offsets[region]) % 94
        entries.setdefault(str(region), {"step": steps, "opcode": op})
        if op == 4:
            c = tape[d]
        elif op == 5:
            out.append(a % 256)
        elif op == 23:
            if inp < len(stdin):
                a = stdin[inp]
                inp += 1
            else:
                a = size - 1
        elif op == 39:
            v = tape[d]
            tape[d] = v // 3 + (v % 3) * third
            a = tape[d]
        elif op == 40:
            d = tape[d]
        elif op == 62:
            tape[d] = crazy_k(a, tape[d], k)
            a = tape[d]
        elif op == 81:
            status = "HALTED"
            break
        if 33 <= tape[c] <= 126:
            tape[c] = malbolge._ENCRYPT[tape[c]]
        c = (c + 1) % size
        d = (d + 1) % size
    return {"status": status, "dimension": k, "memory_cells": size, "steps": steps,
            "stdout_hex": out.hex(), "a": a, "c": c, "d": d,
            "visited": sorted(int(r) for r in entries), "first_entries": entries,
            "initial_tape_sha256": initial, "final_tape_sha256": tape_sha256(tape),
            "load_seconds": round(load_s, 2)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dimension", type=int)
    ap.add_argument("source")
    ap.add_argument("--stdin-hex", default="")
    ap.add_argument("--max-steps", type=int, default=512)
    ap.add_argument("--offsets", type=int, nargs=3, default=(0, 0, 0))
    args = ap.parse_args()
    print(json.dumps(run(args.source, args.dimension, args.offsets,
                         bytes.fromhex(args.stdin_hex), args.max_steps), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
