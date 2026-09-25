"""Full-VM sweep E11-E18: the frozen preregistration, applied exactly.

Gates come from evidence/intermediate_vm_sweep_preregistration.json.
IMPLEMENTATION_PARITY_Ek comes from the addendum frozen before execution:
every run is executed twice, by the native Zig runner and by the independent
Python reference (reference_width_vm.py), and the two must agree field by
field, including full-tape SHA-256 before and after execution.

Every width is run and retained even after a failure. The report is written
after each width, so an interruption preserves what already ran.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import binaries
import reference_width_vm as reference

HERE = Path(__file__).resolve().parent
RUNNER = binaries.find_vm_runner() or HERE / ("intermediate_vm_runner" + binaries.EXE_SUFFIX)
PREREG = HERE / "evidence" / "intermediate_vm_sweep_preregistration.json"
ADDENDUM = HERE / "evidence" / "intermediate_vm_sweep_preregistration_addendum.json"
REPORT = HERE / "evidence" / "intermediate_vm_sweep_report.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zig_run(k: int, source: str, stdin_hex: str, fuel: int, offsets) -> dict:
    args = [str(RUNNER), str(k), source.encode("ascii").hex(), stdin_hex, str(fuel),
            *map(str, offsets)]
    started = time.perf_counter()
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired:
        return {"status": "HOST_TIMEOUT"}
    elapsed = round(time.perf_counter() - started, 2)
    text = proc.stderr + proc.stdout          # the runner reports on stderr
    lines = [line for line in text.splitlines() if line.startswith("RESULT ")]
    if not lines:
        if "InvalidSource" in text or "InvalidCharacter" in text:
            return {"status": "INVALID", "raw": text.strip()[-300:], "seconds": elapsed}
        return {"status": "RUNNER_ERROR", "raw": text.strip()[-300:], "seconds": elapsed}
    fields = dict(token.split("=", 1) for token in lines[-1].split()[1:])
    if fields.get("status") == "RESOURCE_LIMIT":
        return {"status": "RESOURCE_LIMIT", "raw": lines[-1], "seconds": elapsed}
    bits = int(fields["visited"])
    visited = [r for r in range(3) if bits >> r & 1]
    return {
        "status": fields["status"], "steps": int(fields["steps"]),
        "stdout_hex": "" if fields["out_hex"] == "-" else fields["out_hex"],
        "a": int(fields["a"]), "c": int(fields["c"]), "d": int(fields["d"]),
        "visited": visited,
        "first_entries": {str(r): {"step": int(fields[f"e{r}step"]),
                                   "opcode": int(fields[f"e{r}op"])} for r in visited},
        "initial_tape_sha256": fields["initial_tape_sha256"],
        "final_tape_sha256": fields["final_tape_sha256"],
        "fill_completed": fields.get("fill") == "true",
        "memory_cells": int(fields["memory_cells"]),
        "seconds": elapsed, "raw": lines[-1],
    }


def ref_run(k: int, source: str, stdin_hex: str, fuel: int, offsets) -> dict:
    started = time.perf_counter()
    try:
        result = reference.run(source, k, list(offsets), bytes.fromhex(stdin_hex), fuel)
    except MemoryError:
        return {"status": "RESOURCE_LIMIT"}
    result["seconds"] = round(time.perf_counter() - started, 2)
    return result


PARITY_FIELDS = ("status", "steps", "stdout_hex", "a", "c", "d", "visited",
                 "first_entries", "initial_tape_sha256", "final_tape_sha256")
UNAVAILABLE = {"RESOURCE_LIMIT", "HOST_TIMEOUT", "RUNNER_ERROR"}


def parity(zig: dict, ref: dict) -> dict:
    if zig["status"] in UNAVAILABLE or ref["status"] in UNAVAILABLE:
        return {"verdict": "NOT_DEMONSTRATED", "reason": f"zig={zig['status']} ref={ref['status']}"}
    if zig["status"] == "INVALID" or ref["status"] == "INVALID":
        same = zig["status"] == ref["status"]
        return {"verdict": "PASS" if same else "FAIL", "fields": ["status"],
                "differences": [] if same else [["status", zig["status"], ref["status"]]]}
    diffs = [[f, zig.get(f), ref.get(f)] for f in PARITY_FIELDS if zig.get(f) != ref.get(f)]
    return {"verdict": "PASS" if not diffs else "FAIL", "fields": list(PARITY_FIELDS),
            "differences": diffs}


def both(k, source, stdin_hex, fuel, offsets) -> dict:
    zig = zig_run(k, source, stdin_hex, fuel, offsets)
    ref = ref_run(k, source, stdin_hex, fuel, offsets)
    return {"offsets": list(offsets), "zig": zig, "reference": ref, "parity": parity(zig, ref)}


def toy_gate(run: dict, success: dict) -> str:
    z = run["zig"]
    if z["status"] in UNAVAILABLE:
        return "NOT_DEMONSTRATED"
    ok = (z.get("fill_completed") is True and z["status"] == success["status"]
          and z["steps"] == success["steps"] and z["stdout_hex"] == success["stdout_hex"]
          and {"a": z["a"], "c": z["c"], "d": z["d"]} == success["final_registers"])
    return "PASS" if ok else "FAIL"


def witness_gate(run: dict) -> str:
    z = run["zig"]
    if z["status"] in UNAVAILABLE:
        return "NOT_DEMONSTRATED"
    ok = (z.get("fill_completed") is True and z["status"] == "HALTED"
          and z["visited"] == [0, 1, 2])
    return "PASS" if ok else "FAIL"


def control_sensitive(control: dict, target: dict, region: int) -> bool:
    key = str(region)
    c, t = control["zig"], target["zig"]
    return (c["status"] not in UNAVAILABLE and key in c.get("first_entries", {})
            and c["first_entries"][key]["opcode"] != t["first_entries"][key]["opcode"])


def main() -> int:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    toy, witness = prereg["toy"], prereg["regional_witness"]
    report = {
        "format": "malbolge-intermediate-full-vm-sweep-report/1",
        "preregistration_sha256": sha256_file(PREREG),
        "addendum_sha256": sha256_file(ADDENDUM),
        "runner_sha256": sha256_file(RUNNER),
        "reference_sha256": sha256_file(HERE / "reference_width_vm.py"),
        "widths": [],
    }
    first_fail = {"toy": None, "region": None, "parity": None}
    for k in prereg["dimensions"]:
        offsets = prereg["offsets"][str(k)]
        started = time.perf_counter()
        width = {"dimension": k, "memory_cells": 3 ** k, "offsets": offsets}

        width["toy"] = both(k, toy["source"], toy["stdin_hex"], toy["max_steps"], offsets)
        width["toy_gate"] = toy_gate(width["toy"], toy["success"])

        width["witness"] = both(k, witness["source"], witness["stdin_hex"],
                                witness["max_steps"], offsets)
        width["witness_gate"] = witness_gate(width["witness"])
        width["natural_all_region"] = "NOT_DEMONSTRATED"
        if width["witness_gate"] == "PASS":
            r1 = [offsets[0], offsets[1] + 1, offsets[2]]
            r2 = [offsets[0], offsets[1], offsets[2] + 1]
            width["control_region1"] = both(k, witness["source"], witness["stdin_hex"],
                                            witness["max_steps"], r1)
            width["control_region2"] = both(k, witness["source"], witness["stdin_hex"],
                                            witness["max_steps"], r2)
            s1 = control_sensitive(width["control_region1"], width["witness"], 1)
            s2 = control_sensitive(width["control_region2"], width["witness"], 2)
            width["control_region1_sensitive"], width["control_region2_sensitive"] = s1, s2
            width["natural_all_region"] = "DEMONSTRATED" if (s1 and s2) else "NOT_DEMONSTRATED"

        runs = [width[key] for key in ("toy", "witness", "control_region1", "control_region2")
                if key in width]
        verdicts = [run["parity"]["verdict"] for run in runs]
        width["implementation_parity"] = (
            "FAIL" if "FAIL" in verdicts else
            "NOT_DEMONSTRATED" if "NOT_DEMONSTRATED" in verdicts else "PASS")
        width["runs_compared"] = len(runs)
        width["seconds"] = round(time.perf_counter() - started, 1)

        if width["toy_gate"] != "PASS" and first_fail["toy"] is None:
            first_fail["toy"] = k
        if width["natural_all_region"] != "DEMONSTRATED" and first_fail["region"] is None:
            first_fail["region"] = k
        if width["implementation_parity"] != "PASS" and first_fail["parity"] is None:
            first_fail["parity"] = k
        report["widths"].append(width)
        report["first_failing_width"] = first_fail
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        z = width["witness"]["zig"]
        print(f"E{k}: toy={width['toy_gate']} witness={width['witness_gate']} "
              f"visited={z.get('visited')} status={z['status']} steps={z.get('steps')} "
              f"all_region={width['natural_all_region']} parity={width['implementation_parity']} "
              f"({width['runs_compared']} runs, {width['seconds']}s)", flush=True)

    widths = report["widths"]
    report["claims"] = {
        **{f"FULL_VM_TOY_E{w['dimension']}": "DEMONSTRATED" if w["toy_gate"] == "PASS"
           else "NOT_DEMONSTRATED" for w in widths},
        **{f"NATURAL_ALL_REGION_E{w['dimension']}": w["natural_all_region"] for w in widths},
        **{f"IMPLEMENTATION_PARITY_E{w['dimension']}":
           "DEMONSTRATED" if w["implementation_parity"] == "PASS" else w["implementation_parity"]
           for w in widths},
        "FULL_VM_TOY_E11_TO_E18": "DEMONSTRATED" if first_fail["toy"] is None else "NOT_DEMONSTRATED",
        "NATURAL_ALL_REGION_E11_TO_E18": "DEMONSTRATED" if first_fail["region"] is None else "NOT_DEMONSTRATED",
        "IMPLEMENTATION_PARITY_E11_TO_E18": "DEMONSTRATED" if first_fail["parity"] is None else "NOT_DEMONSTRATED",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"first_failing_width": first_fail, "claims": report["claims"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
