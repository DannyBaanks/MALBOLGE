"""Positional encoder/decoder for the fixed 3^19 Unshackled runtime.

The 3^19 runtime keeps modulo-94 instruction decoding but adds one offset per
memory third. This is the direct inverse of bolge19/main.zig's dispatch; it is
not a Classic-to-Unshackled converter.
"""
from __future__ import annotations

import argparse

from classic_encoder import OPCODES

END = 3 ** 19
THIRD = 3 ** 18

# Exact offsets from bolge19/main.zig, including its documented parenthesis
# quirk. Keeping the source expression here makes the model auditable.
A1_OFF = 94 - ((END - 1) // 6 - 29524) % 94
A2_OFF = 94 - ((END - 1) // 3 - 59048) % 94
OFFSETS = (
    0,
    ((A1_OFF - THIRD) % 94) + 94,
    A2_OFF - ((2 * THIRD) % 94) + 94,
)


def region(position: int) -> int:
    if not 0 <= position < END:
        raise ValueError(f"position must be in 0..{END - 1}")
    return position // THIRD


def decode(character: str, position: int) -> int:
    if len(character) != 1 or not 33 <= ord(character) <= 126:
        raise ValueError("character must be printable ASCII 33..126")
    return (ord(character) + position + OFFSETS[region(position)]) % 94


def encode(opcode: int, position: int) -> str:
    if opcode not in OPCODES:
        raise ValueError(f"opcode must be one of {sorted(OPCODES)}")
    residue = (opcode - position - OFFSETS[region(position)]) % 94
    ascii_code = residue if residue >= 33 else residue + 94
    return chr(ascii_code)


def assemble19(opcodes: list[int], start_c: int = 0) -> str:
    """Directly encode an opcode plan; no search or runtime simulation."""
    if start_c < 0 or start_c + len(opcodes) > END:
        raise ValueError("opcode plan exceeds the k=19 address space")
    return "".join(encode(opcode, start_c + i)
                    for i, opcode in enumerate(opcodes))


def decode_program(source: str, start_c: int = 0) -> list[int]:
    """Decode source at its actual positions, independently of assembly."""
    if start_c < 0 or start_c + len(source) > END:
        raise ValueError("source exceeds the k=19 address space")
    return [decode(char, start_c + i) for i, char in enumerate(source)]


def verify_plan(opcodes: list[int], start_c: int = 0) -> bool:
    """Check direct encode/decode round-trip for an opcode plan."""
    return decode_program(assemble19(opcodes, start_c), start_c) == opcodes


# Backward-compatible short name for existing callers.
assemble = assemble19


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("opcode", type=int, nargs="?")
    parser.add_argument("position", type=int, nargs="?")
    parser.add_argument("--assemble", nargs="+", type=int)
    args = parser.parse_args()
    if args.assemble is not None:
        print(assemble19(args.assemble))
        return 0
    if args.opcode is None or args.position is None:
        parser.error("provide opcode position or --assemble opcodes...")
    char = encode(args.opcode, args.position)
    print(f"position={args.position} region={region(args.position)} "
          f"offset={OFFSETS[region(args.position)]} opcode={args.opcode} "
          f"ASCII={ord(char)} char={char!r} decoded={decode(char,args.position)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
