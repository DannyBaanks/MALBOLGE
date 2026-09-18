"""Confirmatory E15 probe for natural runtime dispatch in all three regions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import malbolge
from e15_vm_probe import crazy_width, load_full, tape_sha256

HERE = Path(__file__).resolve().parent
PREREG = HERE / "evidence" / "e15_region_preregistration.json"
REPORT = HERE / "evidence" / "e15_region_report.json"
DIMENSION = 15
SIZE = 3 ** DIMENSION
THIRD = 3 ** (DIMENSION - 1)


def run(source: str, offsets: tuple[int, int, int], max_steps: int = 512) -> dict:
    tape, reason, load_seconds = load_full(source, DIMENSION, offsets)
    if tape is None:
        return {"status": "INVALID", "halt_reason": reason,
                "full_crazy_fill_completed": False}
    initial_hash = tape_sha256(tape)
    a = c = d = steps = 0
    stdout = bytearray()
    entered: dict[int, dict] = {}
    transitions = []
    previous_region = None
    while steps < max_steps:
        steps += 1
        region = c // THIRD
        opcode = (tape[c] + c + offsets[region]) % 94
        if region != previous_region:
            transitions.append({"step": steps, "region": region,
                                "a": a, "c": c, "d": d, "opcode": opcode})
            previous_region = region
        entered.setdefault(region, {"step": steps, "a": a, "c": c,
                                    "d": d, "opcode": opcode})
        if opcode == 4:
            c = tape[d]
        elif opcode == 5:
            stdout.append(a % 256)
        elif opcode == 23:
            a = SIZE - 1
        elif opcode == 39:
            tape[d] = tape[d] // 3 + (tape[d] % 3) * THIRD
            a = tape[d]
        elif opcode == 40:
            d = tape[d]
        elif opcode == 62:
            tape[d] = crazy_width(a, tape[d], DIMENSION)
            a = tape[d]
        elif opcode == 81:
            return {"status": "HALTED", "halt_reason": "halt_opcode",
                    "steps": steps, "stdout_hex": stdout.hex(),
                    "final_registers": {"a": a, "c": c, "d": d},
                    "full_crazy_fill_completed": True, "memory_cells": len(tape),
                    "offsets": list(offsets), "first_entries": entered,
                    "region_transitions": transitions,
                    "initial_tape_sha256": initial_hash,
                    "final_tape_sha256": tape_sha256(tape),
                    "load_seconds": load_seconds}
        if 33 <= tape[c] <= 126:
            tape[c] = malbolge._ENCRYPT[tape[c]]
        c = (c + 1) % SIZE
        d = (d + 1) % SIZE
    return {"status": "OUT_OF_FUEL", "halt_reason": "max_steps",
            "steps": steps, "stdout_hex": stdout.hex(),
            "final_registers": {"a": a, "c": c, "d": d},
            "full_crazy_fill_completed": True, "memory_cells": len(tape),
            "offsets": list(offsets), "first_entries": entered,
            "region_transitions": transitions,
            "initial_tape_sha256": initial_hash,
            "final_tape_sha256": tape_sha256(tape),
            "load_seconds": load_seconds}


def target_passes(result: dict, criterion: dict) -> bool:
    entries = {int(region): item
               for region, item in result.get("first_entries", {}).items()}
    return (
        result.get("full_crazy_fill_completed") is True
        and sorted(int(region) for region in entries) == criterion["visited_regions"]
        and {str(region): item["step"] for region, item in entries.items()}
        == criterion["first_region_entry_steps"]
        and {key: entries[2][key] for key in ("a", "c", "d")}
        == criterion["region2_entry_state"]
        and result.get("status") == criterion["status"]
        and result.get("halt_reason") == criterion["halt_reason"]
        and result.get("steps") == criterion["steps"]
        and result.get("final_registers") == criterion["final_registers"]
    )


def main() -> int:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    source = prereg["source"]
    offsets = tuple(prereg["offsets"])
    target = run(source, offsets)
    control_r1 = run(source, (offsets[0], offsets[1] + 1, offsets[2]))
    control_r2 = run(source, (offsets[0], offsets[1], offsets[2] + 1))
    target_pass = target_passes(target, prereg["success_criterion"])
    r1_sensitive = (1 in control_r1.get("first_entries", {})
                    and control_r1["first_entries"][1]["opcode"]
                    != target["first_entries"][1]["opcode"])
    r2_sensitive = (2 in control_r2.get("first_entries", {})
                    and control_r2["first_entries"][2]["opcode"]
                    != target["first_entries"][2]["opcode"])
    demonstrated = target_pass and r1_sensitive and r2_sensitive
    report = {
        "format": "malbolge-e15-natural-region-dispatch/1",
        "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
        "target": target,
        "target_pass": target_pass,
        "region1_offset_sensitivity_control": control_r1,
        "region1_control_pass": r1_sensitive,
        "region2_offset_sensitivity_control": control_r2,
        "region2_control_pass": r2_sensitive,
        "null_hypothesis_rejected": demonstrated,
        "claim": ("NATURAL_RUNTIME_DISPATCH_E15_REGIONS_0_1_2=DEMONSTRATED"
                  if demonstrated else
                  "NATURAL_RUNTIME_DISPATCH_E15_REGIONS_0_1_2=NOT_DEMONSTRATED"),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if demonstrated else 1


if __name__ == "__main__":
    raise SystemExit(main())
