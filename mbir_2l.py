"""MBIR-2L byte VM used by the Befunge and WebAssembly frontends."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

HALT = 0x00
PUSH_CONST, POP, DUP = 0x01, 0x02, 0x03
ADD, SUB, MUL = 0x06, 0x07, 0x08
CMP_EQ, CMP_LT, CMP_GT = 0x09, 0x0A, 0x0B
JUMP, JUMP_IF_FALSE = 0x0C, 0x0D
OUT_BYTE, IN_BYTE = 0x10, 0x11

MNEMONICS = {
    HALT: "HALT", PUSH_CONST: "PUSH_CONST", POP: "POP", DUP: "DUP",
    ADD: "ADD", SUB: "SUB",
    MUL: "MUL", CMP_EQ: "CMP_EQ", CMP_LT: "CMP_LT", CMP_GT: "CMP_GT",
    JUMP: "JUMP", JUMP_IF_FALSE: "JUMP_IF_FALSE", OUT_BYTE: "OUT_BYTE",
    IN_BYTE: "IN_BYTE",
}
OPERAND_WIDTH = {PUSH_CONST: 1, JUMP: 3, JUMP_IF_FALSE: 3}


class MBIR2LError(Exception):
    def __init__(self, reason: str, pc: int = -1):
        super().__init__(f"{reason} at pc={pc}")
        self.reason = reason
        self.pc = pc


@dataclass(frozen=True)
class Instruction:
    offset: int
    opcode: int
    operand: int | None
    next_offset: int


def encode(instructions: list[tuple[int, int | None]]) -> bytes:
    out = bytearray()
    for opcode, operand in instructions:
        if opcode not in MNEMONICS:
            raise ValueError(f"BAD_OPCODE: 0x{opcode:02x}")
        out.append(opcode)
        width = OPERAND_WIDTH.get(opcode, 0)
        if width == 0:
            if operand is not None:
                raise ValueError(f"unexpected operand for {MNEMONICS[opcode]}")
        elif width == 1:
            if not isinstance(operand, int) or not 0 <= operand <= 0xFF:
                raise ValueError("u8 operand out of range")
            out.append(operand)
        else:
            if not isinstance(operand, int) or not 0 <= operand <= 0xFFFFFF:
                raise ValueError("u24 operand out of range")
            out.extend(operand.to_bytes(3, "little"))
    return bytes(out)


def decode(blob: bytes) -> list[Instruction]:
    result: list[Instruction] = []
    pc = 0
    while pc < len(blob):
        start = pc
        opcode = blob[pc]
        pc += 1
        if opcode not in MNEMONICS:
            raise MBIR2LError("BAD_OPCODE", start)
        width = OPERAND_WIDTH.get(opcode, 0)
        if pc + width > len(blob):
            raise MBIR2LError("BAD_OPERAND", start)
        operand = None
        if width == 1:
            operand = blob[pc]
        elif width == 3:
            operand = int.from_bytes(blob[pc:pc + 3], "little")
        pc += width
        result.append(Instruction(start, opcode, operand, pc))
    return result


def run(blob: bytes, input_bytes: bytes = b"", max_steps: int = 1_000_000,
        trace: bool = False) -> dict:
    try:
        instructions = decode(blob)
    except MBIR2LError as exc:
        return {"status": "ERROR", "reason": exc.reason, "pc": exc.pc,
                "steps": 0, "output_bytes": [], "stack": [], "trace": None}
    by_offset = {instruction.offset: instruction for instruction in instructions}
    stack: list[int] = []
    output = bytearray()
    events = [] if trace else None
    pc = instructions[0].offset if instructions else 0
    input_cursor = 0
    steps = 0

    def pop() -> int:
        if not stack:
            raise MBIR2LError("STACK_UNDERFLOW", pc)
        return stack.pop()

    while steps < max_steps:
        if pc not in by_offset:
            return {"status": "ERROR", "reason": "BAD_TARGET", "pc": pc,
                    "steps": steps, "output_bytes": list(output),
                    "stack": stack, "trace": events}
        instruction = by_offset[pc]
        if events is not None:
            events.append({"pc": pc, "op": MNEMONICS[instruction.opcode],
                           "stack": list(stack)})
        steps += 1
        next_pc = instruction.next_offset
        op = instruction.opcode
        try:
            if op == HALT:
                return {"status": "HALTED", "steps": steps,
                        "output_bytes": list(output), "stack": stack,
                        "trace": events}
            if op == PUSH_CONST:
                stack.append(instruction.operand)
            elif op == POP:
                pop()
            elif op == DUP:
                stack.append(pop()); stack.append(stack[-1])
            elif op == ADD:
                b, a = pop(), pop(); stack.append((a + b) & 0xFF)
            elif op == SUB:
                b, a = pop(), pop(); stack.append((a - b) & 0xFF)
            elif op == MUL:
                b, a = pop(), pop(); stack.append((a * b) & 0xFF)
            elif op in (CMP_EQ, CMP_LT, CMP_GT):
                b, a = pop(), pop()
                value = (a == b) if op == CMP_EQ else ((a < b) if op == CMP_LT else (a > b))
                stack.append(1 if value else 0)
            elif op == JUMP:
                next_pc = instruction.operand
            elif op == JUMP_IF_FALSE:
                condition = pop()
                if condition == 0:
                    next_pc = instruction.operand
            elif op == OUT_BYTE:
                output.append(pop() & 0xFF)
            elif op == IN_BYTE:
                value = input_bytes[input_cursor] if input_cursor < len(input_bytes) else 0xFF
                input_cursor += 1
                stack.append(value)
        except MBIR2LError as exc:
            return {"status": "ERROR", "reason": exc.reason, "pc": exc.pc,
                    "steps": steps, "output_bytes": list(output),
                    "stack": stack, "trace": events}
        pc = next_pc

    return {"status": "MAX_STEPS", "steps": steps, "output_bytes": list(output),
            "stack": stack, "trace": events}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an MBIR-2L blob")
    parser.add_argument("blob", help="hex blob")
    parser.add_argument("--input", default="", help="Latin-1 input")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    result = run(bytes.fromhex(args.blob), args.input.encode("latin-1"), trace=args.trace)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "HALTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
