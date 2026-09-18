"""Deterministic finite Befunge-93 subset lowered to MBIR-2L."""
from __future__ import annotations

from collections import deque
from mbir_2l import (ADD, CMP_EQ, DUP, HALT, IN_BYTE, JUMP, JUMP_IF_FALSE,
                     MUL, OUT_BYTE, POP, PUSH_CONST, SUB, encode)


class BefungeUnsupported(ValueError):
    pass


def compile_source(source: str) -> bytes:
    lines = source.splitlines() or [source]
    if len(lines) > 25:
        raise BefungeUnsupported("grid exceeds canonical height 25")
    width, height = 80, 25
    grid = [line.ljust(width)[:width] for line in lines]
    grid.extend([" " * width] * (height - len(grid)))
    start = (0, 0, 1, 0)
    nodes, queue = [], deque([start]); seen = set()
    def next_state(x, y, dx, dy, count=1):
        return ((x + dx * count) % width, (y + dy * count) % height, dx, dy)
    edges = {}
    while queue:
        x, y, dx, dy = queue.popleft()
        state = (x, y, dx, dy)
        if state in seen: continue
        seen.add(state); nodes.append(state)
        char = grid[y][x]
        if char in '"?pg&':
            raise BefungeUnsupported(f"unsupported Befunge command {char!r} at position {x}")
        if char == '@': successors = []
        elif char == '_': successors = [next_state(x, y, 1, 0), next_state(x, y, -1, 0)]
        elif char == '|': successors = [next_state(x, y, 0, 1), next_state(x, y, 0, -1)]
        elif char == '>': successors = [next_state(x, y, 1, 0)]
        elif char == '<': successors = [next_state(x, y, -1, 0)]
        elif char == '^': successors = [next_state(x, y, 0, -1)]
        elif char == 'v': successors = [next_state(x, y, 0, 1)]
        elif char == '#': successors = [next_state(x, y, dx, dy, 2)]
        elif char in '0123456789+-*!,:~ ':
            successors = [next_state(x, y, dx, dy)]
        else:
            raise BefungeUnsupported(f"unsupported Befunge command {char!r} at position {x}")
        edges[state] = successors
        for successor in successors:
            if successor not in seen: queue.append(successor)
    index = {state: i for i, state in enumerate(nodes)}
    instructions = []
    pending = []
    node_instruction_index = {}
    for state in nodes:
        node_instruction_index[index[state]] = len(instructions)
        x, y, dx, dy = state; char = grid[y][x]
        if char.isdigit(): instructions.append((PUSH_CONST, int(char)))
        elif char == '+': instructions.append((ADD, None))
        elif char == '-': instructions.append((SUB, None))
        elif char == '*': instructions.append((MUL, None))
        elif char == '!': instructions.extend(((PUSH_CONST, 0), (CMP_EQ, None)))
        elif char == ':': instructions.append((DUP, None))
        elif char == '$': instructions.append((POP, None))
        elif char == ',': instructions.append((OUT_BYTE, None))
        elif char == '~': instructions.append((IN_BYTE, None))
        elif char == '@': instructions.append((HALT, None)); continue
        elif char in ' <>^v': pass
        elif char == '_': pass
        else: raise BefungeUnsupported(f"unsupported command {char!r} at position {x}")
        successors = edges[state]
        if char == '_':
            pending.append((len(instructions), index[successors[0]], 'false'))
            instructions.append((JUMP_IF_FALSE, None))
            pending.append((len(instructions), index[successors[1]], 'jump'))
            instructions.append((JUMP, None))
        else:
            pending.append((len(instructions), index[successors[0]], 'jump'))
            instructions.append((JUMP, None))
    offsets = []; offset = 0
    for opcode, operand in instructions:
        offsets.append(offset); offset += 1 + (1 if opcode == PUSH_CONST else 3 if opcode in (JUMP, JUMP_IF_FALSE) else 0)
    for instruction_index, target_node, kind in pending:
        opcode, _ = instructions[instruction_index]
        instructions[instruction_index] = (opcode, offsets[node_instruction_index[target_node]])
    return encode(instructions)


def run(source: str, input_bytes: bytes = b"", max_steps: int = 1_000_000) -> dict:
    from mbir_2l import run as run_mbir
    return run_mbir(compile_source(source), input_bytes, max_steps)
