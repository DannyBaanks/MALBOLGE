"""E16-E18 VM execution parity (preregistered 2026-10-02).

Same pipeline as e11_e14_vm_parity.py on the generalized probe. Adds a
memory guard: a dimension that does not fit in currently available RAM is
recorded SKIPPED_INSUFFICIENT_MEMORY and makes the claim NOT_DEMONSTRATED.
Fail-closed: refuses to run if offsets_for(k) drifts from the registration.
Writes evidence/e16_e18_vm_report.json; never touches other reports.
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from offset_epoch_ladder import TOY_OPCODES, encode, offsets_for  # noqa: E402
from e15_vm_probe import exact_success, execute  # noqa: E402

PREREG = HERE / "evidence" / "e16_e18_vm_preregistration.json"
REPORT = HERE / "evidence" / "e16_e18_vm_report.json"
HEADROOM_BYTES = 1536 * 1024 * 1024


def mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable not found")


def main() -> int:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    stdin = bytes.fromhex(prereg["target"]["stdin_hex"])
    results = []
    for entry in prereg["dimensions"]:
        dim = entry["dimension"]
        live = list(offsets_for(dim))
        if live != entry["offsets"]:
            print(f"FORMULA DRIFT at E{dim}: ladder={live} registered={entry['offsets']}",
                  file=sys.stderr)
            return 2
        needed = entry["memory_cells"] * 4
        available = mem_available_bytes()
        if needed + HEADROOM_BYTES > available:
            print(f"E{dim}: SKIPPED_INSUFFICIENT_MEMORY need={needed // 2**20}MB "
                  f"avail={available // 2**20}MB headroom={HEADROOM_BYTES // 2**20}MB")
            results.append({"dimension": dim, "status": "SKIPPED_INSUFFICIENT_MEMORY",
                            "pass": False, "memory_cells": entry["memory_cells"]})
            continue
        offsets = tuple(entry["offsets"])
        source = "".join(encode(op, pos, dim, offsets)
                         for pos, op in enumerate(TOY_OPCODES))
        result = execute(source, dim, offsets, stdin, prereg["target"]["max_steps"])
        result["source"] = source
        result["pass"] = exact_success(result)
        results.append({"dimension": dim, **result})
        mark = "PASS" if result["pass"] else "FAIL"
        print(f"E{dim}: {mark} status={result['status']} steps={result['steps']} "
              f"out={result['stdout_hex']} regs={result.get('final_registers')} "
              f"cells={result.get('memory_cells')} load={result.get('load_seconds', 0):.2f}s")
    # Registered negative control: frozen E16 source with region-0 offset 0->1.
    e16 = next(r for r in results if r["dimension"] == 16)
    bad_offsets = (1, *offsets_for(16)[1:])
    if "source" in e16:
        negative = execute(e16["source"], 16, bad_offsets, stdin,
                           prereg["target"]["max_steps"])
    else:
        negative = {"status": "SKIPPED_INSUFFICIENT_MEMORY", "steps": 0}
    negative_pass = (negative["status"] == "INVALID"
                     and negative.get("full_crazy_fill_completed") is False)
    print(f"negative_control_E16: {'PASS' if negative_pass else 'FAIL'} "
          f"status={negative['status']} steps={negative['steps']}")
    targets_pass = all(r["pass"] for r in results)
    claim = ("VM_EXECUTION_PARITY_E16_E18=DEMONSTRATED"
             if (targets_pass and negative_pass)
             else "VM_EXECUTION_PARITY_E16_E18=NOT_DEMONSTRATED")
    report = {
        "format": "malbolge-parametric-vm-report/1",
        "preregistration": PREREG.name,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "mem_available_bytes_at_start": mem_available_bytes(),
        },
        "results": results,
        "negative_control_e16": {**negative, "pass": negative_pass},
        "targets_pass": targets_pass,
        "claim": claim,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(claim)
    return 0 if claim == "VM_EXECUTION_PARITY_E16_E18=DEMONSTRATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
