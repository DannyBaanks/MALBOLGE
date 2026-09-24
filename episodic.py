"""episodic.py — Episodic Anchuring (V1).

A "macro-machine" whose every transition is a COMPLETE, fresh Malbolge
computation called an EPOCH. Between epochs, only sealed output bytes cross
(SHA-256), exactly like the V0 anchor discipline in `malbolge-anchuring`.

The leap over V0:
  - V0  : processo A --bytes--> processo B          (the anchor vouches bytes)
  - V1  : each whole Malbolge run is ONE ATOMIC STEP of a higher machine;
          the macro-observer sees a state trace 0 -> 1 -> 2 -> ...

Honesty contract (unchanged from V0, made explicit):
  - NO process resumption          (every epoch starts fresh)
  - NO serialized mid-run state
  - NO Turing-completeness claim
  - only sealed output bytes cross an epoch boundary
  - the anchor does NOT compute semantics; it vouches integrity

This V1 harness establishes the FRONTIER and the SEAL. Whether an epoch
actually COMPUTES a macro transition (as opposed to just re-committing
bytes) is the V2 question; see V2_NOTE in README.

Commands:
  python3 episodic.py run [--out PATH]     build + seal an episodic chain
  python3 episodic.py verify FILE          replay every epoch, re-check seals
  python3 episodic.py tamper-demo FILE     show a 1-bit change is rejected
  python3 episodic.py macro-trace FILE     print the macro state timeline
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import malbolge
from gen_echo import gen_echo

FORMAT_ID = "malbolge-episodic/1"
HERE = Path(__file__).resolve().parent
HELLO_FILE = "fixtures/hello.mal"
FUEL = 200_000


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_epoch(index: int, program_file: str, source: str,
              stdin_data: bytes) -> dict:
    """One macro-step: a complete, fresh Malbolge computation + seal."""
    status, steps, stdout = malbolge.run(
        source, stdin_data=stdin_data, max_steps=FUEL)
    return {
        "macro_state_before": index,          # the frontier the observer reads
        "macro_state_after": index + 1,
        "program_file": program_file,
        "program_sha256": sha256_hex(source.encode("latin-1")),
        "fuel": FUEL,
        "stdin_hex": stdin_data.hex(),
        "stdin_sha256": sha256_hex(stdin_data),
        "status": status,
        "steps": steps,
        "stdout_hex": stdout.hex(),
        "stdout_sha256": sha256_hex(stdout),
    }


def feed(sealed_sha256: str, payload: bytes) -> bool:
    """The only gate between epochs: exact hash or no entry."""
    return sha256_hex(payload) == sealed_sha256


def build_episodic() -> dict:
    """hello -> echo12 -> echo12, sealed at every boundary, macro trace 0..3.

    Each link is a brand-new Malbolge process. The bytes that move are sealed;
    the macro-observer counts the frontier as a complete computation happens."""
    hello_src = (HERE / HELLO_FILE).read_text(encoding="latin-1").strip()
    links = []
    payload = b""
    for i, (prog_file, src) in enumerate([
        (HELLO_FILE, hello_src),
    ]):
        links.append(run_epoch(i, prog_file, src, payload))
        payload = bytes.fromhex(links[-1]["stdout_hex"])

    # echo the payload twice: two more complete computations, macro-state 1->2->3
    echo_src = gen_echo(len(payload))
    echo_file = f"fixtures/echo{len(payload)}.mal"
    (HERE / echo_file).write_text(echo_src, encoding="latin-1")
    for i in range(1, 3):
        assert feed(links[-1]["stdout_sha256"], payload)
        links.append(run_epoch(i, echo_file, echo_src, payload))
        payload = bytes.fromhex(links[-1]["stdout_hex"])

    return {
        "format": FORMAT_ID,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "macro_states": [0] + [link["macro_state_after"] for link in links],
        "links": links,
    }


def verify(manifest: dict) -> list[str]:
    problems = []
    links = manifest.get("links", [])
    prev_out = None
    for i, link in enumerate(links):
        source = (HERE / link["program_file"]).read_text(encoding="latin-1")
        if sha256_hex(source.encode("latin-1")) != link["program_sha256"]:
            problems.append(f"epoch {i}: program file differs from sealed hash")
            continue
        stdin_bytes = bytes.fromhex(link["stdin_hex"])
        if sha256_hex(stdin_bytes) != link["stdin_sha256"]:
            problems.append(f"epoch {i}: recorded stdin fails its own seal")
        if i > 0 and sha256_hex(stdin_bytes) != prev_out:
            problems.append(f"epoch {i}: stdin does not match sealed stdout "
                            f"of epoch {i-1}")
        recorded_stdout = bytes.fromhex(link["stdout_hex"])
        if sha256_hex(recorded_stdout) != link["stdout_sha256"]:
            problems.append(f"epoch {i}: recorded stdout fails its own seal")
        if link["macro_state_before"] != i or link["macro_state_after"] != i + 1:
            problems.append(f"epoch {i}: macro-state frontier broken "
                            f"({link['macro_state_before']}->"
                            f"{link['macro_state_after']})")
        status, steps, stdout = malbolge.run(
            source, stdin_data=stdin_bytes, max_steps=link["fuel"])
        if status != link["status"] or steps != link["steps"]:
            problems.append(f"epoch {i}: replay diverged "
                            f"({status}/{steps} vs {link['status']}/{link['steps']})")
        if sha256_hex(stdout) != link["stdout_sha256"]:
            problems.append(f"epoch {i}: replayed stdout fails the seal")
        prev_out = link["stdout_sha256"]
    return problems


def tamper_demo(manifest: dict) -> None:
    link0 = manifest["links"][0]
    payload = bytearray.fromhex(link0["stdout_hex"])
    original = link0["stdout_sha256"]
    payload[0] ^= 0x01
    if feed(original, bytes(payload)):
        print("1-bit tampered payload was ACCEPTED — must never happen")
        sys.exit(1)
    print(f"1-bit tampered epoch output ({bytes(payload)!r}) -> REJECTED")

    tampered = json.loads(json.dumps(manifest))
    hexed = bytearray.fromhex(tampered["links"][0]["stdout_hex"])
    hexed[0] ^= 0x01
    tampered["links"][0]["stdout_hex"] = hexed.hex()
    problems = verify(tampered)
    if not problems:
        print("edited stdout_hex went UNNOTICED by verify — must never happen")
        sys.exit(1)
    print(f"stdout_hex edited without re-sealing -> verify REJECTS ({problems[0]})")


def macro_trace(manifest: dict) -> None:
    print(f"macro trace: {' -> '.join(str(s) for s in manifest['macro_states'])}")
    for i, link in enumerate(manifest["links"]):
        print(f"  epoch {i}: state {link['macro_state_before']} -> "
              f"{link['macro_state_after']}  "
              f"program={link['program_file']} "
              f"status={link['status']} steps={link['steps']} "
              f"out_sha256={link['stdout_sha256'][:16]}")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "verify", "tamper-demo", "macro-trace"):
        print(__doc__)
        return 2

    if sys.argv[1] == "run":
        out_path = HERE / "fixtures" / "episodic_demo.json"
        if "--out" in sys.argv:
            out_path = Path(sys.argv[sys.argv.index("--out") + 1])
        manifest = build_episodic()
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for link in manifest["links"]:
            print(f"epoch{link['macro_state_before']}: {link['program_file']} "
                  f"status={link['status']} steps={link['steps']} "
                  f"out={bytes.fromhex(link['stdout_hex'])!r}")
        print(f"episodic chain sealed -> {out_path}")
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
        print(f"replay OK: {len(manifest['links'])} epochs, "
              f"all seals verified, deterministic")
        return 0

    if sys.argv[1] == "macro-trace":
        macro_trace(manifest)
        return 0

    tamper_demo(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())