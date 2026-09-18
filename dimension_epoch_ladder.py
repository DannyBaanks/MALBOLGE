"""Experiment: a parametric Malbolge epoch ladder E10 -> E19.

This is a research harness, not a claim that Classic semantics automatically
become Unshackled semantics. For each k, memory has 3**k cells, the positional
instruction equation is applied, and the same [IN, OUT, END] toy crosses the
epoch boundary. Only the state byte is transported.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = "ubO"
DIMENSIONS = tuple(range(10, 20))
FORMAT = "malbolge-dimension-epoch-ladder/1"
SCHEMA_VERSION = 1
PROFILE = "TOY_ZERO_OFFSET"
MEMORY_MODEL = "SPARSE_TOY"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_zero_offset(opcode: int, position: int) -> str:
    residue = (opcode - position) % 94
    return chr(residue if residue >= 33 else residue + 94)


def decode_zero_offset(character: str, position: int) -> int:
    return (ord(character) + position) % 94


def source_for_toy() -> str:
    return "".join(encode_zero_offset(op, pos)
                   for pos, op in enumerate((23, 5, 81)))


@dataclass
class Epoch:
    schema_version: int
    profile: str
    memory_model: str
    dimension: int
    memory_cells: int
    source: str
    source_sha256: str
    state_before_hex: str
    state_after_hex: str
    state_before_sha256: str
    state_after_sha256: str
    decoded_ops: list[int]
    status: str
    steps: int
    final_a: int
    final_c: int
    final_d: int


def run_epoch(dimension: int, payload: bytes) -> tuple[bytes, Epoch]:
    if dimension < 1:
        raise ValueError("dimension must be positive")
    source = source_for_toy()
    decoded = [decode_zero_offset(char, pos)
               for pos, char in enumerate(source)]
    if decoded != [23, 5, 81]:
        raise AssertionError(decoded)
    a = c = d = steps = 0
    output = bytearray()
    for opcode in decoded:
        steps += 1
        if opcode == 23:
            a = payload[0] if payload else (3 ** dimension - 1) & 0xff
        elif opcode == 5:
            output.append(a & 0xff)
        elif opcode == 81:
            after = bytes(output)
            return after, Epoch(
                SCHEMA_VERSION, PROFILE, MEMORY_MODEL,
                dimension, 3 ** dimension, source,
                sha(source.encode("ascii")), payload.hex(), after.hex(),
                sha(payload), sha(after), decoded, "HALTED", steps, a, c, d)
        c = (c + 1) % (3 ** dimension)
        d = (d + 1) % (3 ** dimension)
    raise AssertionError("toy did not halt")


def build() -> dict:
    state = b"Z"
    epochs = []
    for dimension in DIMENSIONS:
        state, epoch = run_epoch(dimension, state)
        epochs.append(asdict(epoch))
    return {"format": FORMAT, "schema_version": SCHEMA_VERSION,
            "profile": PROFILE, "memory_model": MEMORY_MODEL,
            "source": SOURCE, "dimensions": list(DIMENSIONS),
            "epochs": epochs, "final_state_hex": state.hex()}


def verify(manifest: dict) -> list[str]:
    problems = []
    if manifest.get("format") != FORMAT:
        problems.append("manifest format mismatch")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        problems.append("manifest schema version mismatch")
    if manifest.get("profile") != PROFILE:
        problems.append("manifest profile mismatch")
    if manifest.get("memory_model") != MEMORY_MODEL:
        problems.append("manifest memory model mismatch")
    if manifest.get("dimensions") != list(DIMENSIONS):
        problems.append("manifest dimension ladder mismatch")
    if not manifest.get("epochs"):
        return problems + ["manifest has no epochs"]
    state = bytes.fromhex(manifest["epochs"][0]["state_before_hex"])
    for expected in manifest["epochs"]:
        if expected["schema_version"] != SCHEMA_VERSION:
            problems.append(f"E{expected['dimension']}: schema mismatch")
        if expected["profile"] != PROFILE:
            problems.append(f"E{expected['dimension']}: profile mismatch")
        if expected["memory_model"] != MEMORY_MODEL:
            problems.append(f"E{expected['dimension']}: memory model mismatch")
        if expected["memory_cells"] != 3 ** expected["dimension"]:
            problems.append(f"E{expected['dimension']}: memory size mismatch")
        if expected["state_before_hex"] != state.hex():
            problems.append(f"E{expected['dimension']}: chain input mismatch")
        if sha(state) != expected["state_before_sha256"]:
            problems.append(f"E{expected['dimension']}: input seal mismatch")
        replay, actual = run_epoch(expected["dimension"], state)
        if asdict(actual) != expected:
            problems.append(f"E{expected['dimension']}: replay diverged")
        state = replay
    if state.hex() != manifest["final_state_hex"]:
        problems.append("final ladder state mismatch")
    return problems


def main() -> int:
    manifest_path = HERE / "fixtures" / "dimension_epoch_ladder.json"
    manifest = build()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    problems = verify(manifest)
    for epoch in manifest["epochs"]:
        print(f"E{epoch['dimension']}: memory={epoch['memory_cells']} "
              f"ops={epoch['decoded_ops']} state={epoch['state_after_hex']} "
              f"steps={epoch['steps']}")
    print("LADDER PASS: E10 -> E19" if not problems else "\n".join(problems))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
