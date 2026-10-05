#!/usr/bin/env python3
"""readout5 v3: readout de 5 celdas DENTRO de Malbolge, encadenado con MOVED.

Correcciones sobre v1/v2, ambas medidas y preservadas:
  v1: continuacion entre cadenas = etiqueta desnuda en fallthrough -> imprime
      1 digito y halt limpio. Medido: no encadena (ver run_link.py).
  v2: misma falla + dos defectos del arnes: el fallthrough tras la carga de
      gateways caia en un HALT dummy, y el contador desenrollado con
      `MOVED loop` re-enreda el bucle (OUT_OF_FUEL para T>=2).
  v3: continuacion = `MOVED <etiqueta>` (medido OK en 2 celdas: '99'), y el
      estado se alcanza con una cascada de parada S1..Sk de b_i posiciones cada
      una, que envuelve en T = b1*b2*...*bk (solo factores <=9).

H0: el readout de 5 celdas no imprime los 5 digitos esperados.
METRICA: out == ''.join(str(9 - ((T // 9**(i-1)) % 9)) for i in 1..5),
         con T = sum (9 - D_i) * 9^(i-1).
CONTROL: (a) chain8: 8 llamadas no envuelven; (b) enlace medido en 2 celdas
         ('99' con MOVED, '9' con etiqueta desnuda); (c) T=0 y T=59049 dan el
         mismo estado (control de equivalencia), aqui T=0 da '99999'.
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
import malbolge  # noqa: E402

SWEEP = {0: [], 1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 6: [6], 7: [7], 8: [8],
         9: [9], 18: [3, 6], 27: [9, 3], 36: [6, 6], 54: [9, 6], 81: [9, 9],
         243: [9, 9, 3]}


def cyc(n: int) -> str:
    ops = "/".join(["Nop"] * (n - 1) + ["MovD"])
    return f"\t{ops}\n\tJmp\n"


def predict(T: int) -> str:
    return "".join(str(9 - ((T // (9 ** (i - 1))) % 9)) for i in range(1, 6))


def build(T: int, stops: list[int]) -> str:
    cells = ["N1", "N2", "N3", "N4", "N5"] + [f"S{i+1}" for i in range(len(stops) - 1)]
    code = ".CODE\n" + "".join(f"{c}:\n{cyc(9)}\n" for c in cells)
    code += "".join(f"{c}:\n{cyc(n)}\n" for c, n in zip([f"S{i+1}" for i in range(len(stops))], stops))
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\n"
             "HALT:\n\tHlt\n\nMOVED:\n\tMovD/Nop\n\tJmp\n")

    L: list[str] = []
    s1 = "S1" if stops else None
    if not stops:                                   # T=0: sin cascada, leer ya
        L.append("\tENTRY:")
        L.append("\tMOVED read_N1")
    else:
        L += ["\tloop:", "\tR_MOVED", "\tENTRY:"]
        L += [f"\tN1 w1", f"\t{s1} st1", "\tMOVED loop"]
        for k in range(2, 6):
            L += [f"\tw{k-1}:", f"\tN{k} w{k}", f"\t{s1} st1", "\tMOVED loop"]
        L += ["\tw5:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-"]
        for i in range(len(stops)):
            L.append(f"\tst{i+1}:")
            if i + 1 < len(stops):
                L += [f"\tS{i+2} st{i+2}", "\tMOVED loop"]
            else:
                L.append("\tMOVED read_N1")
    for cell in range(1, 6):
        L.append(f"\tread_N{cell}:")
        L += [f"\tN{cell} r{cell}_{k}" for k in range(1, 10)]
        for k in range(1, 10):
            L += [f"\tr{cell}_{k}:", f"\tROT '{k}'<<1 R_ROT", "\tOUT ?- R_OUT",
                  "\tHALT ?-" if cell == 5 else f"\tMOVED read_N{cell+1}"]
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


rows = []
for T, stops in SWEEP.items():
    src = WORK / f"readout5v3_T{T}.hell"
    mb = WORK / f"readout5v3_T{T}.mb"
    src.write_text(build(T, stops))
    cp = subprocess.run([str(LMAO), "-o", str(mb), str(src)],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"T": T, "stops": stops, "predicted": predict(T),
           "hell_sha256": sha256(src), "hell_bytes": src.stat().st_size,
           "compile_rc": cp.returncode, "compile_stderr": cp.stderr.strip()[:200]}
    if cp.returncode == 0:
        row["mb_sha256"] = sha256(mb)
        row["mb_bytes"] = mb.stat().st_size
        t0 = time.time()
        res = malbolge.run(mb.read_text(), b"", MAX_STEPS)
        row["oracle_raw"] = repr(res)
        row["steps"] = res[1]
        row["out_hex"] = res[2].hex()
        row["out"] = res[2].decode("latin-1")
        row["wall_s"] = round(time.time() - t0, 2)
        row["match"] = row["out"] == row["predicted"]
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

ok = [r for r in rows if r.get("match")]
bad = [r for r in rows if not r.get("match")]
doc = {
    "format": "malbolge-lmao-readout5/3",
    "question": "Puede un programa Malbolge (Classic, LMAO/HeLL) emitir el estado de su cascada de 5 ciclos de 9 como 5 digitos, sin interprete externo?",
    "null_hypothesis": "El readout de 5 celdas no imprime los 5 digitos esperados (H0).",
    "metric": "out == ''.join(str(9 - ((T // 9**(i-1)) % 9)) for i in 1..5)",
    "relation": "T = sum_{i=1..5} (9 - D_i) * 9^(i-1)",
    "mechanism": "cadena de 9 llamadas por celda; el wrap imprime D=k; encadenado con MOVED <etiqueta> (medido OK en 2 celdas; la etiqueta desnuda en fallthrough imprime 1 digito)",
    "stop_cascade": "S1..Sk con b_i posiciones; envuelve en T = b1*...*bk",
    "sweep": {str(k): v for k, v in SWEEP.items()},
    "rows": rows,
    "n_rows": len(rows),
    "n_match": len(ok),
    "mismatches": [{"T": r["T"], "stops": r["stops"], "predicted": r["predicted"],
                    "got": r.get("out"), "out_hex": r.get("out_hex"),
                    "compile_rc": r["compile_rc"], "stderr": r["compile_stderr"][:160]} for r in bad],
    "claim": (f"READOUT5_MALBOLGE=DEMONSTRATED ({len(ok)}/{len(rows)} fases)"
              if len(ok) == len(rows) else "READOUT5_MALBOLGE=NOT_DEMONSTRATED"),
    "scope": "Oraculo malbolge.py unicamente. Cascada de 5 celdas leida en 16 estados (fases de N1 completas, N2 parcial, N3 parcial).",
    "not_demonstrated": [
        "mod59049 real (T=59048) sin cascada de parada",
        "replicacion en un segundo interprete",
        "no destructividad del readout (leer dos veces el mismo estado)",
        "lectura incremental / Stillwell",
    ],
}
out = WORK / "readout5_v3_report.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"\n{len(ok)}/{len(rows)} match")
print(f"REPORT={out} sha256={sha256(out)}")