#!/usr/bin/env python3
"""Variante F: pre-call en TODAS las cadenas. Barrido p in {1,2,4,5,6}.

Medido en el barrido anterior (p=2): las variantes A0, C0, E1 y E2 dan '78' --
dos digitos, halt limpio, primer digito correcto (9-p=7). Es decir la
transferencia `MOV2 read_N2` YA funciona y no hay fallthrough. El defecto
restante: la segunda cadena lee la posicion p2+1 (imprime 8 en vez de 9 cuando
p2=0), el mismo desfase de una unidad que la primera cadena tenia en sentido
inverso y que se corrigio con una llamada de advanceo.

F: antepone `N2 b9` (llamada de advanceo) tambien a la segunda cadena.
  Si la segunda cadena mide p2+1, el advanceo la deja en p2 -> imprime 9-p2.
  b9 como etiqueta de la llamada de advanceo cubre el caso p2=8 sin caso especial.

METRICA: out == str(9-p) + '9'
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work")
MAX_STEPS = 300_000
PS = (1, 2, 4, 5, 6)

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402


def cyc(n: int) -> str:
    return "\t" + "/".join(["Nop"] * (n - 1) + ["MovD"]) + "\n\tJmp\n"


def build(p: int, pre2: bool) -> str:
    code = ".CODE\n" + "".join(f"{x}:\n{cyc(9)}\n" for x in ("N1", "N2"))
    code += f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\nHALT:\n\tHlt\n\n"
             "MOVED:\n\tMovD/Nop\n\tJmp\n\nMOV2:\n\tMovD/Nop\n\tJmp\n")
    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         "\tN1 w1", "\tS st1", "\tMOVED loop",
         "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
         "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
         "\tst1:", "\tR_MOV2", "\tMOV2 read_N1", "\tread_N1:", "\tN1 a9"]
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\ta{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tMOV2 read_N2"]
    L.append("\tread_N2:")
    if pre2:
        L.append("\tN2 b9")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for pre2 in (False, True):
    for p in PS:
        tag = f"vF{'pre2' if pre2 else 'plain'}_p{p}"
        src = WORK / f"{tag}.hell"
        mb = WORK / f"{tag}.mb"
        src.write_text(build(p, pre2))
        cp = subprocess.run([str(LMAO), "-o", str(mb.resolve()), str(src.resolve())],
                            capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
        row = {"variant": tag, "pre2": pre2, "p": p, "expected": f"{9-p}9",
               "compile_rc": cp.returncode, "stderr": cp.stderr.strip()[:120],
               "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        if cp.returncode == 0:
            row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
            st, steps, out = M.run(mb.read_text(), b"", MAX_STEPS)
            row.update({"status": st, "steps": steps, "out": out.decode("latin-1"),
                        "match": out.decode("latin-1") == f"{9-p}9"})
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

for v in ("vFplain", "vFpre2"):
    got = sum(1 for r in rows if r["variant"].startswith(v) and r.get("match"))
    print(f"{v}: {got}/{len(PS)}")

doc = {
    "format": "malbolge-lmao-variant-F/1",
    "question": "Anadiendo la llamada de advanceo a la segunda cadena, se cierra el readout de 2 celdas?",
    "metric": "out == str(9-p) + '9' para p in {1,2,4,5,6}",
    "rows": rows,
    "n_plain": sum(1 for r in rows if r["variant"].startswith("vFplain") and r.get("match")),
    "n_pre2": sum(1 for r in rows if r["variant"].startswith("vFpre2") and r.get("match")),
    "claim": ("READOUT2_MIDWRAP=DEMONSTRATED_LOCALLY (5/5)" if
              sum(1 for r in rows if r["variant"].startswith("vFpre2") and r.get("match")) == len(PS)
              else "READOUT2_MIDWRAP=NOT_DEMONSTRATED"),
    "note": "El avanceo por cadena es estatico: cada etiqueta k es constante de compilacion; no se requiere conocer p en runtime.",
    "not_demonstrated": ["readout 5 celdas", "mod59049 real", "segundo interprete", "p=3,7,8"],
}
out = WORK / "variant_F_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"REPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")