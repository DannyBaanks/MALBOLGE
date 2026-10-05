#!/usr/bin/env python3
"""Generador unico y persistido del readout mid-wrap, parametrizado por celda.

CIERRA UN HUECO DE PROCEDENCIA DEL TURNO ANTERIOR: el generador guardado como
"ganador" (run_readout2_winner.py) NO incluia el shift +1 de la tabla de la
cadena 2 y da 0/5; el 4/4 habia salido de un heredoc inline. Este generador
incluye la receta completa y sirve para cualquier numero de celdas.

RECETA DEMOSTRADA PARA 2 CELDAS (verificada en el turno anterior):
  1. la celda de parada S se llama DESPUES de la celda de cascada dentro del tick
  2. una llamada de advanceo antes de la cadena 1
  3. ninguna llamada de advanceo antes de la cadena 2
  4. transferencia con MOV dedicado, un uso por transicion
  5. la tabla de digitos de la cadena 2 lleva +1 porque esa cadena mide p2+1

PARAMETROS (para barrer):
  ncells      numero de celdas de la cascada
  pre[i]      llamadas de advanceo antes de la cadena i
  shift[i]    compensacion de la tabla de digitos de la cadena i (bloque k
              imprime el caracter k+shift[i])

ANTI-FALSO-POSITIVO: assert explicito de que ningun bloque colapsa al mismo
caracter por un `else` y de que k+shift <= 9. dump() imprime la fuente para
inspeccion manual del caracter real de cada bloque.

Uso:
  python3 readout_gen.py --cells 2 --pre 1,0 --shift 0,1 --sweep 1,2,4,5,6
  python3 readout_gen.py --cells 2 --pre 1,0 --shift 0,1 --sweep 1,2,4,5,6 --dump
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/danny/Development/ISyCo Git/MALBOLGE")
LMAO = ROOT / "vendor/lmao/bin/lmao"
WORK = pathlib.Path("/tmp/lmao_work")
sys.path.insert(0, str(ROOT))
import malbolge as M  # noqa: E402


def cyc(n: int) -> str:
    return "\t" + "/".join(["Nop"] * (n - 1) + ["MovD"]) + "\n\tJmp\n"


def source(p: int, ncells: int, pre: list[int], shift: list[int]) -> str:
    cells = [f"N{i}" for i in range(1, ncells + 1)]
    blocks = ["\tN%d %s_%d" % (i, "a" if i == 1 else chr(ord("a") + i - 1), 9) for i in []]  # noqa
    code = ".CODE\n" + "".join(f"{c}:\n{cyc(9)}\n" for c in cells) + f"S:\n{cyc(p)}\n\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\nHALT:\n\tHlt\n\n"
             "MOVED:\n\tMovD/Nop\n\tJmp\n\n")
    for i in range(2, ncells + 1):          # MOV dedicado por transicion
        code += f"MOV{i}:\n\tMovD/Nop\n\tJmp\n\n"
    # --- datos ---
    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         f"\t{cells[0]} w1", "\tS st1", "\tMOVED loop"]
    for i in range(2, ncells + 1):
        L += [f"\tw{i-1}:", f"\t{cells[i-1]} w{i}", "\tS st1", "\tMOVED loop"]
    last = f"w{ncells}:"
    L += [last, "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
          "\tst1:", f"\tR_{st1_block}", f"\t{st1_block} read_1", "\tread_1:"]
    for i, c in enumerate(cells):
        pref = "a" if i == 0 else chr(ord("a") + i)
        # anti-falso-positivo: cada bloque k imprime k+shift, sin colapsos
        chars = [chr(48 + k + shift[i]) for k in range(1, 10)]
        assert len(set(chars)) == 9, f"colision de caracteres en cadena {i+1}: {chars}"
        assert all(48 + k + shift[i] <= 57 for k in range(1, 10)), \
            f"shift {shift[i]} en cadena {i+1} desborda el digito 9"
        L += [f"\t{c} {pref}9"] * pre[i]                 # llamadas de advanceo
        L += [f"\t{c} {pref}{k}" for k in range(1, 10)]
        for k in range(1, 10):
            L += [f"\t{pref}{k}:", f"\tROT '{chars[k-1]}'<<1 R_ROT", "\tOUT ?- R_OUT"]
            if i + 1 < ncells:
                L += [f"\tR_MOV{i+2}", f"\tMOV{i+2} read_{i+2}"]
        if i + 1 < ncells:
            L.append(f"\tread_{i+2}:")
        else:
            # la ultima cadena no transfiere: sus 9 bloques hacen HALT
            L = L[:-9 * 4] if False else L
    # los 9 bloques de la ultima cadenaNeed HALT: se reemiten
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


def source_v2(p: int, ncells: int, pre: list[int], shift: list[int],
              st1_block: str = "MOV2", entry_restore: bool = False,
              entry_cell: str = "none") -> str:
    """Variante sin el hack: la ultima cadena emite sus bloques con HALT."""
    cells = [f"N{i}" for i in range(1, ncells + 1)]
    code = ".CODE\n" + "".join(f"{c}:\n{cyc(9)}\n" for c in cells) + f"S:\n{cyc(p)}\n\n"
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\nHALT:\n\tHlt\n\n"
             "MOVED:\n\tMovD/Nop\n\tJmp\n\n")
    for i in range(2, ncells + 1):
        code += f"MOV{i}:\n\tMovD/Nop\n\tJmp\n\n"
    if st1_block == "MOVST":            # bloque FRESCO solo para la entrada
        code += "MOVST:\n\tMovD/Nop\n\tJmp\n\n"
    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         f"\t{cells[0]} w1", "\tS st1", "\tMOVED loop"]
    for i in range(2, ncells + 1):
        L += [f"\tw{i-1}:", f"\t{cells[i-1]} w{i}", "\tS st1", "\tMOVED loop"]
    L += [f"\tw{ncells}:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tHALT ?-",
          "\tst1:", f"\tR_{st1_block}", f"\t{st1_block} read_1", "\tread_1:"]
    for i, c in enumerate(cells):
        pref = chr(ord("a") + i)
        # anti-falso-positivo: cada bloque k imprime k+shift, sin colapsos.
        # Un bloque cuyo caracter excederia '9' es inalcanzable (la cadena mide
        # >=1, luego el wrap dispara en k<=8): se emite como HALT sin imprimir,
        # de modo que si se ejecutara el output se acorte y falle, nunca un
        # falso positivo por un 'else' que colapsa caracteres.
        # UNIFORMIDAD DE LAYOUT: todos los bloques deben ocupar el mismo numero
        # de celdas. Un bloque 'muerto' con menos celdas desplaza d y rompe la
        # alineacion de las cadenas siguientes (medido: 6-8 digitos de salida).
        # Por eso el caracter fuera de rango se emite tal cual (':' para k=9 con
        # shift=1): si el bloque llegara a dispararse, el caracter delata el fallo.
        chars = [chr(48 + k + shift[i]) for k in range(1, 10)]
        assert len(set(chars)) == 9, f"colision de caracteres en cadena {i+1}: {chars}"
        dead = [k for k, ch in enumerate(chars, start=1) if not ch.isdigit()]
        if dead:
            print(f"[nota] cadena {i+1} shift={shift[i]}: bloques {dead} con caracter "
                  f"fuera de 0-9 ({[chars[k-1] for k in dead]}) -> inalcanzables; "
                  f"se emiten con celdas uniformes")
        L += [f"\t{c} {pref}9"] * pre[i]
        L += [f"\t{c} {pref}{k}" for k in range(1, 10)]
        for k in range(1, 10):
            L += [f"\t{pref}{k}:", f"\tROT '{chars[k-1]}'<<1 R_ROT", "\tOUT ?- R_OUT"]
            # la receta demostrada usa la linea de transferencia SIN R_ previo:
            # con R_ el microtest dio 'XBDC' y el readout cae en fallthrough.
            if i + 1 < ncells:
                # entry_restore: anteponer R_ a TODAS las transiciones de cadena,
                # igualando la forma de entrada de la cadena 1 (R_ + MOV + target)
                # con la de las cadenas 2..n (MOV + target).
                # entry_cell: celda extra ANTES de la linea de transferencia, con el
                # MISMO numero de celdas en todos los modos (neutral en layout):
                #   "none" -> sin celda extra (receta demostrada)
                #   "R"    -> R_MOVx (restaura el bloque)
                #   "?"    -> celda don't-care, mismo tamano, sin efecto semantico
                if entry_cell == "R":
                    L += [f"\tR_MOV{i+2}"]
                elif entry_cell == "?":
                    L += ["\t?"]
                elif entry_cell == "none" and entry_restore:
                    L += [f"\tR_MOV{i+2}"]
                L += [f"\tMOV{i+2} read_{i+2}"]
            else:
                L += ["\tHALT ?-"]
        if i + 1 < ncells:
            L.append(f"\tread_{i+2}:")
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


def source_mod59049(k: int, pre: list[int], shift: list[int], stops=None, passes: int = 1,
                   verify: int = 0, pre_v: int = 0, v_cell: int = 1,
                   restore: int = 0, stop_first: bool = False,
                   restore_cell: int = 1) -> str:
    """mod59049 + readout. Reescrito limpio tras detectar que un restructure por
    regex habia roto el caso base: las lineas terminadoras de bloque quedaban en
    la lista equivocada y el readout principal no imprimia.

    verify=0 : solo el readout de 5 celdas (modo de referencia, debe dar 5 digitos)
    verify=1 : readout de 5 celdas y luego una cadena de verificacion que relee la
               celda 1 y hace HALT (6 digitos)
    verify=2 : solo la cadena de verificacion, sin readout previo (calibra el
               instrumento contra el estado verdadero)
    verify=3 : readout de 5 celdas, la cadena de verificacion, y tras ella se
               vuelve al bucle de ticks (lecturas multiple)
    passes>1 : la salida del readout vuelve al bucle en vez de hacer HALT
    """
    stops = list(stops) if stops else [9] * k
    cells = [f"N{i}" for i in range(1, 6)]
    stopnames = [f"S{i}" for i in range(1, len(stops) + 1)]

    code = ".CODE\n" + "".join(f"{c}:\n{cyc(9)}\n" for c in cells)
    code += "".join(f"{n}:\n{cyc(b)}\n" for n, b in zip(stopnames, stops))
    code += ("ROT:\n\tRot/Nop\n\tJmp\n\nOUT:\n\tOut/Nop\n\tJmp\n\n"
             "HALT:\n\tHlt\n\nMOVED:\n\tMovD/Nop\n\tJmp\n\n")
    for i in range(2, 6):
        code += f"MOV{i}:\n\tMovD/Nop\n\tJmp\n\n"
    # verify NO anade bloques de codigo: la posicion de un code block en el area de
    # codigo forma parte del estado xlat2 de los bloques existentes. Reusa MOV5.

    L = ["\tENTRY:", "\tloop:", "\tR_MOVED",
         ] + ([f"\t{stopnames[0]} s1", f"\t{cells[0]} w1"] if stop_first
              else [f"\t{cells[0]} w1", f"\t{stopnames[0]} s1"]) + ["\tMOVED loop"]
    for i in range(2, 6):
        L += [f"\tw{i-1}:",
              f"\t{cells[i-1]} w{i}",
              *([f"\t{stopnames[0]} s1"] if stop_first else []),
              "\tMOVED loop"]
    entry = "read_v" if verify == 2 else "read_1"
    L += ["\tw5:", "\tROT 'Z'<<1 R_ROT", "\tOUT ?- R_OUT", "\tR_MOV2", f"\tMOV2 {entry}"]
    for i in range(1, len(stops)):
        L += [f"\ts{i}:", f"\t{stopnames[i]} s{i+1}", "\tMOVED loop"]
    L += [f"\ts{len(stops)}:", "\tR_MOV2", f"\tMOV2 {entry}"]
    if verify != 2:
        L.append("\tread_1:")

    if verify != 2:
        for i, c in enumerate(cells):
            pref = chr(ord("a") + i)
            chars = [chr(48 + kk + shift[i]) for kk in range(1, 10)]
            assert len(set(chars)) == 9, f"colision de caracteres en cadena {i+1}: {chars}"
            L += [f"\t{c} {pref}9"] * pre[i]
            L += [f"\t{c} {pref}{kk}" for kk in range(1, 10)]
            for kk in range(1, 10):
                L += [f"\t{pref}{kk}:", f"\tROT '{chars[kk-1]}'<<1 R_ROT", "\tOUT ?- R_OUT"]
                if i + 1 < 5:
                    L += [f"\tMOV{i+2} read_{i+2}"]
                elif verify in (1, 3):
                    L += ["\tMOV5 read_v"]
                elif verify == 0 or passes == 1:
                    L += ["\tHALT ?-"]
                else:
                    L += ["\tR_MOVED", "\tMOVED loop"]
            if i + 1 < 5:
                L.append(f"\tread_{i+2}:")

    if verify in (1, 2, 3) and restore:
        # R llamadas de reparacion a la celda 1; si alguna envuelve, salta a la
        # verificacion (lo que acorta la salida y lo delata).
        L += [f"\tN{restore_cell} read_v"] * restore
    if verify in (1, 2, 3):
        vc = f"N{v_cell}"
        L += ["\tread_v:"] + [f"\t{vc} v9"] * pre_v + [f"\t{vc} v{j}" for j in range(1, 10)]
        for j in range(1, 10):
            tail = "\tHALT ?-" if verify != 3 else "\tR_MOVED\n\tMOVED loop"
            L += [f"\tv{j}:", f"\tROT '{j}'<<1 R_ROT", "\tOUT ?- R_OUT"] + tail.split("\n")
    return code + "\n.DATA {\n" + "\n".join(L) + "\n}\n"


def run_mod59049(k: int, pre: list[int], shift: list[int], stops=None, passes: int = 1,
                  verify: int = 0, pre_v: int = 0, v_cell: int = 1,
                  restore: int = 0, stop_first: bool = False, restore_cell: int = 1):
    stops = stops or [9]*k
    T = 1
    for b in stops: T *= b
    tag = f"mod{k}_p" + "-".join(map(str, pre)) + "_" + "-".join(map(str, shift))
    src = WORK / f"{tag}.hell"
    mb = WORK / f"{tag}.mb"
    src.write_text(source_mod59049(k, pre, shift, stops, passes, verify, pre_v, v_cell, restore, stop_first, restore_cell))
    cp = subprocess.run([str(LMAO), "-d", "-o", str(mb.resolve()), str(src.resolve())],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"k": k, "stops": stops, "T": T, "passes": passes, "verify": verify, "pre_v": pre_v, "v_cell": v_cell, "restore": restore, "stop_first": stop_first, "restore_cell": restore_cell, "pre": pre, "shift": shift,
           "compile_rc": cp.returncode, "stderr": cp.stderr.strip()[:160],
           "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        st, steps, out = M.run(mb.read_text(), b"", 40_000_000)
        got = out.decode("latin-1")
        pos = [(T // (9 ** i)) % 9 for i in range(5)]
        row["expected_positions"] = pos
        row["expected"] = "".join(chr(48 + 9 - q) for q in pos)
        row["status"] = st
        row["steps"] = steps
        row["out"] = got
        row["match"] = got.endswith(row["expected"])
        row["len"] = len(got)
    return row


def run_one(p: int, ncells: int, pre: list[int], shift: list[int], dump=False,
            st1_block: str = "MOV2", entry_restore: bool = False,
            entry_cell: str = "none"):
    src_text = source_v2(p, ncells, pre, shift, st1_block, entry_restore, entry_cell)
    tag = f"g{ncells}_p{p}_" + "-".join(map(str, pre)) + "_" + "-".join(map(str, shift))
    src = WORK / f"{tag}.hell"
    mb = WORK / f"{tag}.mb"
    src.write_text(src_text)
    if dump:
        print(src_text)
    cp = subprocess.run([str(LMAO), "-d", "-o", str(mb.resolve()), str(src.resolve())],
                        capture_output=True, text=True, cwd=str(ROOT / "vendor/lmao"))
    row = {"p": p, "ncells": ncells, "pre": pre, "shift": shift, "st1_block": st1_block,
           "entry_restore": entry_restore, "entry_cell": entry_cell,
           "compile_rc": cp.returncode, "stderr": cp.stderr.strip()[:160],
           "hell_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if cp.returncode == 0:
        row["mb_sha256"] = hashlib.sha256(mb.read_bytes()).hexdigest()
        st, steps, out = M.run(mb.read_text(), b"", 400_000)
        got = out.decode("latin-1")
        row.update({"status": st, "steps": steps, "out": got, "len": len(got)})
        # digits esperados por cadena
        pos = [(p // (9 ** i)) % 9 for i in range(ncells)]
        row["expected_digits"] = [9 - q for q in pos]
        row["expected"] = "".join(chr(48 + d) for d in row["expected_digits"])
        row["digit_ok"] = [got[i] == chr(48 + d) if i < len(got) else False
                           for i, d in enumerate(row["expected_digits"])]
        row["no_fallthrough"] = len(got) == ncells
        row["match"] = got == row["expected"]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", type=int, required=True)
    ap.add_argument("--pre", required=True, help="lista de pre-call por cadena")
    ap.add_argument("--shift", required=True, help="shift de tabla por cadena")
    ap.add_argument("--sweep", required=True, help="lista de p")
    ap.add_argument("--entry-cell", default="none", choices=["none","R","?"],
                    help="celda extra antes de la linea de transferencia, neutral en layout")
    ap.add_argument("--entry-restore", action="store_true",
                    help="anteponer R_ a todas las transiciones (iguala la forma de entrada)")
    ap.add_argument("--st1-block", default="MOV2", choices=["MOV2","MOVST"],
                    help="MOV2 = reutiliza el bloque de la cadena 1 (receta actual); MOVST = bloque fresco solo para la entrada")
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    pre = [int(x) for x in a.pre.split(",")]
    shift = [int(x) for x in a.shift.split(",")]
    ps = [int(x) for x in a.sweep.split(",")]
    assert len(pre) == a.cells and len(shift) == a.cells, "pre/shift deben tener ncells elementos"
    rows = []
    for p in ps:
        r = run_one(p, a.cells, pre, shift, dump=a.dump and p == ps[0],
                   st1_block=a.st1_block, entry_restore=a.entry_restore,
                   entry_cell=a.entry_cell)
        rows.append(r)
        print(json.dumps({k: v for k, v in r.items() if "sha256" not in k}, ensure_ascii=False))
    n = sum(1 for r in rows if r.get("match"))
    print(f"\n{n}/{len(ps)} match  (pre={pre} shift={shift} cells={a.cells})")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(
            {"format": "malbolge-lmao-readout-gen/1", "ncells": a.cells, "pre": pre,
             "shift": shift, "st1_block": a.st1_block, "entry_restore": a.entry_restore, "entry_cell": a.entry_cell,
             "sweep": ps, "rows": rows,
             "n_match": n}, indent=2,
            ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()