"""Closed WebAssembly MVP expression subset lowered to MBIR-2L."""
from __future__ import annotations

from mbir_2l import (ADD, CMP_EQ, CMP_GT, CMP_LT, HALT, JUMP, JUMP_IF_FALSE,
                     MUL, OUT_BYTE, PUSH_CONST, SUB, encode)


class WasmUnsupported(ValueError):
    pass


def _u32(data: bytes, pos: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        if pos >= len(data): raise WasmUnsupported("truncated leb128")
        byte = data[pos]; pos += 1; value |= (byte & 0x7f) << shift
        if not byte & 0x80: return value, pos
        shift += 7


def _name(data: bytes, pos: int) -> tuple[str, int]:
    size, pos = _u32(data, pos); end = pos + size
    if end > len(data): raise WasmUnsupported("truncated name")
    return data[pos:end].decode("utf-8"), end


def compile_module(module: bytes) -> bytes:
    if module[:8] != b"\x00asm\x01\x00\x00\x00": raise WasmUnsupported("bad Wasm magic/version")
    pos = 8; body = None; exported_run = False
    while pos < len(module):
        section = module[pos]; size, pos = _u32(module, pos + 1); end = pos + size
        if end > len(module): raise WasmUnsupported("truncated section")
        payload = module[pos:end]; pos = end
        if section in (2, 5): raise WasmUnsupported("imports or memory unsupported")
        if section == 7:
            count, p = _u32(payload, 0)
            for _ in range(count):
                name, p = _name(payload, p); kind = payload[p]; index = payload[p + 1]; p += 2
                exported_run |= name == "run" and kind == 0 and index == 0
        if section == 10:
            count, p = _u32(payload, 0)
            if count != 1: raise WasmUnsupported("only one function supported")
            body_size, p = _u32(payload, p); raw = payload[p:p + body_size]
            if len(raw) != body_size: raise WasmUnsupported("truncated function body")
            local_count, p = _u32(raw, 0)
            if local_count: raise WasmUnsupported("locals unsupported")
            body = raw[p:]
    if not exported_run or body is None: raise WasmUnsupported("module must export function run")

    instructions: list[tuple[int, int | None]] = []
    patches: list[tuple[int, int]] = []
    opmap = {0x6a: ADD, 0x6b: SUB, 0x6c: MUL, 0x46: CMP_EQ, 0x48: CMP_LT, 0x4a: CMP_GT}
    p = 0

    def sequence(allow_else: bool) -> str:
        nonlocal p
        while p < len(body):
            opcode = body[p]; p += 1
            if opcode == 0x0b: return "end"
            if opcode == 0x05:
                if allow_else: return "else"
                raise WasmUnsupported("unexpected else")
            if opcode == 0x41:
                value, p = _u32(body, p)
                if value > 255: raise WasmUnsupported("i32.const outside byte profile")
                instructions.append((PUSH_CONST, value)); continue
            if opcode in opmap:
                instructions.append((opmap[opcode], None)); continue
            if opcode == 0x04:
                if p >= len(body): raise WasmUnsupported("truncated if blocktype")
                blocktype = body[p]; p += 1
                if blocktype != 0x40: raise WasmUnsupported("only void if blocks supported")
                jif = len(instructions); instructions.append((JUMP_IF_FALSE, None))
                arm = sequence(True)
                if arm == "else":
                    jump = len(instructions); instructions.append((JUMP, None))
                    else_target = len(instructions)
                    end_arm = sequence(False)
                    patches.append((jif, else_target)); patches.append((jump, len(instructions)))
                    if end_arm != "end": raise WasmUnsupported("missing if end")
                else:
                    patches.append((jif, len(instructions)))
                continue
            raise WasmUnsupported(f"unsupported Wasm opcode 0x{opcode:02x}")
        raise WasmUnsupported("missing function end")

    if sequence(False) != "end" or p != len(body): raise WasmUnsupported("invalid function expression")
    instructions.extend(((OUT_BYTE, None), (HALT, None)))
    offsets: list[int] = []; offset = 0
    for opcode, _ in instructions:
        offsets.append(offset); offset += 1 + (1 if opcode == PUSH_CONST else 3 if opcode in (JUMP, JUMP_IF_FALSE) else 0)
    for instruction_index, target_index in patches:
        opcode, _ = instructions[instruction_index]
        instructions[instruction_index] = (opcode, offsets[target_index])
    return encode(instructions)
