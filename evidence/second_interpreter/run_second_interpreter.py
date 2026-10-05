#!/usr/bin/env python3
"""Corroboracion en interprete independiente de los artifacts ganadores.

Interprete 1: malbolge.py (referencia python del repo).
Interprete 2: intermediate_vm_runner nativo en Zig, compilado desde
              intermediate_vm_runner.zig con dimension 10 (3^10 = 59049 celdas).
Es una implementacion independiente: si coincide en output Y en numero de
pasos, el resultado no depende de una sola VM.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

WORK = pathlib.Path("/tmp/lmao_work")
REPO = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
RUNNER = pathlib.Path("/tmp/ivm_runner_native")
sys.path.insert(0, str(WORK))
sys.path.insert(0, str(REPO))
import readout_gen as g  # noqa: E402
import malbolge as M  # noqa: E402

sw = json.load(open(WORK / "mod59049_sweep.json"))
targets = [r for r in sw["rows"] if r["T"] in (2, 45, 90, 180, 81, 9)]
# el caso T=9 viene del barrido de potencias de 9 (stops=[9], pre=[1,0,0,0,0])
targets.append({"T": 9, "stops": [9], "pre": [1, 0, 0, 0, 0], "shift": [0, 0, 0, 0, 0],
                "expected": "98999"})

rows = []
print(f"runner sha256 = {hashlib.sha256(RUNNER.read_bytes()).hexdigest()}")
print(" T     esperado  malbolge.py            runner Zig out_hex     pasos py/zig   veredicto")
for r in targets:
    pre, shift, stops = r["pre"], r["shift"], r["stops"]
    res = g.run_mod59049(len(stops), pre, shift, stops=stops)
    if res["compile_rc"] != 0:
        print(f" {r['T']:<5} COMPILE_FAIL"); continue
    tag = f"mod{len(stops)}_p" + "-".join(map(str, pre)) + "_" + "-".join(map(str, shift))
    mb = WORK / f"{tag}.mb"
    py = M.run(mb.read_text(), b"", 40_000_000)
    proc = subprocess.run([str(RUNNER), "10", f"@{mb}", "", "40000000", "0", "0", "0"],
                          capture_output=True, text=True, timeout=600)
    # el runner escribe RESULT en stderr (por eso region_witness_search parsea stderr+stdout)
    kv = dict(tok.split("=", 1) for tok in (proc.stderr + " " + proc.stdout).split() if "=" in tok)
    zig_out_hex = kv.get("out_hex", "")
    zig_steps = int(kv.get("steps", -1))
    zig_status = kv.get("status", "?")
    py_out = py[2].decode("latin-1")
    ok = (zig_status == "HALTED" and zig_out_hex == py[2].hex()
          and zig_steps == py[1] and py[2].decode().endswith(r["expected"]))
    rows.append({"T": r["T"], "stops": stops, "pre": pre, "shift": shift,
                 "expected": r["expected"], "mb_sha256": res["mb_sha256"],
                 "py_status": py[0], "py_steps": py[1], "py_out": py_out,
                 "zig_status": zig_status, "zig_steps": zig_steps,
                 "zig_out_hex": zig_out_hex,
                 "zig_initial_tape_sha256": kv.get("initial_tape_sha256"),
                 "zig_final_tape_sha256": kv.get("final_tape_sha256"),
                 "agree": ok})
    print(f" {r['T']:<5} {r['expected']}    {py[0]:<7} {py_out!r:12} {zig_out_hex:14} "
          f"{py[1]}/{zig_steps:<9} {'COINCIDE' if ok else 'DIFIERE'}")

n = sum(1 for r in rows if r["agree"])
doc = {"format": "malbolge-mod59049-readout-second-interpreter/1",
       "runner": {"path": str(RUNNER),
                  "sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
                  "source": "intermediate_vm_runner.zig (repo MALBOLGE), compilado con zig build-exe -O ReleaseSafe",
                  "dimension": 10},
       "note": "el binario versionado en el repo es PE32+ (Windows); se reconstruyo nativo en Linux para esta corrida",
       "rows": rows, "n_agree": n, "n_total": len(rows)}
out = WORK / "second_interpreter_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\n{n}/{len(rows)} coinciden en output Y en numero de pasos")
print(f"sha256 report = {hashlib.sha256(out.read_bytes()).hexdigest()}")