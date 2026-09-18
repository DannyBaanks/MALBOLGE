"""MBIR Classic: symbolic instruction plans lowered directly to Malbolge.

This is deliberately bottom-up: the IR is the eight decoded Classic opcodes,
and lowering is the positional inverse ``r = (opcode - c) mod 94``.  No
Brainfuck, Python, or other upper-level runtime participates in execution.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

import malbolge
from classic_codec import assemble, parse_plan


@dataclass(frozen=True)
class ClassicPlan:
    opcodes: tuple[int, ...]

    @classmethod
    def parse(cls, text: str) -> "ClassicPlan":
        opcodes = tuple(parse_plan(text))
        if not opcodes:
            raise ValueError("plan must contain at least one opcode")
        invalid = [opcode for opcode in opcodes if opcode not in malbolge._VALID_OPS]
        if invalid:
            raise ValueError(f"invalid Classic opcode(s): {invalid}")
        return cls(opcodes)

    def lower(self) -> str:
        return assemble(list(self.opcodes))

    def run(self, stdin_data: bytes = b"", max_steps: int = 2_000_000):
        return malbolge.run(self.lower(), stdin_data, max_steps)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lower a symbolic plan to Classic Malbolge")
    commands = parser.add_subparsers(dest="command", required=True)
    asm = commands.add_parser("assemble")
    asm.add_argument("plan", help="comma/space-separated opcode names or numbers")
    run = commands.add_parser("run")
    run.add_argument("plan", help="comma/space-separated opcode names or numbers")
    run.add_argument("--input", default="", help="Latin-1 input bytes")
    run.add_argument("--max-steps", type=int, default=2_000_000)
    args = parser.parse_args()
    plan = ClassicPlan.parse(args.plan)
    source = plan.lower()
    if args.command == "assemble":
        print(source)
        return 0
    status, steps, output = plan.run(args.input.encode("latin-1"), args.max_steps)
    print(f"source={source!r}")
    print(f"status={status} steps={steps} stdout={output!r}")
    return 0 if status == "HALTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
