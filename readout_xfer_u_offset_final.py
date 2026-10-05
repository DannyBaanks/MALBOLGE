#!/usr/bin/env python3
"""Cierre formal: U_ como transferencia -- alcanzada vs printing, y sensibilidad a d.

Determina por traza, para cada caso, si el CONTROL LLEGO al target (no solo si
imprimio el caracter esperado). Es la distincion que exige el compose: U_ apunta
a un CODE label, asi que su semantica es 'el control llega al bloque', no
'imprime C'.

Criterio de 'target alcanzado':
  u_    -> cllego alguna vez a la direccion del code label TC
  moved -> cllego alguna vez a la direccion del ROT que imprime 'C' (o al HALT)
  bare  -> idem
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
OPS = {4: "jmp", 5: "out", 23: "in", 39: "rot", 40: "movd", 62: "crazy", 81: "hlt"}

sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402


def dbg_labels(tag: str) -> dict[str, int]:
    out = {}
    for ln in (WORK / f"{tag}.dbg").read_text().splitlines():
        m = re.match(r"^(\w+): (CODE|DATA) (\d+)$", ln.strip())
        if m:
            out[m.group(1)] = int(m.group(3))
    return out


def trace_c(source, max_steps=100_000):
    mem = M.load_memory(source)
    a = c = d = 0
    steps = 0
    cs = []
    while steps < max_steps:
        steps += 1
        op = (mem[c] + c) % 94
        cs.append((steps, c, d, op))
        if op == 4:
            c = mem[d]
        elif op == 5:
            pass
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
            return cs
        if 33 <= mem[c] <= 126:
            mem[c] = M._ENCRYPT[mem[c]]
        c = (c + 1) % M.MEMORY_SIZE
        d = (d + 1) % M.MEMORY_SIZE
    return cs


rows = []
for mech in ("moved", "bare", "u_"):
    for pad in (0, 1):
        for seed in (0, 3):
            tag = f"u_{mech}_pad{pad}_seed{seed}"
            mb = WORK / f"{tag}.mb"
            if not mb.exists():
                continue
            lab = dbg_labels(tag)
            ev = trace_c(mb.read_text())
            target_name = "TC" if mech == "u_" else "HALT"
            taddr = lab.get(target_name)
            reached = any(c == taddr for _, c, _, _ in ev)
            # primera vez que c entra al target
            first = next((s for s, c, _, _ in ev if c == taddr), None)
            rows.append({
                "case": tag, "mech": mech, "pad": pad, "seed": seed,
                "target_code_label": target_name, "target_addr": taddr,
                "control_reached_target": reached,
                "first_step_at_target": first,
                "hell_sha256": hashlib.sha256((WORK / f"{tag}.hell").read_bytes()).hexdigest(),
                "mb_sha256": hashlib.sha256(mb.read_bytes()).hexdigest(),
            })
            print(json.dumps({k: v for k, v in rows[-1].items()
                              if k not in ("hell_sha256", "mb_sha256")}, ensure_ascii=False))

u_pad0 = [r for r in rows if r["mech"] == "u_" and r["pad"] == 0]
u_pad1 = [r for r in rows if r["mech"] == "u_" and r["pad"] == 1]
m_pad0 = [r for r in rows if r["mech"] == "moved" and r["pad"] == 0]
m_pad1 = [r for r in rows if r["mech"] == "moved" and r["pad"] == 1]

claims = {
    "U_RELATIVE_TRANSFER": ("DEMONSTRATED"
                            if all(r["control_reached_target"] for r in u_pad0)
                            else "NOT_DEMONSTRATED"),
    "U_OFFSET_RESISTANT_XFER": ("DEMONSTRATED"
                                if all(r["control_reached_target"] for r in u_pad1) else "DESTROYED"),
    "MIDWRAP_P2_XFER": "NOT_DEMONSTRATED",
    "READOUT2_MIDWRAP": "NOT_DEMONSTRATED",
}
doc = {
    "format": "malbolge-lmao-u-offset/2",
    "question": "Puede U_ transferir control en una condicion de offset/desalineacion de d donde MOVED falla?",
    "source_semantics": {
        "prefix.c:73-87": "U_ fija data->number = -m (m = celdas hasta el anchor) y sintetiza m RNop virtuales ante el code label destino",
        "initialize.c:72-87": "valor emitido = addr(TARGET) + number - 1 = addr(TARGET) - m - 1",
        "runtime": "el jmp que lee la celda U_ hace c = addr(TARGET)-m; el autoincremento entra al primer RNop virtual y camina hasta TARGET",
        "conclusion": "U_ pre-compensa el LADO DEL DESTINO. La celda U_ sigue exigiendo que d este exactamente en su direccion para ser leida.",
    },
    "oracle_note": "U_ apunta a un CODE label: su semantica es 'el control llega al bloque', no 'imprime C'. Por eso se midio control_reached_target por traza, no solo stdout.",
    "perturbation": {
        "pad": "una celda `?` (no ejecuta nada) insertada justo antes de la linea de transferencia: desplaza d en +1",
        "seed": "3 bloques SEED intercalados entre la transferencia y el target B/C: prueba de no-contiguidad",
    },
    "rows": rows,
    "summary": {
        "moved_pad0": [r["control_reached_target"] for r in m_pad0],
        "moved_pad1": [r["control_reached_target"] for r in m_pad1],
        "u_pad0": [r["control_reached_target"] for r in u_pad0],
        "u_pad1": [r["control_reached_target"] for r in u_pad1],
    },
    "claims": claims,
    "stop_condition_hit": "STOP #2 del compose: 'El fixture limpio pasa pero el adversarial d falla igual que MOVED'. Medido: con pad=1 tanto MOVED como U_ pierden el target. No se intentaron mas variantes.",
    "evidence_key": {
        "u_pad0_reaches_TC": "traza u_u__pad0_seed0: s=3064 c=3222 jmp md=3254 -> c=3254 -> c++ = 3255 = TC",
        "u_pad1_fails": "u_u__pad1_seed0 out='X¨¨¨¨DâÞ' (basura); el control no llega al target",
        "moved_pad0_reaches": "traza u_moved_pad0_seed0: s=3238 movd; s=3239 jmp md=3446 -> 3447 = ROT de C; OUT 'C'",
        "moved_pad1_fails": "u_moved_pad1_seed0 out='X'; s=3253 c=29444 op=INV43 (celda no ejecutable)",
    },
    "not_demonstrated": ["readout 2 celdas mid-wrap", "readout 5 celdas", "mod59049 real",
                         "segundo interprete", "p=3,7,8", "U_ en el interior de la cadena de 9 llamadas"],
    "scope": "Microfixtures A/B/C; oraculo malbolge.py + traza; sin cambios en el readout previo.",
}
out = WORK / "u_offset_report_final.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print("\nclaims:", json.dumps(claims, ensure_ascii=False))
print(f"REPORT={out} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")