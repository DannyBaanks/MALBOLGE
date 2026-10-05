#!/usr/bin/env python3
"""FASE 4: por que falla la transferencia en el contexto del wrap (p=2).

Medido en el microexperimento (FASE 2b/3):
  - `MOVED <target>` transfiere a un target conocido POR DIRECCION: sobrevive a
    3 bloques SEED intercalados (moved_seed -> 'XC'). La celda de operando se
    lee con `movd` (d = mem[d]) y luego el `jmp` usa ese d. DEPENDE de d.
  - Una linea de datos con una etiqueta desnuda (bare) NO transfiere: 'X' y halt.
  - El salto entre code blocks (OUT -> MOVED) va por palabra encadenada y es
    d-independiente.

Medido en la traza de v1 (p=2): tras el wrap, d = 58904 y el bloque a_k arranca
en 58905 (=a7). Las 3 lineas de datos de a_k ocupan 6 celdas (2 por linea), luego
el movd de MOVED corre con d = 58912, que es la celda de OPERANDO de la linea
MOVED (no la anterior): d queda desplazado +1 y el jmp lee la celda que no es.

VARIANTES p=2 (gate 4A: OUT '7' correcto -> transfer -> read_N2 sin '8' extra):
  v4   MOV2 read_N2                 (baseline v4)
  v5a  ?- + MOV2 read_N2            (desplaza el operando una celda)
  v5b  R_MOV2 + MOV2 read_N2        (restaura el bloque)
  v5c  MOV2 read_N2 + MOV2 read_N2  (doble linea: consume el desfase de dos modos)
METRICA: out == '79' (D1=9-p=7 correcto, D2=9) y el bloque a_{k+1} NO se ejecuta.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work"
                     )
MAX_STEPS = 200_000

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402

OPS = {4: "jmp", 5: "out", 23: "in", 39: "rot", 40: "movd", 62: "crazy", 81: "hlt"}


def cyc(n: int) -> str:
    return "\t" + "/".join(["Nop"] * (n - 1) + ["MovD"]) + "\n\tJmp\n"


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


def build(p: int, variant: str) -> str:
    code = ".CODE\n" + "".join(f"{n}:\n{cyc(9)}\n" for n in ("N1", "N2"))
    code += f"S:\n{cyc(p)}\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\n"
             "HALT:\n\tHlt\n\nMOVED:\n\tMovD/Nop\n\tJmp\n\nMOV2:\n\tMovD/Nop\n\tJmp\n")
    tail = {"v4": ["\tMOV2 read_N2"],
            "v5a": ["\t?-", "\tMOV2 read_N2"],
            "v5b": ["\tR_MOV2", "\tMOV2 read_N2"],
            "v5c": ["\tMOV2 read_N2", "\tMOV2 read_N2"]}[variant]
    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         "\tN1 w1", "\tS st1", "\tMOVED loop",
         "\tw1:", "\tN2 w2", "\tS st1", "\tMOVED loop",
         "\tw2:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
         "\tst1:", "\tMOV2 read_N1", "\tread_N1:"]
    L += [f"\tN1 a{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\ta{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT"] + tail
    L.append("\tread_N2:")
    L += [f"\tN2 b{k}" for k in range(1, 10)]
    for k in range(1, 10):
        L += [f"\tb{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


rows = []
for variant in ("v4", "v5a", "v5b", "v5c"):
    src = WORK / f"xfer4_{variant}.hell"
    mb = WORK / f"xfer4_{variant}.mb"
    src.write_text(build(2, variant))
    cp = subprocess.run([str(LMAO), "-d", "-o", str(mb), str(src)],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"variant": variant, "p": 2, "expected": "79", "compile_rc": cp.returncode,
           "stderr": cp.stderr.strip()[:160],
           "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        st, steps, out, ev = traced(mb.read_text())
        row.update({"status": st, "steps": steps, "out": out.decode("latin-1"),
                    "match": out.decode("latin-1") == "79"})
        lab = {}
        for ln in (WORK / f"xfer4_{variant}.dbg").read_text().splitlines():
            m = re.match(r"^(\w+): (CODE|DATA) (\d+)$", ln.strip())
            if m:
                lab.setdefault(int(m.group(3)), f"{m.group(1)}[{m.group(2)[0]}]")
        row["labels"] = {k: v for k, v in sorted(lab.items())
                         if v.startswith(("a", "b", "read", "N", "S")) or v.startswith(("MOV", "ROT", "OUT", "HALT", "st", "w", "loop"))}
        outs = [i for i, e in enumerate(ev) if "OUT" in e]
        if outs:
            i = outs[0]
            row["trace_after_first_digit"] = [
                {k: v for k, v in e.items() if k in ("s", "c", "d", "op", "md", "a", "OUT", "HLT")}
                for e in ev[i:i + 14]]
            row["trace_lab"] = {e["c"]: lab.get(e["c"], "") for e in ev[i:i + 14]}
    rows.append(row)
    print(json.dumps({k: v for k, v in row.items()
                      if k not in ("labels", "trace_after_first_digit", "trace_lab")},
                     ensure_ascii=False))

for row in rows:
    if row.get("trace_after_first_digit"):
        print(f"\n=== {row['variant']} (p=2) out={row['out']!r} : 14 eventos tras el primer digito ===")
        for e in row["trace_after_first_digit"]:
            lbl = row["trace_lab"].get(e["c"], "")
            extra = f" OUT={e['OUT']!r}" if "OUT" in e else ""
            if e.get("HLT"):
                extra += " HLT"
            print(f"  s={e['s']:<6} c={e['c']:<6} {lbl:<10} d={e['d']:<6} op={e['op']:<6} md={e['md']:<6} a={e['a']:<6}{extra}")

ok = [r for r in rows if r.get("match")]
doc = {
    "format": "malbolge-lmao-xfer-midwrap/1",
    "question": "Por que la transferencia medida en el microexperimento no funciona en el contexto del wrap (p=2)?",
    "metric": "out == '79'",
    "variants": {r["variant"]: r.get("out", f"COMPILE_FAIL rc={r['compile_rc']}") for r in rows},
    "rows": rows,
    "n_match": len(ok),
    "claim": ("XFER_MIDWRAP=DEMONSTRATED_LOCALLY via " + ",".join(r["variant"] for r in ok)
              if ok else "XFER_MIDWRAP=NOT_DEMONSTRATED"),
    "surface_facts": [
        "MOVED <target> transfiere por direccion (sobrevive 3 bloques SEED intercalados) pero su movd lee mem[d]: depende de la alineacion de d",
        "el salto entre code blocks consecutivos va por palabra encadenada y es d-independiente",
        "una linea de datos con etiqueta desnuda NO transfiere (microtest bare -> 'X' + halt)",
    ],
    "scope": "p=2 solamente; oraculo malbolge.py.",
    "not_demonstrated": ["matriz p in {1,2,4,5,6}", "readout 5 celdas", "mod59049 real", "segundo interprete"],
}
out = WORK / "xfer_midwrap_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\nREPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")