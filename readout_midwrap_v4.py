#!/usr/bin/env python3
"""Medio-wrap v4: transicion con bloque MOVED DEDICADO (usado una sola vez).

Por que: la traza de v1 localizo la causa -- `MOVED[C] op=INV44`, la celda movd
del bloque MOVED COMPARTIDO ya esta cifrada porque `MOVED loop` se usa 3 veces
por tick y el readout no re-pasa por `loop: R_MOVED`. Con un bloque propio
(MOV2) que se usa exactamente una vez (solo uno de los 9 labels a_k se
ejecuta) no hay apertura.

H0: el readout de 2 celdas con posicion p in {1,2,4,5,6} no imprime str(9-p)+'9'.
METRICA: out == str(9-p) + '9'.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work")
MAX_STEPS = 200_000

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402


def cyc(n: int) -> str:
    return "\t" + "/".join(["Nop"] * (n - 1) + ["MovD"]) + "\n\tJmp\n"


def build(p: int) -> str:
    code = ".CODE\n" + "".join(f"{n}:\n{cyc(9)}\n" for n in ("N1", "N2"))
    code += f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\n"
             "HALT:\n\tHlt\n\nMOVED:\n\tMovD/Nop\n\tJmp\n\nMOV2:\n\tMovD/Nop\n\tJmp\n")
    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         "\tN1 w1", "\tS st1", "\tMOVED loop",
         "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
         "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
         "\tst1:", "\tMOV2 read_N1",
         "\tread_N1:"]
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\ta{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tMOV2 read_N2"]
    L.append("\tread_N2:")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for p in (1, 2, 4, 5, 6):
    src = WORK / f"tr4_p{p}.hell"
    mb = WORK / f"tr4_p{p}.mb"
    src.write_text(build(p))
    cp = subprocess.run([str(LMAO), "-o", str(mb), str(src)],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"p": p, "predicted": f"{9-p}9", "compile_rc": cp.returncode,
           "stderr": cp.stderr.strip()[:160],
           "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        st, steps, out = M.run(mb.read_text(), b"", MAX_STEPS)
        row.update({"status": st, "steps": steps, "out": out.decode("latin-1"),
                    "match": out.decode("latin-1") == f"{9-p}9"})
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

ok = [r for r in rows if r.get("match")]
doc = {
    "format": "malbolge-lmao-readout-midwrap-trace/4",
    "question": "Se puede encadenar el readout cuando una cadena envuelve a mitad de secuencia (p in 1..8)?",
    "null_hypothesis": "El readout de 2 celdas con posicion p in {1,2,4,5,6} no imprime str(9-p)+'9' (H0).",
    "metric": "out == str(9-p) + '9'",
    "variant": "transicion con bloque MOV2 dedicado (usado 1 vez); sin gateway",
    "history": {
        "v1_MOVED_compartido_sin_restore": "0/5; digito extra 9-(p-1). Traza: MOVED[C] op=INV44",
        "v2_MOVED_con_R_MOVED": "0/5; racha (p=6 -> '34567899')",
        "v3_gateway_precargado": "0/5; caida al bloque de etiqueta siguiente (p=6 -> '4567898')",
        "v4_MOV2_dedicado": f"{len(ok)}/{len(rows)}",
    },
    "rows": rows,
    "n_match": len(ok),
    "claim": ("MIDWRAP_CHAINING_VIA_DEDICATED_MOVED=DEMONSTRATED (2 celdas, p in {1,2,4,5,6})"
              if len(ok) == len(rows) else "MIDWRAP_CHAINING=NOT_DEMONSTRATED"),
    "root_cause": "El bloque MOVED compartido se agota: `MOVED loop` se usa 3 veces por tick y el readout no re-pasa por `loop: R_MOVED`, de modo que su celda movd llega cifrada (traza v1: MOVED[C] op=INV44) y el jmp cae en la llamada siguiente de la cadena N1.",
    "scope": "Oraculo malbolge.py; 2 celdas; el readout de 5 celdas sigue sin cerrar.",
    "not_demonstrated": ["5 celdas", "mod59049 real", "segundo interprete", "p=3,7,8 (LMAO rechaza el ciclo)"],
}
out = WORK / "readout_midwrap_v4_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\n{len(ok)}/{len(rows)} match")
print(f"REPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")