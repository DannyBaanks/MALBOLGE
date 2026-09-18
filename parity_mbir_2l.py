"""Run equivalent Befunge and WebAssembly sources through MBIR-2L."""
from __future__ import annotations

import json

from befunge_mbir import compile_source as compile_befunge
from mbir_2l import run
from wasm_mbir import compile_module


def wasm_const_add() -> bytes:
    return bytes.fromhex("0061736d010000000105016000017f030201000707010372756e00000a09010700410241036a0b")


def run_parity() -> dict:
    cases = [("arithmetic_add", compile_befunge("23+,@"), compile_module(wasm_const_add()), b"")]
    results = []
    for case_id, befunge_blob, wasm_blob, input_bytes in cases:
        left = run(befunge_blob, input_bytes)
        right = run(wasm_blob, input_bytes)
        semantic_fields = ("status", "output_bytes", "stack")
        equal = all(left[field] == right[field] for field in semantic_fields)
        results.append({"id": case_id, "befunge": left, "wasm": right,
                        "equal": equal, "steps_equal": left["steps"] == right["steps"]})
    return {"format": "mbir-2l-parity/1", "cases": results,
            "status": "PASS" if all(item["equal"] for item in results) else "FAIL"}


if __name__ == "__main__":
    print(json.dumps(run_parity(), sort_keys=True))
