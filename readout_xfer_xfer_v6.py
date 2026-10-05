#!/usr/bin/env python3
"""FASE 4b + FASE 5: transferencia canonical + correccion del desfase de una unidad.

DOS DEFECTOS SEPARADOS, ambos medidos:

(1) TRANSFERENCIA DE CONTROL. La forma canonica de los ejemplos
    (example_hello_world.hell:259,264 / 282-284 / 300-301) es
        R_<bloque>
        MOVED <target>
    Es decir, el restore va en la linea ANTERIOR, como celda propia. Medido en
    este turno: v4 (`MOV2 read_N2` solo) -> el movd del bloque no esta disponible
    o cae mal; v5b (`R_MOV2` + `MOV2 read_N2`) -> traza s=13861/13862 demuestra
    que el jmp lee la palabra encadenada de read_N2 y aterriza en N2[C], sin
    ejecutar el bloque a_{k+1}. Salida de 2 cifras para 2 celdas: sin fallthrough.

(2) DESFASE DE UNA UNIDAD EN EL DIGITO. La cadena de 9 llamadas lee la posicion
    p-1, no p (p=2 -> imprime 8 en vez de 7). Correccion: anteponer UNA llamada
    deAdvance con etiqueta a9. Si esa llamada envuelve (p=8) salta a a9, que
    imprime 9, que es el digito correcto para p=8; si no envuelve, la celda queda
    en p+1 y la cadena de 9 mide (8-p) -> imprime 8-p = 9-p. No hace falta caso
    especial para p=8.

METRICA: out == str(9-p) + '9'.
DOMINIO: p in {1,2,4,5,6}  (p=3,7,8 los rechaza LMAO: 'Forced xlat cycle doesn't exist').
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

PRED = lambda p: f"{9-p}9"          # noqa: E731
PS = (1, 2, 4, 5, 6)


def cyc(n: int) -> str:
    return "\t" + "/".join(["Nop"] * (n - 1) + ["MovD"]) + "\n\tJmp\n"


def build(p: int, pre_call: bool) -> str:
    code = ".CODE\n" + "".join(f"{n}:\n{cyc(9)}\n" for n in ("N1", "N2"))
    code += f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\n"
             "HALT:\n\tHlt\n\nMOVED:\n\tMovD/Nop\n\tJmp\n\nMOV2:\n\tMovD/Nop\n\tJmp\n")
    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         "\tN1 w1", "\tS st1", "\tMOVED loop",
         "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
         "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
         "\tst1:", "\tR_MOV2", "\tMOV2 read_N1", "\tread_N1:"]
    if pre_call:
        L.append("\tN1 a9")            # advanceo previo: corrige el desfase de 1
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\ta{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT",
              "\tR_MOV2", "\tMOV2 read_N2"]
    L.append("\tread_N2:")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for pre_call in (False, True):
    for p in PS:
        tag = f"v6{'pre' if pre_call else 'nopre'}_p{p}"
        src = WORK / f"{tag}.hell"
        mb = WORK / f"{tag}.mb"
        src.write_text(build(p, pre_call))
        cp = subprocess.run([str(LMAO), "-o", str(mb), str(src)],
                            capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
        row = {"variant": "v6_pre" if pre_call else "v5b", "p": p,
               "expected": PRED(p), "compile_rc": cp.returncode,
               "stderr": cp.stderr.strip()[:120],
               "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        if cp.returncode == 0:
            row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
            st, steps, out = M.run(mb.read_text(), b"", MAX_STEPS)
            row.update({"status": st, "steps": steps, "out": out.decode("latin-1"),
                        "match": out.decode("latin-1") == PRED(p)})
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

for tag in ("v5b", "v6_pre"):
    got = sum(1 for r in rows if r["variant"] == tag and r.get("match"))
    tot = sum(1 for r in rows if r["variant"] == tag)
    print(f"\n{tag}: {got}/{tot}")

doc = {
    "format": "malbolge-lmao-xfer-midwrap/2",
    "question": "Con transferencia canonica (R_MOV2 + MOVED target) y la correccion de una unidad, se lee el estado de 2 celdas para p != 0?",
    "null_hypothesis": "Alguna de las dos correcciones no basta y la matriz sigue fallando (H0).",
    "metric": "out == str(9-p) + '9' para p in {1,2,4,5,6}",
    "fix_1_control_flow": "R_MOV2 + MOV2 <target> (forma canonica de los ejemplos). Traza p=2: s=13861 MOV2[C] movd; s=13862 jmp md=58810 -> N2[C]. Sin ejecucion del bloque a_{k+1}.",
    "fix_2_off_by_one": "La cadena de 9 llamadas mide p-1; anteponer una llamada con etiqueta a9 corrige el desfase y cubre p=8 sin caso especial.",
    "rows": rows,
    "n_v5b": sum(1 for r in rows if r["variant"] == "v5b" and r.get("match")),
    "n_v6_pre": sum(1 for r in rows if r["variant"] == "v6_pre" and r.get("match")),
    "claim": ("READOUT2_MIDWRAP=DEMONSTRATED_LOCALLY (5/5 con R_MOV2+MOVED y llamada de advanceo)"
              if sum(1 for r in rows if r["variant"] == "v6_pre" and r.get("match")) == len(PS)
              else "READOUT2_MIDWRAP=NOT_DEMONSTRATED"),
    "scope": "2 celdas; oraculo malbolge.py; p in {1,2,4,5,6}.",
    "not_demonstrated": ["readout 5 celdas", "mod59049 real", "segundo interprete", "p=3,7,8"],
}
out = WORK / "xfer_midwrap_v2_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\nREPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")