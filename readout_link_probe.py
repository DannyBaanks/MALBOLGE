#!/usr/bin/env python3
"""Aisla el mecanismo de ENCADENADO del readout (2 celdas, 3 variantes).

La pregunta minima: tras imprimir un digito, como se ejecuta la cadena de la
celda siguiente?

  bare     : continuacion = etiqueta desnuda en fallthrough  (patron no probado)
  gateway  : continuacion = llamada a gateway precargado a 8 -> wrap inmediato
             -> salta por el camino probado (wrap target) a la cadena siguiente
  moved    : continuacion = MOVED <etiqueta de la cadena siguiente>

H0: ninguna de las tres imprime '99' (el encadenado no es posible).
METRICA: out == '99'.
CONTROL: chain8 (8 llamadas no envuelven) ya descarta que el wrap sea trivial.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work")
MAX_STEPS = 2_000_000

sys.path.insert(0, str(ROOT))
import malbolge  # noqa: E402

CYC = "\tNop/Nop/Nop/Nop/Nop/Nop/Nop/Nop/MovD\n\tJmp\n"
CODE = ".CODE\n" + "".join(f"{n}:\n{CYC}\n" for n in ("N1", "N2", "G")) + (
    "ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\nHALT:\n\tHlt\n\nMOVED:\n\tMovD/Nop\n\tJmp\n")


def chain(cell: str, out_char_from_wrap: str = "k") -> list[str]:
    """Cadena de 9 llamadas; el wrap imprime el digito k y ejecuta `cont`."""
    L = []
    for k in range(1, 10):
        L.append(f"\t{cell} c{cell}_{k}")
    for k in range(1, 10):
        L.append(f"\tc{cell}_{k}:")
        L.append(f"\tROT '{k}'<<1 R_ROT")
        L.append("\tOUT ?- R_OUT")
        L.append(out_char_from_wrap)
    return L


def build(variant: str) -> str:
    L = ["\tENTRY:"]
    if variant == "gateway":
        for _ in range(8):
            L.append("\tG dead")
        L.append("\tread_N1:")
        L += chain("N1", "\tG r2_first")
        L.append("\tr2_first:")
        L += chain("N2", "\tHALT ?-")
        L.append("\tdead:")
        L.append("\tHALT ?-")
    elif variant == "bare":
        L.append("\tread_N1:")
        L += chain("N1", "\tread_N2")
        L.append("\tread_N2:")
        L += chain("N2", "\tHALT ?-")
    elif variant == "moved":
        L.append("\tread_N1:")
        L += chain("N1", "\tMOVED read_N2")
        L.append("\tread_N2:")
        L += chain("N2", "\tHALT ?-")
    else:
        raise ValueError(variant)
    return CODE + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for variant in ("bare", "gateway", "moved"):
    src = WORK / f"link_{variant}.hell"
    mb = WORK / f"link_{variant}.mb"
    src.write_text(build(variant))
    cp = subprocess.run([str(LMAO), "-o", str(mb), str(src)],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"variant": variant, "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
           "compile_rc": cp.returncode, "compile_stderr": cp.stderr.strip()[:200]}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        res = malbolge.run(mb.read_text(), b"", MAX_STEPS)
        row["oracle_raw"] = repr(res)
        row["out_hex"] = res[2].hex() if isinstance(res[2], (bytes, bytearray)) else None
        row["out"] = res[2].decode("latin-1") if isinstance(res[2], (bytes, bytearray)) else None
        row["match"] = row["out"] == "99"
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

doc = {
    "format": "malbolge-lmao-readout-link/1",
    "question": "Tras imprimir un digito, como se ejecuta la cadena de la celda siguiente?",
    "null_hypothesis": "Ninguna variante imprime '99': el encadenado de readout no es posible (H0).",
    "metric": "out == '99' (2 celdas leidas, ambas en posicion 0)",
    "control": "chain8: 8 llamadas no envuelven (wrap no trivial)",
    "rows": rows,
    "n_match": sum(1 for r in rows if r.get("match")),
    "winner": next((r["variant"] for r in rows if r.get("match")), None),
    "claim": "READOUT_CHAINING=" + ("DEMONSTRATED via " + next(
        (r["variant"] for r in rows if r.get("match")), "NONE") + " en 2 celdas"
        if any(r.get("match") for r in rows) else "READOUT_CHAINING=NOT_DEMONSTRATED"),
    "scope": "Oraculo malbolge.py; solo el mecanismo de encadenado, no el readout de 5 celdas.",
    "not_demonstrated": ["5 celdas", "segundo interprete", "mod59049 real"],
}
out = WORK / "readout_link_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\nREPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")