#!/usr/bin/env python3
"""AISLAR -> ROMPER -> COMPARAR: U_ como transferencia resistente a desalineacion.

FASE 0 (fuente, ya established):
  src/prefix.c:73-87  U_ fija data->number = -m, m = celdas entre la celda U_ y el
                      anchor; sintetiza m RNop virtuales ante el code label destino.
  src/initialize.c:72-87 el valor emitido es addr(TARGET) + number - 1
                      = addr(TARGET) - m - 1.
  Efecto runtime: el jmp que LEE la celda U_ hace c = addr(TARGET)-m, y el
  autoincremento lleva al primer RNop virtual, que camina hasta TARGET.
  => U_ pre-compensa el LADO DEL DESTINO. La celda U_ sigue necesitando que d
     este exactamente en ella para ser leida. H2 predice DESTROYED; se mide.

H1: U_ transfiere a un target conocido de forma relativa (no por contiguidad).
H2: U_ tolera la desalineacion de d que rompe MOVED.  <-- la que importa
H0: la desalineacion se rompe con `?` (una celda de datos que ocupa 1 celda y no
    ejecuta nada) inserta JUSTO ANTES de la linea de transferencia.

MATRIZ: mecanismo {moved, bare, u_} x pad {0,1} x seed {0,3}
METRICA: out == 'XC'  (X = bloque A; B y D nunca deben ejecutarse)
ORACLE: target esperado vs target observado, con trace (pc, d, mem[d], opcode).
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work")
MAX_STEPS = 100_000
OPS = {4: "jmp", 5: "out", 23: "in", 39: "rot", 40: "movd", 62: "crazy", 81: "hlt"}

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402

CODE = (".CODE\n"
        "TC:\n\tRot/Nop\n\tJmp\n\n"          # bloque destino de U_ (code label)
        "ROT:\n\tRot/Nop\n\tJmp\n\n"
        "OUT:\n\tOut/Nop\n\tJmp\n\n"
        "HALT:\n\tHlt\n\n"
        "MOVED:\n\tMovD/Nop\n\tJmp\n")


def traced(source, max_steps=MAX_STEPS):
    mem = M.load_memory(source)
    a = c = d = 0
    out = bytearray()
    steps = 0
    ev = []
    while steps < max_steps:
        steps += 1
        op = (mem[c] + c) % 94
        rec = None if op == 68 else {"s": steps, "c": c, "d": d,
                                     "op": OPS.get(op, f"INV{op}"), "md": mem[d], "a": a}
        if op == 4:
            c = mem[d]
        elif op == 5:
            out.append(a % 256)
            if rec:
                rec["OUT"] = chr(a % 256)
        elif op == 23:
            a = M.EOF_VALUE
        elif op == 39:
            v = mem[d]
            mem[d] = v // 3 + (v % 3) * (3 ** 9)
            a = mem[d]
            if rec:
                rec["rotsrc"] = v
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
        if 33 <= mem[c] <= 126:
            mem[c] = M._ENCRYPT[mem[c]]
        if rec:
            ev.append(rec)
        c = (c + 1) % M.MEMORY_SIZE
        d = (d + 1) % M.MEMORY_SIZE
    return "OUT_OF_FUEL", steps, bytes(out), ev


def seed_block(tag: str) -> list[str]:
    ch = {"s1": "1", "s2": "2", "s3": "3"}[tag]
    return [f"\t{tag}:", f"\tROT '{ch}'<<1 R_ROT", "\tOUT ?- R_OUT"]


def build(mech: str, pad: int, seed: int) -> str:
    transfer = {"moved": ["\tMOVED C"],
                "bare": ["\tC"],
                "u_": ["\tU_TC ANCHOR"]}[mech]
    L = ["\tENTRY:", "\tROT 'X'<<1 R_ROT", "\tOUT ?- R_OUT"]
    L += ["\t?"] * pad                     # perturbacion de d: 1 celda por '?'
    L += transfer
    for t in ("s1", "s2", "s3")[:seed]:
        L += seed_block(t)
    L += ["\tANCHOR:", "\tC0"]             # anchor de U_ (debe seguir en el mismo bloque)
    L += ["\tB:", "\tROT 'B'<<1 R_ROT", "\tOUT ?- R_OUT",
          "\tROT 'D'<<1 R_ROT", "\tOUT ?- R_OUT"]
    L += ["\tC:", "\tROT 'C'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return CODE + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for mech in ("moved", "bare", "u_"):
    for pad in (0, 1):
        for seed in (0, 3):
            tag = f"u_{mech}_pad{pad}_seed{seed}"
            src = WORK / f"{tag}.hell"
            mb = WORK / f"{tag}.mb"
            src.write_text(build(mech, pad, seed))
            cp = subprocess.run([str(LMAO), "-d", "-o", str(mb.resolve()), str(src.resolve())],
                                capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
            row = {"case": tag, "mech": mech, "pad": pad, "seed": seed,
                   "expected": "XC", "compile_rc": cp.returncode,
                   "stderr": cp.stderr.strip()[:180],
                   "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
            if cp.returncode == 0:
                row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
                st, steps, out, ev = traced(mb.read_text())
                row.update({"status": st, "steps": steps,
                            "out": out.decode("latin-1"),
                            "match": out.decode("latin-1") == "XC"})
                # trace: 6 eventos alrededor del 2o OUT (o del final si no hay 2o)
                outs = [i for i, e in enumerate(ev) if "OUT" in e]
                anchor = outs[1] if len(outs) > 1 else (outs[0] if outs else len(ev) - 1)
                row["trace_at_transfer"] = [
                    {k: v for k, v in e.items() if k in ("s", "c", "d", "op", "md", "a", "OUT", "HLT")}
                    for e in ev[max(0, anchor - 7):anchor + 4]]
            rows.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != "trace_at_transfer"},
                             ensure_ascii=False))

print("\n=== trazas de la segunda salida (o del final), por caso ===")
for row in rows:
    if not row.get("trace_at_transfer"):
        continue
    print(f"\n--- {row['case']}  out={row['out']!r} ---")
    for e in row["trace_at_transfer"]:
        extra = f" OUT={e['OUT']!r}" if "OUT" in e else ""
        if e.get("HLT"):
            extra += " HLT"
        print(f"  s={e['s']:<5} c={e['c']:<6} d={e['d']:<6} op={e['op']:<6} md={e['md']:<6} a={e['a']:<6}{extra}")

doc = {
    "format": "malbolge-lmao-u-offset/1",
    "question": "Puede U_ transferir control en una condicion de offset/desalineacion de d donde MOVED falla?",
    "hypotheses": {
        "H1_U_is_relative_transfer": "DEMONSTRATED si llega a C con y sin SEED",
        "H2_U_tolerates_d_misalignment": "DEMONSTRATED si con pad=1 sigue llegando a C mientras MOVED no",
    },
    "source_semantics": {
        "prefix.c:73-87": "U_ fija number=-m y sintetiza m RNop virtuales ante el code label destino",
        "initialize.c:72-87": "valor emitido = addr(TARGET) + number - 1 = addr(TARGET) - m - 1",
        "runtime": "el jmp que lee la celda U_ hace c=addr(TARGET)-m; el autoincremento entra al primer RNop virtual y camina hasta TARGET",
        "prediccion": "U_ pre-compensa el destino, no el punto de entrada de d; la celda U_ sigue exigiendo d en su direccion",
    },
    "metric": "out == 'XC' (nunca 'XBC'/'XBDC'/'XBCD')",
    "rows": rows,
    "n_match": sum(1 for r in rows if r.get("match")),
    "by_mech_pad": {f"{r['mech']}_pad{r['pad']}_seed{r['seed']}": r.get("out", "COMPILE_FAIL")
                    for r in rows},
}
out = WORK / "u_offset_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\nREPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")