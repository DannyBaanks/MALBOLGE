#!/usr/bin/env python3
"""FASE 2b + FASE 3: superficie de transferencia real, con control adversario.

Superficie (README.md HeLL Reference + malbolge.py:102-103):
  - Celda .DATA con SOME_LABEL  = address(SOME_LABEL)-1.
  - El Jmp final de cada code block hace  c = mem[d]; es decir, la celda de
    datos SIGUIENTE acts como palabra encadenada: si contiene una etiqueta, el
    c pasa a esa etiqueta. Esa via no depende de d en absoluto.
  - La linea `MOVED <target>` es un bloque de codigo mas una celda de operando:
    su movd hace d = mem[d] y el jmp siguiente usa ese d. SI depende de d.

FASE 3 (adversario): se interponen bloques SEED entre el punto de transferencia
y C, para comprobar que el salto usa la direccion y no la contiguidad.

H0: ninguna via transfiere a un target conocido sin depender de fallthrough o de
    la alineacion de d (H0 para esta superficie).
METRICA: out == 'XC' y nunca 'XBC' ni 'XBDC'; con SEED presente, out == 'XC'.
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

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402

OPS = {4: "jmp", 5: "out", 23: "in", 39: "rot", 40: "movd", 62: "crazy", 81: "hlt"}


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


CODE = (".CODE\n"
        "ROT:\n\tRot/Nop\n\tJmp\n\n"
        "OUT:\n\tOut/Nop\n\tJmp\n\n"
        "HALT:\n\tHlt\n\n"
        "MOVED:\n\tMovD/Nop\n\tJmp\n\n"
        "ROT2:\n\tRot/Nop\n\tJmp\n\n"
        "OUT2:\n\tOut/Nop\n\tJmp\n")


def seed(tag: str) -> list[str]:
    """Bloque SEED: imprime un caracter distinto; sirve para detectar que se
    ejecuto en lugar de.transferir. Se usa como perturbacion de layout (FASE 3)."""
    ch = {"s1": "1", "s2": "2", "s3": "3"}[tag]
    return [f"\t{tag}:", f"\tROT2 '{ch}'<<1 R_ROT2", "\tOUT2 ?- R_OUT2"]


def build(kind: str, with_seed: bool) -> str:
    if kind == "moved":
        transfer = ["\tMOVED C"]
    elif kind == "bare":
        transfer = ["\tC"]
    else:
        raise ValueError(kind)
    L = ["\tENTRY:",
         "\tROT 'X'<<1 R_ROT", "\tOUT ?- R_OUT"] + transfer
    if with_seed:
        L += seed("s1") + seed("s2") + seed("s3")
    else:
        L += ["\tB:", "\tROT 'B'<<1 R_ROT", "\tOUT ?- R_OUT",
              "\tROT 'D'<<1 R_ROT", "\tOUT ?- R_OUT"]
    L += ["\tC:", "\tROT 'C'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
    return CODE + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


cases = [("moved", False), ("bare", False), ("moved", True), ("bare", True)]
rows = []
for kind, with_seed in cases:
    tag = f"{kind}_{'seed' if with_seed else 'direct'}"
    src = WORK / f"xfer2_{tag}.hell"
    mb = WORK / f"xfer2_{tag}.mb"
    src.write_text(build(kind, with_seed))
    cp = subprocess.run([str(LMAO), "-d", "-o", str(mb), str(src)],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"case": tag, "expected": "XC", "compile_rc": cp.returncode,
           "stderr": cp.stderr.strip()[:200],
           "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        st, steps, out, ev = traced(mb.read_text())
        # trace: los 6 eventos alrededor de cada OUT
        row["status"] = st
        row["steps"] = steps
        row["out"] = out.decode("latin-1")
        row["match"] = out.decode("latin-1") == "XC"
        outs = [i for i, e in enumerate(ev) if "OUT" in e]
        row["trace_around_outs"] = [
            [{k: v for k, v in e.items() if k in ("s", "c", "d", "op", "md", "a", "OUT", "HLT")}
             for e in ev[max(0, i - 3):i + 2]]
            for i in outs]
    rows.append(row)
    print(json.dumps({k: v for k, v in row.items() if k != "trace_around_outs"},
                     ensure_ascii=False))

# volcado legible de la traza del caso winner
win = next((r for r in rows if r.get("match")), None)
if win:
    tag = win["case"]
    print(f"\n=== TRACE completo (no-nop) del caso ganador {tag} ===")
    st, steps, out, ev = traced((WORK / f"xfer2_{tag}.mb").read_text())
    lab = {}
    for ln in (WORK / f"xfer2_{tag}.dbg").read_text().splitlines():
        m = re.match(r"^(\w+): (CODE|DATA) (\d+)$", ln.strip())
        if m:
            lab.setdefault(int(m.group(3)), f"{m.group(1)}[{m.group(2)[0]}]")
    for e in ev[-24:]:
        extra = ""
        if "rotsrc" in e:
            extra += f" rot({e['rotsrc']})"
        if "OUT" in e:
            extra += f" OUT={e['OUT']!r}"
        if e.get("HLT"):
            extra += " HLT"
        print(f"s={e['s']:<5} c={e['c']:<6} {lab.get(e['c'], '@'+str(e['c'])):<9} d={e['d']:<6} "
              f"op={e['op']:<6} md={e['md']:<6} a={e['a']:<6}{extra}")

doc = {
    "format": "malbolge-lmao-xfer-micro/2",
    "question": "Que via de LMAO transfiere el control a un target conocido sin depender del fallthrough ni de la alineacion de d?",
    "null_hypothesis": "Ninguna via cumple ambas condiciones (H0).",
    "metric": "out == 'XC' (nunca 'XBC'/'XBDC'); con SEED intercalado, out == 'XC'",
    "rows": rows,
    "n_match": sum(1 for r in rows if r.get("match")),
    "winner": win["case"] if win else None,
    "claim": ("XFER_VIA_DATA_WORD=DEMONSTRATED_LOCALLY" if win and win["case"].startswith("bare")
              else ("XFER_VIA_MOVED=DEMONSTRATED_LOCALLY_pero_d_dependiente"
                    if win else "XFER=NOT_DEMONSTRATED")),
    "scope": "Microexperimento; oraculo malbolge.py; control adversario con 3 bloques SEED intercalados.",
    "not_demonstrated": ["readout 5 celdas", "mod59049 real", "segundo interprete", "d-alignment en contexto de wrap"],
}
out = WORK / "xfer_micro2_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\nREPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")