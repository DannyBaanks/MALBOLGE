#!/usr/bin/env python3
"""Barrido de variantes para cerrar la transferencia mid-wrap (p=2 primero).

Conocimiento medido que guia el diseno:
- La llamada `N1 a_k` usa el movd del ciclo para cargar d = operando de a_k. Si d
  no esta alineado en la celda de la llamada, la llamada misma falla.
- El wrap salta al bloque a_k; la longitud de ruta wrap -> transfer es la misma
  para todo k, y tanto d como la direccion del bloque avanzan 1 celda por k, luego
  la DIFERENCIA deberia ser constante. Empiricamente no lo es: el readout falla.
- k es una etiqueta de compilacion: cualquier correccion por k es estatica y NO
  exige conocer p en runtime.

VARIANTES (todas sobre la estructura v6_pre, que ya mide 9-p en el primer digito):
  A padN   : N celdas '?' antes de la linea MOV2 (desplazan d en +N)
  B rN     : 'R_MOV2' + N celdas '?' antes de MOV2
  C shared : vuelve al bloque MOVED compartido con R_MOVED en loop:
  D first  : la transferencia se pone PRIMERO en el bloque, antes del ROT
  E lueur  : la linea MOV2 se duplica N veces seguidas

METRICA: out == str(9-p) + '9'  (p=2 -> '79')
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

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402


def cyc(n: int) -> str:
    return "\t" + "/".join(["Nop"] * (n - 1) + ["MovD"]) + "\n\tJmp\n"


def build(p: int, kind: str, n: int = 0) -> str:
    code = ".CODE\n" + "".join(f"{x}:\n{cyc(9)}\n" for x in ("N1", "N2"))
    code += f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\nHALT:\n\tHlt\n\n"
             "MOVED:\n\tMovD/Nop\n\tJmp\n\nMOV2:\n\tMovD/Nop\n\tJmp\n")
    xfer_block = f"MOV2 read_N2"
    if kind == "A":
        xfer_block = "\t?" * n + "\tMOV2 read_N2"
    elif kind == "B":
        xfer_block = "\tR_MOV2" + "\t?" * n + "\tMOV2 read_N2"
    elif kind == "C":
        xfer_block = "\t?" * n + "\tMOVED read_N2"
    elif kind == "E":
        xfer_block = "\tMOV2 read_N2" * (n + 1)
    elif kind == "D":
        pass
    else:
        raise ValueError(kind)

    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         "\tN1 w1", "\tS st1", "\tMOVED loop",
         "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
         "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
         "\tst1:", "\tR_MOV2", "\tMOV2 read_N1", "\tread_N1:", "\tN1 a9"]
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L.append(f"\ta{k}:")
        if kind == "D":
            L.append("\tR_MOV2")
            L.append("\tMOV2 read_N2")
            L.append(f"\tROT '{k}'<<1 R_ROT")
            L.append("\tOUT ?- R_OUT")
        else:
            L += [f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT"]
            L += xfer_block.split("\t")[1:] if xfer_block.startswith("\t") else [xfer_block]
    L.append("\tread_N2:")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


CASES = ([("A", n) for n in (0, 1, 2, 3)] + [("B", n) for n in (0, 1, 2)]
         + [("C", n) for n in (0, 1)] + [("D", 0)] + [("E", n) for n in (1, 2)])

rows = []
for kind, n in CASES:
    p = 2
    tag = f"s2_{kind}{n}"
    src = WORK / f"{tag}.hell"
    mb = WORK / f"{tag}.mb"
    src.write_text(build(p, kind, n))
    cp = subprocess.run([str(LMAO), "-o", str(mb.resolve()), str(src.resolve())],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"kind": kind, "n": n, "p": p, "expected": "79", "compile_rc": cp.returncode,
           "stderr": cp.stderr.strip()[:120],
           "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        st, steps, out = M.run(mb.read_text(), b"", MAX_STEPS)
        row.update({"status": st, "steps": steps, "out": out.decode("latin-1"),
                    "match": out.decode("latin-1") == "79", "len": len(out.decode("latin-1"))})
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

winners = [r for r in rows if r.get("match")]
print(f"\nganadores p=2: {[(r['kind'], r['n']) for r in winners]}")
doc = {
    "format": "malbolge-lmao-variant-sweep-p2/1",
    "question": "Que desfase/orden de la linea de transferencia cierra el mid-wrap en p=2?",
    "metric": "out == '79'",
    "rows": rows,
    "n_winners": len(winners),
    "claim": "VARIANT_SWEEP_P2=" + ("WINNER:" + ",".join(f"{r['kind']}{r['n']}" for r in winners)
                                    if winners else "NO_WINNER"),
    "note": "k es etiqueta de compilacion: una correccion por k es estatica y no exige conocer p en runtime.",
}
out = WORK / "variant_sweep_p2.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"REPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")