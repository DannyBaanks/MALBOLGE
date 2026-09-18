"""Small, honest MBIR-2L -> Classic backend frontier."""
from __future__ import annotations

from classic_codec import assemble
from mbir_2l import HALT, IN_BYTE, OUT_BYTE, decode
import malbolge


class ClassicUnsupported(ValueError):
    pass


def lower(blob: bytes) -> str:
    """Lower the proven byte-I/O/halt slice to positional Classic source."""
    instructions = decode(blob)
    opcodes = []
    for instruction in instructions:
        if instruction.opcode == IN_BYTE and instruction.operand is None:
            opcodes.append(23)
        elif instruction.opcode == OUT_BYTE and instruction.operand is None:
            opcodes.append(5)
        elif instruction.opcode == HALT and instruction.operand is None:
            opcodes.append(81)
        else:
            raise ClassicUnsupported(
                f"MBIR opcode {instruction.opcode:#04x} has no proven Classic lowering"
            )
    if not opcodes or opcodes[-1] != 81:
        raise ClassicUnsupported("Classic backend requires a final HALT")
    return assemble(opcodes)


def run(blob: bytes, input_bytes: bytes = b"", max_steps: int = 2_000_000):
    return malbolge.run(lower(blob), input_bytes, max_steps)
