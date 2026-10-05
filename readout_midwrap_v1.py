#!/usr/bin/env python3
"""Traza por paso para localizar el digito extra cuando la cadena envuelve a mitad.

Replica malbolge.run() paso a paso registrando los eventos no-nop, con el MISMO
orden que el original (el auto-cifrado se aplica despues del salto, sobre la
celda destino cuando op==4).

H0: el digito extra 9-(p-1) viene de que la cadena que envuelve a mitad deja
celdas ejecutadas (cifradas) y el salto MOVED entra en la celda equivocada.
METRICA: para la variante de 2 celdas con celda de parada de p posiciones,
out == str(9-p) + '9'.  Si out == str(9-p) + str(10-p), el segundo digito
confirma que la segunda cadena ve la celda en posicion p-1.
TRAZA: registro completo de eventos (jmp/out/movd/rot/crazy/hlt) con c, d, a.
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
OPC = {4: "jmp", 5: "out", 23: "in", 39: "rot", 40: "movd", 62: "crazy", 68: "nop", 81: "hlt"}

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402


def traced(source: str, max_steps: int = MAX_STEPS):
    mem = M.load_memory(source)
    a = c = d = 0
    out = bytearray()
    steps = 0
    ev: list[dict] = []
    while steps < max_steps:
        steps += 1
        op = (mem[c] + c) % 94
        rec = None if op == 68 else {"s": steps, "c": c, "d": d, "op": OPC.get(op, f"INVALID_{op}"),
                                     "mc": mem[c], "md": mem[d], "a": a}
        if op == 4:
            c = mem[d]
        elif op == 5:
            out.append(a % 256)
            if rec:
                rec["OUT"] = a % 256
        elif op == 23:
            a = M.EOF_VALUE
        elif op == 39:
            v = mem[d]
            mem[d] = v // 3 + (v % 3) * (3 ** 9)
            a = mem[d]
        elif op == 40:
            d = mem[d]
        elif op == 62:
            mem[d] = M.crazy(a, mem[d])
            a = mem[d]
        elif op == 81:
            if rec:
                rec["HLT"] = True
            ev.append(rec)
            return "HALTED", steps, bytes(out), ev
        elif op not in OPC:
            # el interprete de referencia no tiene else: una instruccion invalida
            # se ejecuta como no-op y la celda se cifra igual.
            if rec:
                rec["invalid_noop"] = True
        if 33 <= mem[c] <= 126:
            if rec:
                rec["enc_after_at_c"] = c
            mem[c] = M._ENCRYPT[mem[c]]
        if rec:
            ev.append(rec)
        c = (c + 1) % M.MEMORY_SIZE
        d = (d + 1) % M.MEMORY_SIZE
    return "OUT_OF_FUEL", steps, bytes(out), ev


def cyc(n: int) -> str:
    return "\t" + "/".join(["Nop"] * (n - 1) + ["MovD"]) + "\n\tJmp\n"


def build(p: int) -> str:
    code = ".CODE\n" + "".join(f"{n}:\n{cyc(9)}\n" for n in ("N1", "N2"))
    code += f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\n"
             "HALT:\n\tHlt\n\nMOVED:\n\tMovD/Nop\n\tJmp\n")
    L = ["\tloop:", "\tR_MOVED", "\tENTRY:",
         "\tN1 w1", "\tS st1", "\tMOVED loop",
         "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
         "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
         "\tst1:", "\tMOVED read_N1",
         "\tread_N1:"]
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\ta{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tMOVED read_N2"]
    L.append("\tread_N2:")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for p in range(1, 9):
    src = WORK / f"tr2_p{p}.hell"
    mb = WORK / f"tr2_p{p}.mb"
    src.write_text(build(p))
    cp = subprocess.run([str(LMAO), "-o", str(mb), str(src)],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"p": p, "predicted": f"{9-p}9", "compile_rc": cp.returncode,
           "stderr": cp.stderr.strip()[:160]}
    if cp.returncode == 0:
        status, steps, out, ev = traced(mb.read_text())
        row.update({"status": status, "steps": steps, "out": out.decode("latin-1"),
                    "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                    "mb_sha256": hashlib.sha256(mb.read_bytes()).hexdigest(),
                    "match": out.decode("latin-1") == f"{9-p}9"})
        if p == 2:
            (WORK / "trace_p2_events.json").write_text(json.dumps(ev, indent=1))
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

doc = {
    "format": "malbolge-lmao-readout-midwrap-trace/1",
    "question": "Por que una cadena que envuelve a mitad de secuencia (p in 1..8) inserta un digito extra 9-(p-1)?",
    "null_hypothesis": "Celdas ejecutadas antes del wrap quedan cifradas y el salto MOVED entra en la celda equivocada.",
    "metric": "out == str(9-p) + '9' para la variante de 2 celdas con parada de p posiciones",
    "vm_facts_used": [
        "malbolge.py:127-128 toda celda ejecutada se auto-cifra, y el cifrado se aplica DESPUES del salto (sobre la celda destino si op==4)",
        "malbolge.py:102-103 jmp: c = mem[d]",
        "malbolge.py:116-117 movd: d = mem[d]",
    ],
    "rows": rows,
    "n_match": sum(1 for r in rows if r.get("match")),
    "claim": ("MIDWRAP_CHAIN_OK" if all(r.get("match") for r in rows)
              else "MIDWRAP_CHAIN_BROKEN (digito extra = 9-(p-1) = lectura de la celda en posicion p-1)"),
    "trace_file": "/tmp/lmao_work/trace_p2_events.json (p=2)",
    "scope": "Oraculo malbolge.py; solo 2 celdas; la correccion del readout de 5 celdas NO esta cerrada.",
}
out = WORK / "readout_midwrap_trace_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\nREPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")