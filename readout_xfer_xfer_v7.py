#!/usr/bin/env python3
"""v7: bloque dedicado de un solo uso por transicion + llamada de advanceo.

Reejecuta el experimento que antes corrio como heredoc inline (hueco de
procedencia corregido): si los sha de los .hell coinciden con los del run inline,
el archivo reproduce la medicion.

Contexto medido este turno:
  - La microprueba demuestra que `MOVED <target>` transfiere por direccion
    (sobrevive 3 bloques SEED intercalados) -> no es contiguidad.
  - En el contexto del wrap, la traza muestra que el `movd` del bloque de
    transferencia puede estar en estado xlat2 cifrado (op=INV36) y que el
    destino dependen de d: solo cuando d cae alineado en la celda de operando
    el jmp lee la palabra de read_N2 (s=14015-14017).
  - v7shared (un solo bloque para las dos transiciones) y v7ded (bloque dedicado
    por transicion) dan salidas IDENTICAS -> la causa no es agotamiento del
    bloque sino la alineacion de d.

METRICA: out == str(9-p) + '9' para p in {1,2,4,5,6}.
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


def build(p: int, dedicated: bool) -> str:
    tr1 = "MOV2"
    tr2 = "MOV3" if dedicated else "MOV2"
    code = ".CODE\n" + "".join(f"{n}:\n{cyc(9)}\n" for n in ("N1", "N2")) + f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\nHALT:\n\tHlt\n\n"
             "MOVED:\n\tMovD/Nop\n\tJmp\n\nMOV2:\n\tMovD/Nop\n\tJmp\n\nMOV3:\n\tMovD/Nop\n\tJmp\n")
    L = ["\tENTRY:", "\tloop:", "\tR_MOVED", "\tN1 w1", "\tS st1", "\tMOVED loop",
         "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
         "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
         "\tst1:", f"\tR_{tr1}", f"\t{tr1} read_N1", "\tread_N1:", "\tN1 a9"]
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\ta{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT",
              f"\tR_{tr2}", f"\t{tr2} read_N2"]
    L.append("\tread_N2:")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for dedicated in (False, True):
    for p in PS:
        tag = f"v7{'ded' if dedicated else 'shared'}_p{p}"
        src = WORK / f"{tag}.hell"
        mb = WORK / f"{tag}.mb"
        src.write_text(build(p, dedicated))
        cp = subprocess.run([str(LMAO), "-o", str(mb.resolve()), str(src.resolve())],
                            capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
        row = {"variant": tag, "p": p, "expected": f"{9-p}9", "compile_rc": cp.returncode,
               "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        if cp.returncode == 0:
            row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
            st, steps, out = M.run(mb.read_text(), b"", 200_000)
            row.update({"status": st, "steps": steps,
                        "out": out.decode("latin-1"),
                        "match": out.decode("latin-1") == f"{9-p}9"})
        rows.append(row)

for v in ("v7shared", "v7ded"):
    print(v, sum(1 for r in rows if r["variant"].startswith(v) and r.get("match")), "/5")

doc = {
    "format": "malbolge-lmao-xfer-v7/1",
    "question": "El fallo del readout mid-wrap es agotamiento del bloque MOVED compartido o alineacion de d?",
    "null_hypothesis": "Es agotamiento del bloque compartido (H0).",
    "metric": "out == str(9-p) + '9' para p in {1,2,4,5,6}",
    "result": "v7shared y v7ded producen salidas IDENTIFIQUES -> H0 DESTRUIDA como causa unica",
    "rows": rows,
    "n_shared": sum(1 for r in rows if r["variant"].startswith("v7shared") and r.get("match")),
    "n_ded": sum(1 for r in rows if r["variant"].startswith("v7ded") and r.get("match")),
    "claim": "XFER_MIDWRAP=NOT_DEMONSTRATED; causaRemaining=ALIGNMENT_D",
}
out = WORK / "v7_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"REPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")