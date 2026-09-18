"""Pre-registered offset-formula gates for E11 through E18.

The hypothesis under test is deliberately explicit: generalize the E19
three-region expression by replacing only END and THIRD, while freezing its
two Classic anchor constants.  ``preregister`` performs no program execution;
``run`` refuses to proceed unless the table hash matches the registration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from classic_encoder import OPCODES

HERE = Path(__file__).resolve().parent
REGISTRATION = HERE / "evidence" / "offset_epoch_registration.json"
FORMAT = "malbolge-offset-epoch-ladder/1"
EPOCHS = tuple(range(11, 19))
CLASSIC_ANCHOR_HALF = (3 ** 10 - 1) // 2
CLASSIC_ANCHOR_END = 3 ** 10 - 1
TOY_OPCODES = (23, 5, 81)  # IN, OUT, END


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def offsets_for(dimension: int) -> tuple[int, int, int]:
    end = 3 ** dimension
    third = 3 ** (dimension - 1)
    a1 = 94 - (((end - 1) // 6) - CLASSIC_ANCHOR_HALF) % 94
    a2 = 94 - (((end - 1) // 3) - CLASSIC_ANCHOR_END) % 94
    return (0, ((a1 - third) % 94) + 94,
            a2 - ((2 * third) % 94) + 94)


def table() -> list[dict]:
    return [{"dimension": k, "memory_cells": 3 ** k,
             "offsets": list(offsets_for(k))} for k in EPOCHS]


def preregister() -> dict:
    body = {
        "format": FORMAT,
        "hypothesis": "E19_EXPRESSION_GENERALIZED_END_THIRD_ONLY",
        "anchor_half": CLASSIC_ANCHOR_HALF,
        "anchor_end": CLASSIC_ANCHOR_END,
        "epochs": table(),
        "toy_opcodes": list(TOY_OPCODES),
        "success_criterion": "FORMULA_GENERALIZES(E_k)=DEMONSTRATED iff roundtrip and boundary gates pass at k",
        "failure_policy": "first failing k is preserved; later results do not erase it",
    }
    body["table_sha256"] = sha256(canonical_bytes(body["epochs"]))
    return body


def load_registration() -> dict:
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    expected = preregister()
    if registration != expected:
        raise RuntimeError("pre-registration changed after execution was authorized")
    return registration


def encode(opcode: int, position: int, dimension: int, offsets: tuple[int, ...]) -> str:
    if opcode not in OPCODES:
        raise ValueError(opcode)
    width = 3 ** (dimension - 1)
    region = position // width
    residue = (opcode - position - offsets[region]) % 94
    return chr(residue if residue >= 33 else residue + 94)


def decode(char: str, position: int, dimension: int, offsets: tuple[int, ...]) -> int:
    width = 3 ** (dimension - 1)
    return (ord(char) + position + offsets[position // width]) % 94


def run_toy(dimension: int, offsets: tuple[int, ...]) -> dict:
    source = "".join(encode(op, pos, dimension, offsets)
                     for pos, op in enumerate(TOY_OPCODES))
    decoded = [decode(char, pos, dimension, offsets)
               for pos, char in enumerate(source)]
    state = ord("Z")
    output = bytearray()
    for opcode in decoded:
        if opcode == 23:
            pass  # stdin supplies Z
        elif opcode == 5:
            output.append(state)
        elif opcode == 81:
            break
        else:
            raise AssertionError(f"unexpected toy opcode {opcode}")
    return {"source": source, "decoded": decoded,
            "expected_output_hex": "5a", "output_hex": output.hex(),
            "roundtrip_pass": decoded == list(TOY_OPCODES) and output == b"Z"}


def boundary_gate(dimension: int, offsets: tuple[int, ...]) -> dict:
    width = 3 ** (dimension - 1)
    end = 3 ** dimension
    positions = (0, 1, width - 1, width, width + 1,
                 2 * width - 1, 2 * width, 2 * width + 1, end - 1)
    checks = []
    for position in positions:
        for opcode in sorted(OPCODES):
            char = encode(opcode, position, dimension, offsets)
            checks.append({"position": position, "opcode": opcode,
                           "char": char, "decoded": decode(char, position, dimension, offsets),
                           "pass": decode(char, position, dimension, offsets) == opcode})
    return {"positions": list(positions), "checks": checks,
            "boundary_pass": all(item["pass"] for item in checks)}


def execute(registration: dict) -> dict:
    results = []
    first_failure = None
    for row in registration["epochs"]:
        k = row["dimension"]
        offsets = tuple(row["offsets"])
        toy = run_toy(k, offsets)
        boundary = boundary_gate(k, offsets)
        passed = toy["roundtrip_pass"] and boundary["boundary_pass"]
        result = {"dimension": k, "offsets": list(offsets),
                  "roundtrip": toy, "boundary": boundary,
                  "claim": (f"FORMULA_GENERALIZES_E{k}=DEMONSTRATED"
                            if passed else f"FORMULA_GENERALIZES_E{k}=NOT_DEMONSTRATED")}
        results.append(result)
        if not passed and first_failure is None:
            first_failure = k
    last_demonstrated = (first_failure - 1 if first_failure is not None else 18)
    return {"format": FORMAT, "registration_sha256":
            sha256(REGISTRATION.read_bytes()), "results": results,
            "first_failure": first_failure,
            "claim": (f"FORMULA_GENERALIZES_E11_TO_E{last_demonstrated}=DEMONSTRATED; "
                      f"E{first_failure}_TO_E19=NOT_DEMONSTRATED"
                      if first_failure is not None else
                      "FORMULA_GENERALIZES_E11_TO_E18=DEMONSTRATED")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "run"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    REGISTRATION.parent.mkdir(exist_ok=True)
    if args.command == "preregister":
        REGISTRATION.write_text(json.dumps(preregister(), indent=2) + "\n", encoding="utf-8")
        print(json.dumps(preregister(), sort_keys=True))
        return 0
    registration = load_registration()
    result = execute(registration)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for row in result["results"]:
        print(f"E{row['dimension']}: offsets={row['offsets']} "
              f"roundtrip={row['roundtrip']['roundtrip_pass']} "
              f"boundary={row['boundary']['boundary_pass']} {row['claim']}")
    print(json.dumps(result, indent=2))
    return 0 if result["first_failure"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
