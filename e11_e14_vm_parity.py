"""E11-E14 VM execution parity (preregistered 2026-10-02).

Runs the generalized probe (e15_vm_probe.execute, now backed by
crazy_width_general) at E11, E12, E13 and E14 on generated IN,OUT,END toys
with the frozen ladder offsets, plus the registered negative control.

Fail-closed: refuses to run if the preregistration is missing or if
offset_epoch_ladder.offsets_for(k) drifts from the registered offsets.
Writes evidence/e11_e14_vm_report.json; never touches other reports.
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

PREREG = HERE / "evidence" / "e11_e14_vm_preregistration.json"
REPORT = HERE / "evidence" / "e11_e14_vm_report.json"


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
    # Registered negative control: keep the frozen E12-generated source and
    # corrupt only the region-0 offset used when loading/executing. Decoding
    # the valid source with offset 0->1 must fail at load time (INVALID), not
    # silently HALT: generating the source with the corrupted offsets would be
    # self-consistent and is NOT a control.
    e12 = next(r for r in results if r["dimension"] == 12)
    bad_offsets = (1, *offsets_for(12)[1:])
    negative = execute(e12["source"], 12, bad_offsets, stdin, prereg["target"]["max_steps"])
    negative_pass = (negative["status"] == "INVALID"
                     and negative["full_crazy_fill_completed"] is False)
    print(f"negative_control_E12: {'PASS' if negative_pass else 'FAIL'} "
          f"status={negative['status']} steps={negative['steps']}")
    targets_pass = all(r["pass"] for r in results)
    claim = ("VM_EXECUTION_PARITY_E11_E14=DEMONSTRATED"
             if (targets_pass and negative_pass)
             else "VM_EXECUTION_PARITY_E11_E14=NOT_DEMONSTRATED")
    report = {
        "format": "malbolge-parametric-vm-report/1",
        "preregistration": PREREG.name,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "results": results,
        "negative_control_e12": {**negative, "pass": negative_pass},
        "targets_pass": targets_pass,
        "claim": claim,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(claim)
    return 0 if claim == "VM_EXECUTION_PARITY_E11_E14=DEMONSTRATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
