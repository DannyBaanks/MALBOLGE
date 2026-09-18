"""tape_epoch.py — V0 savestate epoch: a bounded tape state crosses one epoch.

The V0 savestate is a fixed 32-cell tape. Pointer/PC remain driver metadata
while this serialization frontier is proven.

The epoch is a complete Malbolge Free computation compiled from generated
Brainfuck. It reads all 32 bytes, increments tape[0], and writes all 32 bytes
again. The whole selected state crosses the epoch boundary sealed by SHA-256.
This is not a general full-tape savestate or Brainfuck-compiler claim; it is
the smallest verifiable savestate-routing proof.

Commands:
  py tape_epoch.py compile
  py tape_epoch.py run --out fixtures\tape_epoch_demo.json
  py tape_epoch.py verify fixtures\tape_epoch_demo.json
  py tape_epoch.py tamper-demo fixtures\tape_epoch_demo.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMAT_ID = "malbolge-tape-epoch/1"
STATE_PROGRAM = HERE / "fixtures" / "tape_epoch.bf"
STATE_MAL = HERE / "fixtures" / "tape_epoch.mal"
TAPE_SIZE = 32
STATE_SIZE = TAPE_SIZE


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generated_bf(size: int = STATE_SIZE) -> str:
    """Read/output the whole state; cell 0 is incremented before output."""
    parts = []
    for index in range(size):
        if index:
            parts.append(">")
        parts.append(",")
        if index == 0:
            parts.append("+")
        parts.append(".")
    return "".join(parts)


def default_state() -> bytes:
    tape = bytearray(TAPE_SIZE)
    tape[0] = 2
    tape[1] = 7
    tape[3] = 9
    return bytes(tape)


def expected_transition(state: bytes) -> bytes:
    if len(state) != STATE_SIZE:
        raise ValueError(f"state must be {STATE_SIZE} bytes")
    tape = bytearray(state)
    tape[0] = (tape[0] + 1) & 0xFF
    return bytes(tape)


def run_epoch(state: bytes) -> tuple[bytes, str, int]:
    result = subprocess.run(
        [str(HERE / "epoch.exe"), "run", str(STATE_MAL), state.hex()],
        capture_output=True,
        text=True,
        check=True,
    )
    fields = dict(kv.split("=", 1) for kv in result.stderr.split())
    return bytes.fromhex(fields["stdout_hex"]), fields["status"], int(fields["steps"])


def manifest_for(state: bytes) -> dict:
    out, status, steps = run_epoch(state)
    expected = expected_transition(state)
    return {
        "format": FORMAT_ID,
        "state_size": STATE_SIZE,
        "layout": {"tape": TAPE_SIZE},
        "program_bf": str(STATE_PROGRAM.relative_to(HERE)),
        "program_mal": str(STATE_MAL.relative_to(HERE)),
        "program_sha256": sha256_hex(STATE_MAL.read_bytes()),
        "state_before_hex": state.hex(),
        "state_after_hex": out.hex(),
        "expected_after_hex": expected.hex(),
        "state_before_sha256": sha256_hex(state),
        "state_after_sha256": sha256_hex(out),
        "status": status,
        "steps": steps,
        "matches_reference": out == expected,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def verify(manifest: dict) -> list[str]:
    problems = []
    if manifest.get("format") != FORMAT_ID:
        return ["unknown format"]
    if sha256_file(STATE_MAL) != manifest["program_sha256"]:
        problems.append("compiled epoch program differs from sealed hash")
    before = bytes.fromhex(manifest["state_before_hex"])
    after = bytes.fromhex(manifest["state_after_hex"])
    if sha256_hex(before) != manifest["state_before_sha256"]:
        problems.append("state before fails its seal")
    if sha256_hex(after) != manifest["state_after_sha256"]:
        problems.append("state after fails its seal")
    replay, status, steps = run_epoch(before)
    if status != manifest["status"] or steps != manifest["steps"]:
        problems.append("replay status/steps diverged")
    if replay != after:
        problems.append("replay output differs from sealed savestate")
    if replay != expected_transition(before):
        problems.append("replay output differs from reference transition")
    return problems


def sha256_file(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def tamper_demo(manifest: dict) -> None:
    token = bytearray.fromhex(manifest["state_after_hex"])
    token[0] ^= 1
    if sha256_hex(bytes(token)) == manifest["state_after_sha256"]:
        print("tamper slipped through — must never happen")
        sys.exit(1)
    print(f"tampered savestate byte -> REJECTS (payload seal mismatch) 0x{token[:1].hex()}")

    tampered = json.loads(json.dumps(manifest))
    tampered["state_after_hex"] = bytes(token).hex()
    problems = verify(tampered)
    if not problems:
        print("edited savestate went UNNOTICED — must never happen")
        sys.exit(1)
    print(f"edited savestate without re-sealing -> verify REJECTS ({problems[0]})")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == "compile":
        STATE_PROGRAM.write_text(generated_bf(), encoding="ascii")
        subprocess.run(
            [str(HERE / "epoch.exe"), "compile", str(STATE_PROGRAM), str(STATE_MAL)],
            check=True,
        )
        print(f"compiled state={STATE_SIZE} bytes -> {STATE_MAL}")
        return 0

    if sys.argv[1] == "run":
        state = default_state()
        if "--state" in sys.argv:
            state_path = Path(sys.argv[sys.argv.index("--state") + 1])
            state = bytes.fromhex(state_path.read_text(encoding="ascii").strip())
        out_path = HERE / "fixtures" / "tape_epoch_demo.json"
        if "--out" in sys.argv:
            out_path = Path(sys.argv[sys.argv.index("--out") + 1])
        manifest = manifest_for(state)
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(
            f"state {STATE_SIZE}B -> epoch {manifest['status']} "
            f"steps={manifest['steps']} transition={'PASS' if manifest['matches_reference'] else 'FAIL'}"
        )
        print(f"sealed -> {out_path}")
        return 0 if manifest["matches_reference"] else 1

    manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    if sys.argv[1] == "verify":
        problems = verify(manifest)
        if problems:
            for problem in problems:
                print("MISMATCH:", problem)
            return 1
        print("savestate epoch replay OK; transition and seals verified")
        return 0
    if sys.argv[1] == "tamper-demo":
        tamper_demo(manifest)
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
