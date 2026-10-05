#!/usr/bin/env python3
"""FASE 2: microexperimento de transferencia de control a target conocido.

Superficie inspeccionada (vendor/lmao):
  README.md 'HeLL Language Reference': una celda .DATA que contiene SOME_LABEL
  almacena address(SOME_LABEL)-1; el -1 compensa el incremento automatico de D,
  de modo que un Jmp o MovD que cargue esa direccion aterrice en la celda correcta.
  src/prefix.c:43 resolve_prefix_for_dataatom -> R_ valida que el code label de
  destino tenga sucesor; U_ calcula offset relativo y sintetiza RNop virtuales.
  ejemplo_hello_world.hell:259,264 / 282-284 / 300-301: la forma canonica de
  transferencia es  R_<bloque>  seguido de  MOVED <target>  en lineas de datos
  consecutivas. Las 4 variantes fallidas del readout NO usaban ese par.

H0: no existe en LMAO una forma de transferir el control a un target conocido
    que no dependa del fallthrough (H0 para esta superficie).
H1: el par canonico R_MOVED + MOVED <target> transfiere incondicionalmente.

METRICA: out == 'XC'  (X = bloque A, C = bloque C) y NUNCA 'XBC'
         (B = el bloque que, con fallthrough, se ejecutaria entre medias).

VARIANTES:
  m1_canonico : R_MOVED + MOVED C   (la forma de los ejemplos)
  m2_solo     : MOVED C             (sin el restore previo; es lo que uso v4)
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work")
MAX_STEPS = 100_000

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402

CODE = (".CODE\n"
        "ROT:\n\tRot/Nop\n\tJmp\n\n"
        "OUT:\n\tOut/Nop\n\tJmp\n\n"
        "HALT:\n\tHlt\n\n"
        "MOVED:\n\tMovD/Nop\n\tJmp\n")


def build(variant: str) -> str:
    transfer = ["\tR_MOVED", "\tMOVED C"] if variant == "m1_canonico" else ["\tMOVED C"]
    L = ["\tENTRY:",
         "\tROT 'X'<<1 R_ROT",          # bloque A
         "\tOUT ?- R_OUT",
         ] + transfer + [
         "\tB:",
         "\tROT 'B'<<1 R_ROT",          # bloque B: NO debe ejecutarse
         "\tOUT ?- R_OUT",
         "\tROT 'D'<<1 R_ROT",          # segundo caracter de B
         "\tOUT ?- R_OUT",
         "\tC:",
         "\tROT 'C'<<1 R_ROT",          # bloque C: destino
         "\tOUT ?- R_OUT",
         "\tHALT ?-",
         ]
    return CODE + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for variant in ("m2_solo", "m1_canonico"):
    src = WORK / f"xfer_{variant}.hell"
    mb = WORK / f"xfer_{variant}.mb"
    src.write_text(build(variant))
    cp = subprocess.run([str(LMAO), "-d", "-o", str(mb), str(src)],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"variant": variant, "expected": "XC", "compile_rc": cp.returncode,
           "stderr": cp.stderr.strip()[:200],
           "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        st, steps, out = M.run(mb.read_text(), b"", MAX_STEPS)
        row.update({"status": st, "steps": steps,
                    "out": out.decode("latin-1"),
                    "out_hex": out.hex(),
                    "match": out.decode("latin-1") == "XC"})
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

winner = next((r for r in rows if r.get("match")), None)
doc = {
    "format": "malbolge-lmao-xfer-micro/1",
    "question": "Puede LMAO transferir el control a un target conocido sin depender del fallthrough?",
    "null_hypothesis": "No existe tal forma en la superficie inspeccionada (H0).",
    "metric": "out == 'XC' y nunca 'XBC'",
    "fixture": "A imprime 'X'; B imprimiria 'BD'; C imprime 'C' y hace HALT.",
    "surface_inspected": [
        "vendor/lmao/README.md (HeLL Language Reference): SOME_LABEL = address-1; R_LABEL = address+1; U_TARGET ANCHOR = address(TARGET) - distancia; .OFFSET; ENTRY",
        "vendor/lmao/src/prefix.c:43 resolve_prefix_for_dataatom (R_ valida sucesor; U_ calcula offset relativo y sintetiza RNop)",
        "vendor/lmao/src/label.c:81 get_label (CODE vs DATA, un solo destino por etiqueta)",
        "vendor/lmao/src/layout.c:28 add_codeblock_to_memory_layout (reserva la celda previa; restriccion xlat2 de posicion)",
        "vendor/lmao/example_hello_world.hell:259,264,282-284,300-301 (forma canonica R_<bloque> + MOVED <target>)",
    ],
    "rows": rows,
    "winner": winner["variant"] if winner else None,
    "claim": ("XFER_CANONICAL_PAIR=DEMONSTRATED_LOCALLY (R_MOVED + MOVED target)"
              if winner else "XFER_CANONICAL_PAIR=NOT_DEMONSTRATED"),
    "scope": "Microexperimento de 2 bloques; oraculo malbolge.py. No cierra el readout de 5 celdas.",
    "not_demonstrated": ["readout 5 celdas", "mod59049 real", "segundo interprete"],
}
out = WORK / "xfer_micro_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\nREPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")