"""v2.py — Episodic Anchuring V2: each upper-level atomic op = one Malbolge epoch.

The upper machine here is a one-register machine with two operations:
  '+'  ->  r = r + 1 (mod 256)
  '-'  ->  r = r - 1 (mod 256)

Each operation is materialized as a COMPLETE Malbolge Free computation (a
"primitive epoch" program) that reads the current register byte on stdin and
writes the new register byte on stdout. The boundary between epochs is sealed
with SHA-256; nothing resumes; only output bytes cross.

This is the V2 claim in miniature and honestly:
  E_+  = Brainfuck '+'     -> one whole Malbolge computation
  E_-  = Brainfuck '-'     -> one whole Malbolge computation

Compiled epoch programs (see .bf sources): from the vendored Malfuck semantic
backend (Malbolge Free, width 10 fixed, TAPE_BASE assisted). Built with:
  zig build-exe epochtool.zig -O ReleaseFast  (then Move-Item -> epoch.exe)

Commands:
  py v2.py compile                     build plus.mal / minus.mal from .bf
  py v2.py run [PROGRAM] [--out PATH]  run a register program as epochs + seal
  py v2.py verify FILE                 replay every epoch, re-check seals
  py v2.py tamper-demo FILE            show a 1-bit change is rejected
  py v2.py macro-trace FILE            print the register (macro-state) trace
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMAT_ID = "malbolge-episodic-v2/1"
REGISTER0 = 0x30  # '0'

EPOCHS = {"+": "fixtures/plus.mal", "-": "fixtures/minus.mal"}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_epoch(program_file: str, token: bytes) -> tuple[int, str]:
    """One atomic op: a complete fresh Malbolge Free computation, sealed."""
    in_hex = token.hex()
    result = subprocess.run(
        [str(HERE / "epoch.exe"), "run", program_file, in_hex],
        capture_output=True, text=True, check=True)
    # output line: status=HALTED steps=N stdout_hex=.. (Zig debug.print -> stderr)
    fields = dict(kv.split("=", 1) for kv in result.stderr.split())
    status = fields["status"]
    steps = int(fields["steps"])
    out_hex = fields["stdout_hex"]
    return status, steps, bytes.fromhex(out_hex), in_hex


def build_v2(program: str) -> dict:
    """Materialize a register program as a chain of sealed epochs."""
    links = []
    token = bytes([REGISTER0])
    for op in program:
        if op not in EPOCHS:
            print(f"unknown op {op!r}")
            sys.exit(2)
        program_file = EPOCHS[op]
        source = (HERE / program_file).read_bytes()
        status, steps, out, in_hex = run_epoch(program_file, token)
        links.append({
            "op": op,
            "register_before": in_hex,
            "register_after": out.hex(),
            "program_file": program_file,
            "program_sha256": sha256_hex(source),
            "stdin_sha256": sha256_hex(token),
            "status": status,
            "steps": steps,
            "stdout_sha256": sha256_hex(out),
        })
        token = out
    return {
        "format": FORMAT_ID,
        "program": program,
        "register_start_hex": f"{REGISTER0:02x}",
        "register_final_hex": token.hex(),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "links": links,
    }


def verify(manifest: dict) -> list[str]:
    problems = []
    token = bytes([REGISTER0])
    for i, link in enumerate(manifest["links"]):
        source = (HERE / link["program_file"]).read_bytes()
        if sha256_hex(source) != link["program_sha256"]:
            problems.append(f"epoch {i}: program file differs from sealed hash")
        if sha256_hex(token) != link["stdin_sha256"]:
            problems.append(f"epoch {i}: stdin does not match sealed token")
        if link["op"] != manifest["program"][i]:
            problems.append(f"epoch {i}: op mismatch")
        status, steps, out, _ = run_epoch(link["program_file"], token)
        if status != link["status"] or steps != link["steps"]:
            problems.append(f"epoch {i}: replay diverged ({status}/{steps})")
        if sha256_hex(out) != link["stdout_sha256"]:
            problems.append(f"epoch {i}: replayed stdout fails the seal")
        if out.hex() != link["register_after"]:
            problems.append(f"epoch {i}: register transition wrong")
        token = out
    if token.hex() != manifest.get("register_final_hex"):
        problems.append("final register differs from sealed trace")
    return problems


def macro_trace(manifest: dict) -> None:
    states = [manifest["register_start_hex"]] + [l["register_after"] for l in manifest["links"]]
    print("ops:      " + "  ".join(l["op"] for l in manifest["links"]))
    print("register: " + " -> ".join(f"0x{s}" for s in states))
    for i, link in enumerate(manifest["links"]):
        print(f"  epoch {i}: {link['op']}  0x{link['register_before']} -> "
              f"0x{link['register_after']}  status={link['status']} "
              f"steps={link['steps']} sha={link['stdout_sha256'][:16]}")


def tamper_demo(manifest: dict) -> None:
    link = manifest["links"][0]
    token = bytearray.fromhex(link["register_after"])
    token[0] ^= 0x01
    if sha256_hex(bytes(token)) == link["stdout_sha256"]:
        print("tamper slipped through — must never happen")
        sys.exit(1)
    print(f"tampered epoch output (0x{token.hex()}) -> REJECTS (seal mismatch)")

    tampered = json.loads(json.dumps(manifest))
    tampered["links"][0]["register_after"] = token.hex()
    problems = verify(tampered)
    if not problems:
        print("edited register_after went UNNOTICED — must never happen")
        sys.exit(1)
    print(f"register_after edited without re-sealing -> verify REJECTS ({problems[0]})")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    if sys.argv[1] == "compile":
        for bf, mal in [("plus.bf", "fixtures/plus.mal"), ("minus.bf", "fixtures/minus.mal")]:
            subprocess.run([str(HERE / "epoch.exe"), "compile", bf, mal], check=True)
        print("compiled plus.mal + minus.mal")
        return 0

    if sys.argv[1] == "run":
        program = sys.argv[2] if len(sys.argv) > 2 else "+++-"
        out_path = HERE / "fixtures" / "v2_demo.json"
        if "--out" in sys.argv:
            out_path = Path(sys.argv[sys.argv.index("--out") + 1])
        manifest = build_v2(program)
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"program {program!r} -> register 0x{manifest['register_start_hex']} "
              f"-> 0x{manifest['register_final_hex']}")
        print(f"sealed -> {out_path}")
        return 0

    manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT_ID:
        print(f"unknown format: {manifest.get('format')!r}")
        return 2
    if sys.argv[1] == "verify":
        problems = verify(manifest)
        if problems:
            for p in problems:
                print("MISMATCH:", p)
            return 1
        print(f"replay OK: {len(manifest['links'])} epochs, all seals verified")
        return 0
    if sys.argv[1] == "macro-trace":
        macro_trace(manifest)
        return 0
    tamper_demo(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())