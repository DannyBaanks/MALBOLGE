"""Confirmatory replay of the frozen E11-E18 region witnesses.

Reads evidence/region_witness_preregistration.json. Refuses to proceed if a
re-encoded source does not match the frozen source. Writes
evidence/region_witness_report.json. Exploration is not this script.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from offset_epoch_ladder import encode, offsets_for  # noqa: E402

PREREG = HERE / "evidence" / "region_witness_preregistration.json"
REPORT = HERE / "evidence" / "region_witness_report.json"
RUNNER = Path("/tmp/ivm_runner_native")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(dimension: int, source: str, offsets: tuple[int, int, int]) -> dict:
    cmd = [str(RUNNER), str(dimension), source.encode("ascii").hex(), "", "512",
           *[str(o) for o in offsets]]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    line = next((ln for ln in (proc.stderr + proc.stdout).splitlines()
                 if ln.startswith("RESULT ")), None)
    if line is None:
        return {"status": "NO_RESULT", "raw": (proc.stderr + proc.stdout)[-300:]}
    return dict(tok.split("=", 1) for tok in line.split()[1:])


def main() -> int:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    rows = []
    first_fail = None
    for width in prereg["widths"]:
        k = width["dimension"]
        offsets = offsets_for(k)
        plan = tuple(width["plan"])
        source = "".join(encode(op, i, k, offsets) for i, op in enumerate(plan))
        if source != width["source"]:
            print(f"E{k} SOURCE DRIFT frozen={width['source']!r} live={source!r}")
            return 2
        target = run(k, source, offsets)
        replay_ok = (
            target.get("status") == "HALTED"
            and int(target.get("visited", "0")) == 7
            and int(target.get("steps", "-1")) == width["steps"]
            and [int(target.get(f"e{i}step", "-1")) for i in range(3)] == width["entry_steps"]
            and [int(target.get(f"e{i}op", "-1")) for i in range(3)] == width["entry_ops"]
            and int(target.get("a", "-1")) == width["final"]["a"]
            and int(target.get("c", "-1")) == width["final"]["c"]
            and int(target.get("d", "-1")) == width["final"]["d"]
            and target.get("initial_tape_sha256") == width["initial_tape_sha256"]
            and target.get("final_tape_sha256") == width["final_tape_sha256"]
        )
        c1_off = (offsets[0], offsets[1] + 1, offsets[2])
        c2_off = (offsets[0], offsets[1], offsets[2] + 1)
        c1 = run(k, source, c1_off)
        c2 = run(k, source, c2_off)
        c1_ok = int(c1.get("e1op", "-1")) != width["entry_ops"][1]
        c2_ok = int(c2.get("e2op", "-1")) != width["entry_ops"][2]
        ok = replay_ok and c1_ok and c2_ok
        if not ok and first_fail is None:
            first_fail = k
        print(f"E{k} replay={'PASS' if replay_ok else 'FAIL'} "
              f"off1={'PASS' if c1_ok else 'FAIL'} off2={'PASS' if c2_ok else 'FAIL'} "
              f"e1op {width['entry_ops'][1]}->{c1.get('e1op')} "
              f"e2op {width['entry_ops'][2]}->{c2.get('e2op')}")
        rows.append({
            "dimension": k,
            "replay_pass": replay_ok,
            "offset1_control_pass": c1_ok,
            "offset2_control_pass": c2_ok,
            "target": target,
            "offset1": {"offsets": list(c1_off), "e1op": c1.get("e1op"),
                        "visited": c1.get("visited"), "status": c1.get("status"),
                        "steps": c1.get("steps")},
            "offset2": {"offsets": list(c2_off), "e2op": c2.get("e2op"),
                        "visited": c2.get("visited"), "status": c2.get("status"),
                        "steps": c2.get("steps")},
        })
    claim = ("NATURAL_ALL_REGION_E11_TO_E18=DEMONSTRATED" if first_fail is None
             else "NATURAL_ALL_REGION_E11_TO_E18=NOT_DEMONSTRATED")
    report = {
        "format": "malbolge-region-witness-report/1",
        "preregistration": PREREG.name,
        "instrument_sha256": sha256_file(RUNNER),
        "runner_source_sha256": sha256_file(HERE / "intermediate_vm_runner.zig"),
        "widths": rows,
        "first_failing_width": first_fail,
        "claim": claim,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(claim)
    return 0 if first_fail is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
