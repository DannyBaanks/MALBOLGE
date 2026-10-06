"""Falsification probe: execute the three-instruction toy on a full E15 VM."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from array import array
from pathlib import Path

import malbolge
from offset_epoch_ladder import encode, offsets_for

HERE = Path(__file__).resolve().parent
PREREGISTRATION = HERE / "evidence" / "e15_vm_preregistration.json"
REPORT = HERE / "evidence" / "e15_vm_report.json"
FORMAT = "malbolge-parametric-vm-probe/1"
VALID_OPS = frozenset({4, 5, 23, 39, 40, 62, 68, 81})
CRAZY = ((1, 0, 0), (1, 0, 2), (2, 2, 1))
CHUNK_TRITS = 5
CHUNK_BASE = 3 ** CHUNK_TRITS


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crazy_chunk_table() -> array:
    result = array("B", [0]) * (CHUNK_BASE * CHUNK_BASE)
    for a0 in range(CHUNK_BASE):
        for b0 in range(CHUNK_BASE):
            a, b, value, place = a0, b0, 0, 1
            for _ in range(CHUNK_TRITS):
                value += CRAZY[b % 3][a % 3] * place
                a //= 3
                b //= 3
                place *= 3
            result[a0 * CHUNK_BASE + b0] = value
    return result


CRAZY_CHUNKS = crazy_chunk_table()


def crazy_width(a: int, b: int, dimension: int) -> int:
    if dimension % CHUNK_TRITS:
        raise ValueError("probe supports dimensions divisible by five")
    value, place = 0, 1
    for _ in range(dimension // CHUNK_TRITS):
        value += CRAZY_CHUNKS[(a % CHUNK_BASE) * CHUNK_BASE + b % CHUNK_BASE] * place
        a //= CHUNK_BASE
        b //= CHUNK_BASE
        place *= CHUNK_BASE
    return value


def tape_sha256(tape: array) -> str:
    return hashlib.sha256(memoryview(tape).cast("B")).hexdigest()


def load_full(source: str, dimension: int, offsets: tuple[int, int, int]):
    started = time.perf_counter()
    chars = [char for char in source if not char.isspace()]
    size = 3 ** dimension
    third = 3 ** (dimension - 1)
    if len(chars) > size:
        return None, "program_too_long", time.perf_counter() - started
    tape = array("I", [0]) * size
    for position, char in enumerate(chars):
        value = ord(char)
        if not 33 <= value <= 126:
            return None, f"non_printable_at_{position}", time.perf_counter() - started
        opcode = (value + position + offsets[position // third]) % 94
        if opcode not in VALID_OPS:
            return None, f"invalid_opcode_{opcode}_at_{position}", time.perf_counter() - started
        tape[position] = value
    chunks = dimension // CHUNK_TRITS
    if chunks not in (2, 3):
        raise ValueError("this probe supports only E10 and E15")
    table, base = CRAZY_CHUNKS, CHUNK_BASE
    for position in range(len(chars), size):
        a, b = tape[position - 1], tape[position - 2]
        if chunks == 2:
            tape[position] = (table[(a % base) * base + b % base] +
                              table[((a // base) % base) * base + (b // base) % base] * base)
        else:
            tape[position] = (table[(a % base) * base + b % base] +
                              table[((a // base) % base) * base + (b // base) % base] * base +
                              table[((a // (base * base)) % base) * base +
                                    (b // (base * base)) % base] * base * base)
    return tape, "loaded", time.perf_counter() - started


def execute(source: str, dimension: int, offsets: tuple[int, int, int],
            stdin_data: bytes, max_steps: int) -> dict:
    tape, load_reason, load_seconds = load_full(source, dimension, offsets)
    if tape is None:
        return {"status": "INVALID", "halt_reason": load_reason, "steps": 0,
                "stdout_hex": "", "full_crazy_fill_completed": False,
                "load_seconds": load_seconds}
    initial_tape_sha256 = tape_sha256(tape)
    size, third = 3 ** dimension, 3 ** (dimension - 1)
    a = c = d = stdin_pos = steps = 0
    stdout = bytearray()
    started = time.perf_counter()
    while steps < max_steps:
        steps += 1
        opcode = (tape[c] + c + offsets[c // third]) % 94
        if opcode == 4:
            c = tape[d]
        elif opcode == 5:
            stdout.append(a % 256)
        elif opcode == 23:
            if stdin_pos < len(stdin_data):
                a = stdin_data[stdin_pos]
                stdin_pos += 1
            else:
                a = size - 1
        elif opcode == 39:
            value = tape[d]
            tape[d] = value // 3 + (value % 3) * (3 ** (dimension - 1))
            a = tape[d]
        elif opcode == 40:
            d = tape[d]
        elif opcode == 62:
            tape[d] = crazy_width(a, tape[d], dimension)
            a = tape[d]
        elif opcode == 81:
            return {"status": "HALTED", "halt_reason": "halt_opcode", "steps": steps,
                    "stdout_hex": stdout.hex(), "final_registers": {"a": a, "c": c, "d": d},
                    "full_crazy_fill_completed": True, "memory_cells": len(tape),
                    "initial_tape_sha256": initial_tape_sha256,
                    "final_tape_sha256": tape_sha256(tape), "load_seconds": load_seconds,
                    "execution_seconds": time.perf_counter() - started}
        if 33 <= tape[c] <= 126:
            tape[c] = malbolge._ENCRYPT[tape[c]]
        c = (c + 1) % size
        d = (d + 1) % size
    return {"status": "OUT_OF_FUEL", "halt_reason": "max_steps", "steps": steps,
            "stdout_hex": stdout.hex(), "final_registers": {"a": a, "c": c, "d": d},
            "full_crazy_fill_completed": True, "memory_cells": len(tape),
            "initial_tape_sha256": initial_tape_sha256,
            "final_tape_sha256": tape_sha256(tape), "load_seconds": load_seconds,
            "execution_seconds": time.perf_counter() - started}


def exact_success(result: dict) -> bool:
    return (result.get("status") == "HALTED" and result.get("halt_reason") == "halt_opcode"
            and result.get("steps") == 3 and result.get("stdout_hex") == "5a"
            and result.get("final_registers") == {"a": 90, "c": 2, "d": 2}
            and result.get("full_crazy_fill_completed") is True)


def main() -> int:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    target = prereg["target"]
    source = "".join(encode(opcode, position, 15, tuple(target["offsets"]))
                     for position, opcode in enumerate((23, 5, 81)))

    baseline = execute(source, 10, (0, 0, 0), b"Z", 10)
    oracle_status, oracle_steps, oracle_stdout = malbolge.run(source, b"Z", 10)
    baseline["oracle"] = {"status": oracle_status, "steps": oracle_steps,
                          "stdout_hex": oracle_stdout.hex()}
    baseline_pass = (exact_success(baseline) and oracle_status == "HALTED"
                     and oracle_steps == 3 and oracle_stdout == b"Z")

    negative = execute(source, 15, (1, 105, 116), b"Z", 10)
    negative_pass = negative["status"] == "INVALID"
    target_result = execute(source, 15, tuple(target["offsets"]), b"Z", target["max_steps"])
    target_pass = exact_success(target_result)
    demonstrated = baseline_pass and negative_pass and target_pass
    report = {
        "format": FORMAT,
        "preregistration_sha256": file_sha256(PREREGISTRATION),
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "byteorder": sys.byteorder, "array_itemsize": array("I").itemsize},
        "source": source,
        "source_hex": source.encode("ascii").hex(),
        "baseline_e10": baseline,
        "baseline_pass": baseline_pass,
        "negative_control_e15": negative,
        "negative_control_pass": negative_pass,
        "target_e15": target_result,
        "target_pass": target_pass,
        "null_hypothesis_rejected": demonstrated,
        "claim": ("VM_EXECUTION_PARITY_E15=DEMONSTRATED" if demonstrated
                  else "VM_EXECUTION_PARITY_E15=NOT_DEMONSTRATED"),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if demonstrated else 1


if __name__ == "__main__":
    raise SystemExit(main())
