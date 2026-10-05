#!/usr/bin/env python3
"""Medio-wrap v3: transicion por wrap (gateway precargado), no por MOVED.

Historia medida:
  v1 (MOVED sin restore): el bloque MOVED compartido queda cifrado -> su movd
     deja de ejecutar -> el jmp cae en la llamada siguiente de la cadena N1 y se
     imprime un digito extra 9-(p-1). Traza: s=13464 MOVED[C] op=INV44.
  v2 (MOVED con R_MOVED): peor; imprime una racha de digitos (p=6 -> '34567899').
  v3 (gateway): cada transicion usa una llamada a una celda G precargada a
     posicion 8, cuyo wrap inmediato salta por el camino de wrap (el unico
     mecanismo medido como fiable: w1 -> N2 en mod59049, y la variante 'gateway'
     del test de enlace).

H0: ninguna variante imprime los 2 digitos esperados para todo p in 1..8.
METRICA: out == str(9-p) + '9' para p en {1,2,4,5,6} (los p que LMAO acepta;
          p=3,7,8 dan 'Forced xlat cycle doesn't exist').
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
    code = ".CODE\n" + "".join(f"{n}:\n{cyc(9)}\n" for n in ("N1", "N2", "G"))
    code += f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\n"
             "HALT:\n\tHlt\n\nMOVED:\n\tMovD/Nop\n\tJmp\n")
    L = ["\tENTRY:"]
    L += ["\tG dead_G"] * 8                     # carga: G queda en posicion 8
    L += ["\tloop:", "\tR_MOVED",
          "\tN1 w1", "\tS st1", "\tMOVED loop",
          "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
          "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
          "\tst1:", "\tG read_N1",              # wrap inmediato -> readout
          "\tread_N1:"]
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\ta{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tG read_N2"]
    L.append("\tread_N2:")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    L += ["\tdead_G:", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for p in (1, 2, 4, 5, 6):
    src = WORK / f"tr3_p{p}.hell"
    mb = WORK / f"tr3_p{p}.mb"
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
    "format": "malbolge-lmao-readout-midwrap-trace/3",
    "question": "Se puede encadenar el readout cuando una cadena envuelve a mitad de secuencia (p in 1..8)?",
    "null_hypothesis": "Ninguna variante imprime los 2 digitos esperados en todo p (H0).",
    "metric": "out == str(9-p) + '9'",
    "variant": "gateway precargado (8 llamadas) + transicion por wrap inmediato",
    "history": {
        "v1_MOVED_sin_restore": "0/5; digito extra 9-(p-1); traza: MOVED[C] op=INV44 (celda cifrada, movd no ejecuta)",
        "v2_MOVED_con_R_MOVED": "0/5; racha de digitos (p=6 -> '34567899')",
        "v3_gateway": f"{len(ok)}/{len(rows)}",
    },
    "rows": rows,
    "n_match": len(ok),
    "claim": ("MIDWRAP_CHAINING_VIA_GATEWAY=DEMONSTRATED (2 celdas, p en {1,2,4,5,6})"
              if len(ok) == len(rows) else "MIDWRAP_CHAINING=NOT_DEMONSTRATED"),
    "root_cause_v1": "El bloque MOVED es un bloque de codigo COMPARTIDO por todas las lineas `MOVED`. En mod59049 lo rearma `R_MOVED` en `loop:` cada vuelta del bucle; el readout no tiene vuelta, asi que su 3o uso encuentra la celda cifrada y el movd no ejecuta.",
    "scope": "Oraculo malbolge.py; 2 celdas; el readout de 5 celdas sigue sin cerrar.",
    "not_demonstrated": ["5 celdas", "mod59049 real", "segundo interprete", "p=3,7,8 (LMAO rechaza esos ciclos)"],
}
out = WORK / "readout_midwrap_v3_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\n{len(ok)}/{len(rows)} match")
print(f"REPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")