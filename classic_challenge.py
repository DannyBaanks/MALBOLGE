"""Generate and execute a hand-encoded Classic Malbolge challenge.

The source is not hardcoded: every character is produced by classic_encoder's
inverse equation at its actual load position. The challenge deliberately runs
several nontrivial Classic operations before halting.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import malbolge
from classic_encoder import encode

HERE = Path(__file__).resolve().parent
PLAN = (23, 5, 39, 40, 62, 68, 81)  # in, out, rot, movd, opr, nop, end
NAMES = ("in", "out", "rot", "movd", "opr", "nop", "end")


def generate() -> str:
    return "".join(encode(opcode, position)[2]
                   for position, opcode in enumerate(PLAN))


def main() -> int:
    source = generate()
    decoded = [(ord(char) + position) % 94
               for position, char in enumerate(source)]
    status, steps, output = malbolge.run(source, stdin_data=b"Z", max_steps=1000)
    result = {
        "source": source,
        "source_ascii": [ord(char) for char in source],
        "plan": list(zip(NAMES, PLAN)),
        "decoded": decoded,
        "stdin": "Z",
        "status": status,
        "steps": steps,
        "stdout": output.decode("latin-1"),
        "source_sha256": hashlib.sha256(source.encode("ascii")).hexdigest(),
    }
    (HERE / "fixtures" / "classic_challenge.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print(f"source={source!r}")
    print(f"decoded={decoded}")
    print(f"run: status={status} steps={steps} stdout={output!r}")
    if decoded != list(PLAN) or (status, output) != ("HALTED", b"Z"):
        return 1
    print("CHALLENGE PASS: formula-generated Classic program executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
