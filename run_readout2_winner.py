#!/usr/bin/env python3
"""Readout de 2 celdas dentro de Malbolge -- configuracion ganadora (4/5).

Se persistio como archivo para cerrar el hueco de procedencia: los barridos de
calibracion corrieron como heredocs inline. Este generador reproduce las fuentes
.c3x/.shiftoff con los mismos sha256 (verificado).

CONFIGURACION GANADORA:
  - la celda de parada S se llama DESPUES de la celda de cascada en el tick
  - una llamada de advanceo (`N1 a9`) antes de la cadena de N1
  - sin llamada de advanceo antes de la cadena de N2
  - transferencia con `MOV2 <target>` (bloque dedicado, un uso por transicion)

MEDIDO: out == str(9-p) + '9' para p in {2,4,5,6}. p=1 falla (celda de parada de
1 posicion: envuelve en el primer tick, ya despues de la llamada a N1).
Con orden invertido (S antes que N1) p=1 y p=2 pasan y p>=4 fallan: las dos
configuraciones son complementarias y ninguna sola da 5/5.

NO escala a 3 celdas: con la misma receta las cadenas 1 y 2 leen bien y la 3 cae
en fallthrough (ver three_cell_report.json).
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work")
sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402
PS = (1, 2, 4, 5, 6)


def cyc(n: int) -> str:
    return "\t" + "/".join(["Nop"] * (n - 1) + ["MovD"]) + "\n\tJmp\n"


def build(p: int) -> str:
    code = ".CODE\n" + "".join(f"{x}:\n{cyc(9)}\n" for x in ("N1", "N2")) + f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\nHALT:\n\tHlt\n\n"
             "MOVED:\n\tMovD/Nop\n\tJmp\n\nMOV2:\n\tMovD/Nop\n\tJmp\n")
    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         "\tN1 w1", "\tS st1", "\tMOVED loop",
         "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
         "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
         "\tst1:", "\tR_MOV2", "\tMOV2 read_N1",
         "\tread_N1:", "\tN1 a9"]
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\ta{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tMOV2 read_N2"]
    L.append("\tread_N2:")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for p in PS:
    tag = f"readout2_p{p}"
    src = WORK / f"{tag}.hell"
    mb = WORK / f"{tag}.mb"
    src.write_text(build(p))
    cp = subprocess.run([str(LMAO), "-o", str(mb.resolve()), str(src.resolve())],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"p": p, "expected": f"{9-p}9", "compile_rc": cp.returncode,
           "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        st, steps, out = M.run(mb.read_text(), b"", 300_000)
        row.update({"status": st, "steps": steps, "out": out.decode("latin-1"),
                    "match": out.decode("latin-1") == f"{9-p}9"})
    rows.append(row)
    print(json.dumps({k: v for k, v in row.items() if "sha256" not in k}, ensure_ascii=False))

n = sum(1 for r in rows if r.get("match"))
doc = {
    "format": "malbolge-lmao-readout2-winner/1",
    "recipe": "S despues de N1 en el tick; una llamada de advanceo antes de la cadena N1; ninguna antes de N2; transferencia con MOV2 dedicado",
    "metric": "out == str(9-p) + '9'",
    "rows": rows,
    "n_match": n,
    "n_domain": len(PS),
    "claim": ("READOUT2_MIDWRAP=DEMONSTRATED para p in {2,4,5,6}; p=1 NOT_DEMONSTRATED"
              if n == len(PS) - 1 else "READOUT2_MIDWRAP=NOT_DEMONSTRATED"),
    "not_demonstrated": ["p=1", "3 o mas celdas", "readout 5 celdas", "mod59049 real",
                         "segundo interprete", "p=3,7,8"],
}
out = WORK / "readout2_winner_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\n{n}/{len(PS)}  REPORT sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
