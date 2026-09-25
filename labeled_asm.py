"""Labeled Malbolge v0: readable opcodes with labels, compiled to Classic Malbolge.

Source language (one statement per line, `#` starts a comment)::

    main:   in
            out
            call sub
            out
            end
    sub:    in
            out
            ret

Statements: ``in``, ``out``, ``nop``, ``end``, ``goto L``, ``call L``, ``ret``.

How it lowers
-------------
* Every statement becomes one Classic cell whose character is the unique
  printable byte that decodes to the wanted opcode at that position.
* ``goto``/``call``/``ret`` become one ``jmp`` cell.  Classic ``jmp`` sets
  ``c = mem[d]``; the VM then encrypts the landing cell ``mem[c]`` without
  executing it and continues at ``landing + 1``.  The compiler therefore has to
  find, for each jump, a data cell ``d`` whose *current* value is the landing
  address.  Its freedom is (a) how many executed ``nop`` cells to insert before
  the ``jmp`` (they advance ``c`` and ``d`` together) and (b) which of the 8
  load-valid characters to store in a not-yet-used data cell.  A depth-first
  search with backtracking picks a layout.

Honest limits of v0 (rejected with an explanation, never silently miscompiled)
----------------------------------------------------------------------------
* No statement may execute twice.  A Classic cell changes opcode every time it
  runs (the encryption table has no fixed points).  Loops are a solved problem
  in Matthias Lutter's HeLL/LMAO (xlat2 cycles, loop-resistant RNop written by
  runtime initialization code) and in malbolge-free's lmao-lite; v0 only lays
  out load-time bytes and deliberately does not reimplement that.
* No ``rot``, ``opr`` or ``movd``: they rewrite memory or ``d`` and would need
  taint tracking.
* Landing addresses come from printable load-time characters, so every jump
  target starts at a cell <= 127.
* Because there are no conditionals and no re-execution, the executed path is
  fixed and independent of input.  Jumps change the *layout*, not what the
  program can compute; they are the verified substrate for later loops.

Every compiled program can be checked with ``verify``: the oracle
``malbolge.run``, an instrumented trace of the same VM, the reference semantics
of the labeled program, the planned cell path, the optional Zig runner, and a
mutation control proving that every data cell actually steers the jump.
"""
from __future__ import annotations

import argparse
import copy
import random
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import binaries
import malbolge
from classic_encoder import encode

MEM = malbolge.MEMORY_SIZE
ENC = malbolge._ENCRYPT
OPCODE = {"in": 23, "out": 5, "nop": 68, "end": 81, "jmp": 4}
PLAIN = ("in", "out", "nop")
MAX_PAD = 94
NODE_BUDGET = 200_000


class CompileError(ValueError):
    pass


@dataclass(frozen=True)
class Stmt:
    line: int
    kind: str
    arg: str | None = None


def parse(text: str) -> tuple[list[Stmt], dict[str, int]]:
    stmts: list[Stmt] = []
    labels: dict[str, int] = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        while True:
            match = re.match(r"^([A-Za-z_]\w*):\s*(.*)$", line)
            if not match:
                break
            name = match.group(1)
            if name in labels:
                raise CompileError(f"line {number}: duplicate label {name!r}")
            labels[name] = len(stmts)
            line = match.group(2).strip()
        if not line:
            continue
        parts = line.split()
        kind = parts[0].lower()
        if kind in ("in", "out", "nop", "end", "ret"):
            if len(parts) != 1:
                raise CompileError(f"line {number}: {kind!r} takes no argument")
            stmts.append(Stmt(number, kind))
        elif kind in ("goto", "call"):
            if len(parts) != 2:
                raise CompileError(f"line {number}: {kind!r} needs exactly one label")
            stmts.append(Stmt(number, kind, parts[1]))
        else:
            raise CompileError(f"line {number}: unknown statement {parts[0]!r} "
                               "(v0 accepts in, out, nop, end, goto, call, ret)")
    if not stmts:
        raise CompileError("empty program")
    for name, index in labels.items():
        if index >= len(stmts):
            raise CompileError(f"label {name!r} points past the last statement")
    for s in stmts:
        if s.arg is not None and s.arg not in labels:
            raise CompileError(f"line {s.line}: unknown label {s.arg!r}")
    return stmts, labels


def execution_path(stmts: list[Stmt], labels: dict[str, int]) -> list[int]:
    """Statement indices in execution order (input-independent in v0)."""
    pc, stack, path, seen = 0, [], [], set()
    while True:
        if pc >= len(stmts):
            raise CompileError("execution runs past the last statement without 'end'")
        if pc in seen:
            raise CompileError(
                f"line {stmts[pc].line}: statement would execute twice; v0 has no loops "
                "(a Classic cell changes opcode every time it runs)")
        seen.add(pc)
        path.append(pc)
        s = stmts[pc]
        if s.kind == "end":
            return path
        if s.kind == "goto":
            pc = labels[s.arg]
        elif s.kind == "call":
            stack.append(pc + 1)
            pc = labels[s.arg]
        elif s.kind == "ret":
            if not stack:
                raise CompileError(f"line {s.line}: 'ret' without a pending 'call'")
            pc = stack.pop()
        else:
            pc += 1


def reference_output(stmts: list[Stmt], path: list[int], stdin: bytes) -> bytes:
    """What the labeled program means, independent of any Malbolge layout."""
    a, pos, out = 0, 0, bytearray()
    for index in path:
        kind = stmts[index].kind
        if kind == "in":
            if pos < len(stdin):
                a = stdin[pos]
                pos += 1
            else:
                a = malbolge.EOF_VALUE
        elif kind == "out":
            out.append(a % 256)
    return bytes(out)


@dataclass
class Layout:
    init: dict[int, int] = field(default_factory=dict)   # cell -> load-time byte
    mem: dict[int, int] = field(default_factory=dict)    # cell -> current value during planning
    role: dict[int, str] = field(default_factory=dict)
    c: int = 0
    d: int = 0
    steps: int = 0
    executed: list[int] = field(default_factory=list)

    def assign(self, cell: int, byte: int, role: str) -> bool:
        if cell in self.init or not 0 <= cell < MEM:
            return False
        self.init[cell] = self.mem[cell] = byte
        self.role[cell] = role
        return True

    def run_plain(self, op: int, role: str) -> bool:
        cell = self.c
        if not self.assign(cell, encode(op, cell)[1], role):
            return False
        self.steps += 1
        self.executed.append(cell)
        if op != OPCODE["end"]:
            self.mem[cell] = ENC[self.mem[cell]]
            self.c = (cell + 1) % MEM
            self.d = (self.d + 1) % MEM
        return True


def _segments(stmts: list[Stmt], path: list[int]):
    segs, body = [], []
    for index in path:
        s = stmts[index]
        if s.kind in PLAIN:
            body.append((s.kind, s.line))
        else:
            segs.append((body, s))
            body = []
    return segs


def compile_layout(stmts: list[Stmt], labels: dict[str, int]) -> Layout:
    path = execution_path(stmts, labels)
    segs = _segments(stmts, path)
    budget = [NODE_BUDGET]
    legal = lambda cell: sorted({encode(op, cell)[1] for op in malbolge._VALID_OPS})

    def place(state: Layout, i: int) -> Layout | None:
        budget[0] -= 1
        if budget[0] < 0:
            return None
        body, tail = segs[i]
        state = copy.deepcopy(state)
        for kind, line in body:
            if not state.run_plain(OPCODE[kind], f"{kind} (line {line})"):
                return None
        if tail.kind == "end":
            return state if state.run_plain(OPCODE["end"], f"end (line {tail.line})") else None
        label = f"{tail.kind}{' ' + tail.arg if tail.arg else ''} (line {tail.line})"
        for pad in range(MAX_PAD + 1):
            base = copy.deepcopy(state)
            if not all(base.run_plain(OPCODE["nop"], "padding nop") for _ in range(pad)):
                break
            jc = base.c
            if not base.assign(jc, encode(OPCODE["jmp"], jc)[1], f"jmp: {label}"):
                break
            x = base.d
            fresh = x not in base.mem
            for target in (legal(x) if fresh else [base.mem[x]]):
                trial = copy.deepcopy(base)
                if fresh:
                    trial.assign(x, target, f"data: landing {target} for {label}")
                trial.steps += 1
                trial.executed.append(jc)
                if target not in trial.mem:
                    trial.assign(target, encode(OPCODE["nop"], target)[1], f"landing of {label} (encrypted, never run)")
                if not 33 <= trial.mem[target] <= 126:
                    continue
                trial.mem[target] = ENC[trial.mem[target]]
                trial.c = (target + 1) % MEM
                trial.d = (trial.d + 1) % MEM
                if trial.c in trial.init:
                    continue
                done = place(trial, i + 1)
                if done is not None:
                    return done
        return None

    result = place(Layout(), 0)
    if result is None:
        raise CompileError("no layout found within the search budget "
                           f"({NODE_BUDGET} nodes, up to {MAX_PAD} padding nops per jump)")
    return result


def emit(layout: Layout) -> str:
    last = max(layout.init)
    return "".join(chr(layout.init[p]) if p in layout.init else chr(encode(OPCODE["nop"], p)[1])
                   for p in range(last + 1))


def trace(source: str, stdin: bytes, max_steps: int = 100_000):
    """malbolge.run's loop, recording the executed cell of every step."""
    mem = malbolge.load_memory(source)
    a = c = d = steps = pos = 0
    out, path = bytearray(), []
    while steps < max_steps:
        steps += 1
        path.append(c)
        op = (mem[c] + c) % 94
        if op == 4:
            c = mem[d]
        elif op == 5:
            out.append(a % 256)
        elif op == 23:
            if pos < len(stdin):
                a = stdin[pos]
                pos += 1
            else:
                a = malbolge.EOF_VALUE
        elif op == 39:
            v = mem[d]
            mem[d] = v // 3 + (v % 3) * 3 ** 9
            a = mem[d]
        elif op == 40:
            d = mem[d]
        elif op == 62:
            mem[d] = malbolge.crazy(a, mem[d])
            a = mem[d]
        elif op == 81:
            return "HALTED", steps, bytes(out), path
        if 33 <= mem[c] <= 126:
            mem[c] = ENC[mem[c]]
        c = (c + 1) % MEM
        d = (d + 1) % MEM
    return "OUT_OF_FUEL", steps, bytes(out), path


def zig_runner(source: str, stdin: bytes):
    exe = binaries.find_vm_runner()
    if exe is None:
        return None
    p = subprocess.run([str(exe), "10", source.encode().hex(), stdin.hex(), "100000", "0", "0", "0"],
                       capture_output=True, text=True, timeout=60)
    line = next((l for l in (p.stderr + p.stdout).splitlines() if l.startswith("RESULT")), None)
    return dict(t.split("=", 1) for t in line.split()[1:]) if line else None


def verify(text: str, seed: int = 20260913) -> tuple[bool, list[str]]:
    stmts, labels = parse(text)
    path = execution_path(stmts, labels)
    layout = compile_layout(stmts, labels)
    source = emit(layout)
    lines, ok = [], True

    def check(name: str, passed: bool):
        nonlocal ok
        ok &= passed
        lines.append(f"{'PASS' if passed else 'FAIL'}  {name}")

    rng = random.Random(seed)
    inputs = [b"", b"A", b"AB", b"Hola", bytes(rng.randrange(256) for _ in range(16))]
    for stdin in inputs:
        want = reference_output(stmts, path, stdin)
        status, steps, out = malbolge.run(source, stdin, 100_000)
        t_status, t_steps, t_out, t_path = trace(source, stdin)
        check(f"input {stdin[:8]!r}: oracle HALTED, output {out!r} == reference {want!r}",
              status == "HALTED" and out == want)
        check(f"input {stdin[:8]!r}: executed cells == planned path ({len(layout.executed)} steps)",
              (t_status, t_steps, t_out, t_path) == ("HALTED", layout.steps, out, layout.executed))
        z = zig_runner(source, stdin)
        if z is not None:
            check(f"input {stdin[:8]!r}: Zig runner status/steps/output match",
                  z.get("status") == "HALTED" and int(z.get("steps", -1)) == steps
                  and (z.get("out_hex") if z.get("out_hex") != "-" else "") == out.hex())  # runner prints '-' for empty output

    data_cells = [p for p, r in layout.role.items() if r.startswith("data")]
    for cell in data_cells:
        steered = True
        for byte in sorted({encode(op, cell)[1] for op in malbolge._VALID_OPS} - {layout.init[cell]}):
            mutated = source[:cell] + chr(byte) + source[cell + 1:]
            if trace(mutated, b"AB")[3] == layout.executed:
                steered = False
        check(f"control: every other valid byte in data cell {cell} changes the executed path", steered)
    if not data_cells:
        lines.append("note  no data cells (no jump read a dedicated data cell)")
    return ok, lines


def explain(text: str) -> str:
    stmts, labels = parse(text)
    layout = compile_layout(stmts, labels)
    source = emit(layout)
    step_of = {cell: i + 1 for i, cell in enumerate(layout.executed)}
    rows = [f"source ({len(source)} cells): {source}", "",
            " cell  char  op    step  role"]
    names = {v: k for k, v in OPCODE.items()}
    names.update({39: "rot", 40: "movd", 62: "opr"})
    for p, ch in enumerate(source):
        op = (ord(ch) + p) % 94
        rows.append(f"{p:5d}  {ch!r:5} {names.get(op, '?'):5} {step_of.get(p, ''):>4}  "
                    f"{layout.role.get(p, 'filler nop (never run, never read)')}")
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Labeled Malbolge v0 -> Classic Malbolge")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("compile", "explain", "verify"):
        p = sub.add_parser(name)
        p.add_argument("file", type=Path)
        if name == "compile":
            p.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    text = args.file.read_text(encoding="utf-8")
    try:
        if args.command == "compile":
            source = emit(compile_layout(*parse(text)))
            if args.output:
                args.output.write_text(source, encoding="ascii")
            print(source)
            return 0
        if args.command == "explain":
            print(explain(text))
            return 0
        ok, lines = verify(text)
        print("\n".join(lines))
        print(f"\nLABELED_VERIFY={'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    except CompileError as exc:
        print(f"COMPILE_ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
