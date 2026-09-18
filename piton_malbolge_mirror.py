"""Differential mirror: one byte-stream runtime in Piton and Malbolge Classic.

Piton executes the source fixture directly. Malbolge executes a formula-built
IN/OUT program specialized only by input length. Both receive identical bytes;
the gate compares exact observable stdout and deterministic replay.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import malbolge
from classic_codec import assemble, disassemble

HERE = Path(__file__).resolve().parent
PITON_PROGRAM = HERE / "fixtures" / "piton_mirror.piton"
OUT = HERE / "fixtures" / "piton_malbolge_mirror.json"
IN, OUT_OP, END = 23, 5, 81
CORPUS = (
    b"",
    b"Z",
    b"ISyCo",
    bytes((0x00, 0x01, 0x20, 0x7f, 0x80, 0xfe, 0xff)),
    bytes(range(256)),
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def malbolge_source(size: int) -> str:
    return assemble(([IN, OUT_OP] * size) + [END])


def run_piton(payload: bytes) -> tuple[int, bytes, bytes]:
    result = subprocess.run(
        ["piton", "ejecutar", str(PITON_PROGRAM)],
        input=payload, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def run_case(payload: bytes) -> dict:
    source = malbolge_source(len(payload))
    decoded = [item.opcode for item in disassemble(source)]
    status, steps, mal_out = malbolge.run(source, payload, max_steps=10_000)
    status2, steps2, replay = malbolge.run(source, payload, max_steps=10_000)
    piton_code, piton_out, piton_err = run_piton(payload)
    expected_plan = ([IN, OUT_OP] * len(payload)) + [END]
    passed = (
        piton_code == 0
        and piton_out == payload
        and mal_out == payload
        and status == "HALTED"
        and decoded == expected_plan
        and (status2, steps2, replay) == (status, steps, mal_out)
    )
    return {
        "input_size": len(payload),
        "input_sha256": sha(payload),
        "piton_exit": piton_code,
        "piton_stdout_sha256": sha(piton_out),
        "piton_stderr": piton_err.decode("utf-8", "replace"),
        "malbolge_status": status,
        "malbolge_steps": steps,
        "malbolge_program_size": len(source),
        "malbolge_program_sha256": sha(source.encode("ascii")),
        "malbolge_stdout_sha256": sha(mal_out),
        "codec_plan_matches": decoded == expected_plan,
        "deterministic_replay": (status2, steps2, replay) == (status, steps, mal_out),
        "byte_exact_parity": piton_out == mal_out == payload,
        "pass": passed,
    }


def main() -> int:
    cases = [run_case(payload) for payload in CORPUS]
    manifest = {
        "format": "piton-malbolge-mirror/1",
        "piton_program": str(PITON_PROGRAM.relative_to(HERE)),
        "piton_program_sha256": sha(PITON_PROGRAM.read_bytes()),
        "cases": cases,
        "pass": all(case["pass"] for case in cases),
    }
    OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for case in cases:
        print(f"{case['input_size']:3d} bytes: PITON={case['piton_exit']} "
              f"Malbolge={case['malbolge_status']}/{case['malbolge_steps']} "
              f"parity={'PASS' if case['pass'] else 'FAIL'}")
    print("MIRROR PASS: PITON == Malbolge Classic"
          if manifest["pass"] else "MIRROR FAIL")
    print(f"evidence={OUT}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
