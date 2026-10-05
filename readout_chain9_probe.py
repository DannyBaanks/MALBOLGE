#!/usr/bin/env python3
"""chain9: primitivo de readout Malbolge-side.

H0 (nula): una cadena de 9 llamadas a la MISMA celda de ciclo de 9 NO
despacha al noveno label; la salida no es '9' (cae por otro lado, se cuelga
o no imprime). Si H0 sobrevive, el readout dentro de Malbolge NO es posible con
este idioma y hay que cerrar el item como NOT_DEMONSTRATED.

H1: la llamada k solo salta a su label cuando esa llamada envuelve el ciclo;
con el ciclo en posicion 0, envuelve la llamada 9 -> imprime '9'.

CONTROL (chain8): 8 llamadas (NO envuelven) y luego un 'X' explicito en el
fallthrough. Si chain8 imprimiera un digito 1..8, el wrap ocurriria antes de la
novena llamada y la metrica no distinguiria wrap de fallthrough.

METRICA: chain9_out == '9' AND chain8_out == 'X'.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work")
MAX_STEPS = 5_000_000

sys.path.insert(0, str(ROOT))
import malbolge  # noqa: E402  (oracle, verificado en GUIA.md §1)


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_case(name: str) -> dict:
    src = WORK / f"{name}.hell"
    mb = WORK / f"{name}.mb"
    rec: dict = {"hell_sha256": sha256(src), "hell_bytes": src.stat().st_size}
    t0 = time.time()
    cp = subprocess.run(
        [str(LMAO), "-o", str(mb), str(src)],
        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"),
    )
    rec["compile_rc"] = cp.returncode
    rec["compile_stdout"] = cp.stdout.strip()
    rec["compile_stderr"] = cp.stderr.strip()
    if cp.returncode != 0 or not mb.exists():
        rec["status"] = "COMPILE_FAIL"
        return rec
    raw = mb.read_text()
    rec["mb_sha256"] = sha256(mb)
    rec["mb_bytes"] = mb.stat().st_size
    res = malbolge.run(raw, b"", MAX_STEPS)
    rec["oracle_raw"] = repr(res)
    rec["halted"] = res[0] == "HALTED"
    rec["steps"] = res[1]
    out = res[2] if len(res) > 2 else b""
    rec["out_bytes"] = list(out) if isinstance(out, (bytes, bytearray)) else None
    rec["out"] = out.decode("latin-1") if isinstance(out, (bytes, bytearray)) else None
    rec["wall_s"] = round(time.time() - t0, 2)
    return rec


cases = {n: run_case(n) for n in ("chain9", "chain8")}

got9 = cases["chain9"].get("out")
got8 = cases["chain8"].get("out")
verdict = {
    "metric": "chain9_out == '9' AND chain8_out == 'X'",
    "chain9_out": got9,
    "chain8_out": got8,
    "h1_supported": bool(got9 == "9" and got8 == "X"),
}
if verdict["h1_supported"]:
    claim = "CHAIN_CALL_WRAP_LABEL=DEMONSTRATED (llamada k -> label k solo al envolver; ciclo en 0 envuelve en la 9)"
else:
    claim = "CHAIN_CALL_WRAP_LABEL=NOT_DEMONSTRATED"

doc = {
    "format": "malbolge-lmao-chain9/1",
    "question": "Puede Malbolge leer su propio estado de ciclo (posicion p) emitiendo un digito, sin salirse a un interprete externo?",
    "null_hypothesis": "La cadena de 9 llamadas no despacha al noveno label (H0).",
    "control": "chain8 = 8 llamadas + 'X' explicito en fallthrough: prueba que el wrap NO ocurre antes de la novena llamada.",
    "metric": verdict["metric"],
    "cases": cases,
    "verdict": verdict,
    "claim": claim,
    "scope": "Solo el idioma HeLL/LMAO Classic y el oráculo malbolge.py. NO demuestra readout de 5 digitos ni de mod59049.",
    "not_demonstrated": [
        "readout completo de 5 celdas (59049 estados)",
        "replicacion en un segundo interprete",
    ],
}
out = WORK / "chain9_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(doc, indent=2, ensure_ascii=False))
print(f"\nREPORT={out} sha256={sha256(out)}")