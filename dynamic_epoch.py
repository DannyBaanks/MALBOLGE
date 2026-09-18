"""V4 dynamic cell selection using a one-hot serialized pointer.

Payload layout is [pointer][flag0,cell0]...[flag7,cell7]. Exactly one flag is
1 and the other seven are 0. The flags are an explicit one-hot workspace: the
Malbolge epoch consumes them while adding each flag into its paired cell, but
the scalar pointer and all cells remain in the emitted payload. The next epoch
regenerates the workspace from that persistent pointer.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BF = HERE / "fixtures" / "dynamic_onehot.bf"
MAL = HERE / "fixtures" / "dynamic_onehot.mal"
FORMAT = "malbolge-dynamic-onehot/1"
PAIRS = 8
SIZE = 1 + PAIRS * 2


def program() -> str:
    # Read the whole interleaved state into the epoch tape.
    read = "," + ">," * (SIZE - 1)
    # Skip the persistent pointer and add each one-hot flag into its cell.
    # After the last input the cursor is at cell SIZE-1; flag0 is cell 1.
    select = "<" * (SIZE - 2) + "[->+<]>>" * PAIRS
    # Return to cell zero and emit the complete payload.
    emit = "<" * SIZE + ".>" * (SIZE - 1) + "."
    return read + select + emit


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def onehot(pointer: int, cells: bytes) -> bytes:
    if not 0 <= pointer < PAIRS or len(cells) != PAIRS:
        raise ValueError("pointer must be 0..7 and cells must contain 8 bytes")
    return bytes((pointer,)) + b"".join(
        bytes((1 if i == pointer else 0, cells[i])) for i in range(PAIRS))


def run(payload: bytes):
    p = subprocess.run([str(HERE / "epoch.exe"), "run", str(MAL), payload.hex()],
                       capture_output=True, text=True, check=True)
    fields = dict(item.split("=", 1) for item in p.stderr.split())
    return fields["status"], int(fields["steps"]), bytes.fromhex(fields["stdout_hex"])


def unpack(payload: bytes) -> tuple[int, bytes]:
    if len(payload) != SIZE:
        raise ValueError("bad payload size")
    pointer = payload[0]
    flags = payload[1::2]
    cells = payload[2::2]
    if flags.count(1) != 1 or any(flag not in (0, 1) for flag in flags):
        raise ValueError("pointer flags are not one-hot")
    return pointer, cells


def build() -> dict:
    records = []
    for pointer in range(PAIRS):
        cells = bytes((10 + i for i in range(PAIRS)))
        before = onehot(pointer, cells)
        status, steps, after = run(before)
        expected_cells = bytearray(cells)
        expected_cells[pointer] = (expected_cells[pointer] + 1) & 0xff
        expected = bytes((pointer,)) + b"".join(
            bytes((0, expected_cells[i])) for i in range(PAIRS))
        records.append({
            "pointer": pointer,
            "before_hex": before.hex(),
            "after_hex": after.hex(),
            "expected_hex": expected.hex(),
            "before_sha256": sha(before),
            "after_sha256": sha(after),
            "status": status,
            "steps": steps,
            "matches_reference": after == expected,
        })
    return {"format": FORMAT, "payload_size": SIZE,
            "program_sha256": sha(MAL.read_bytes()), "records": records}


def verify(manifest: dict) -> list[str]:
    problems = []
    if manifest.get("program_sha256") != sha(MAL.read_bytes()):
        problems.append("program seal mismatch")
    for record in manifest["records"]:
        before = bytes.fromhex(record["before_hex"])
        after = bytes.fromhex(record["after_hex"])
        if sha(before) != record["before_sha256"] or sha(after) != record["after_sha256"]:
            problems.append(f"pointer {record['pointer']}: payload seal mismatch")
        status, steps, replay = run(before)
        if (status, steps, replay) != (record["status"], record["steps"], after):
            problems.append(f"pointer {record['pointer']}: replay mismatch")
        if after != bytes.fromhex(record["expected_hex"]):
            problems.append(f"pointer {record['pointer']}: dynamic selection mismatch")
    return problems


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: dynamic_epoch.py compile|run|verify|tamper-demo")
        return 2
    if sys.argv[1] == "compile":
        BF.write_text(program(), encoding="ascii")
        subprocess.run([str(HERE / "epoch.exe"), "compile", str(BF), str(MAL)], check=True)
        print(f"compiled dynamic payload={SIZE} bytes")
        return 0
    manifest_path = HERE / "fixtures" / "dynamic_onehot_demo.json"
    if sys.argv[1] == "run":
        manifest = build()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for record in manifest["records"]:
            print(f"ptr={record['pointer']}: {record['before_hex']} -> "
                  f"{record['after_hex']} ({record['steps']} steps)")
        return 0 if all(r["matches_reference"] for r in manifest["records"]) else 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sys.argv[1] == "verify":
        problems = verify(manifest)
        print("dynamic selection replay OK: pointers 0..7" if not problems else "\n".join(problems))
        return 0 if not problems else 1
    # Change cell0 (bytes 2..3), not the pointer byte; pointer 0 is already 00.
    after = manifest["records"][0]["after_hex"]
    manifest["records"][0]["after_hex"] = after[:4] + "ff" + after[6:]
    problems = verify(manifest)
    print("tamper REJECTS: " + problems[0] if problems else "tamper accepted")
    return 0 if problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
