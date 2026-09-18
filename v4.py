"""V4: full serialized macrostate crosses every epoch boundary.

State format: [pointer][cell0..cell7] = 9 bytes. The compiled epoch reads and
writes all 9 bytes, incrementing the selected slot (cell1 in this first
windowed proof). Every complete payload is sealed with SHA-256.

This proves full-state transport, not yet arbitrary pointer indexing.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EPOCH = "fixtures/fullstate_plus.mal"
FORMAT = "malbolge-fullstate/1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_epoch(state: bytes):
    p = subprocess.run(
        [str(HERE / "epoch.exe"), "run", EPOCH, state.hex()],
        capture_output=True, text=True, check=True)
    fields = dict(x.split("=", 1) for x in p.stderr.split())
    return fields["status"], int(fields["steps"]), bytes.fromhex(fields["stdout_hex"])


def build(rounds: int = 3):
    state = bytes(9)
    links = []
    for i in range(rounds):
        status, steps, out = run_epoch(state)
        if len(out) != 9:
            raise RuntimeError(f"epoch returned {len(out)} bytes, expected 9")
        links.append({
            "epoch": i,
            "state_before_hex": state.hex(),
            "state_after_hex": out.hex(),
            "stdin_sha256": sha(state),
            "stdout_sha256": sha(out),
            "program_sha256": sha((HERE / EPOCH).read_bytes()),
            "status": status,
            "steps": steps,
        })
        state = out
    return {"format": FORMAT, "rounds": rounds, "links": links,
            "final_state_hex": state.hex()}


def verify(manifest):
    problems = []
    state = bytes.fromhex(manifest["links"][0]["state_before_hex"])
    for link in manifest["links"]:
        if state.hex() != link["state_before_hex"]:
            problems.append(f"epoch {link['epoch']}: state chain broken")
        if sha(state) != link["stdin_sha256"]:
            problems.append(f"epoch {link['epoch']}: input seal broken")
        status, steps, out = run_epoch(state)
        if status != link["status"] or steps != link["steps"]:
            problems.append(f"epoch {link['epoch']}: replay diverged")
        if out.hex() != link["state_after_hex"]:
            problems.append(f"epoch {link['epoch']}: output differs")
        if sha(out) != link["stdout_sha256"]:
            problems.append(f"epoch {link['epoch']}: output seal broken")
        state = out
    if state.hex() != manifest["final_state_hex"]:
        problems.append("final state differs")
    return problems


def main():
    if len(sys.argv) < 2:
        print("usage: v4.py compile|run|verify|tamper-demo")
        return 2
    if sys.argv[1] == "compile":
        subprocess.run([str(HERE / "epoch.exe"), "compile",
                        "fixtures/fullstate_plus.bf", EPOCH], check=True)
        return 0
    if sys.argv[1] == "run":
        m = build()
        Path(HERE / "fixtures/fullstate_demo.json").write_text(
            json.dumps(m, indent=2), encoding="utf-8")
        print("full state chain:")
        for link in m["links"]:
            print(f"  {link['epoch']}: {link['state_before_hex']} -> "
                  f"{link['state_after_hex']} ({link['steps']} steps)")
        return 0
    m = json.loads(Path(HERE / "fixtures/fullstate_demo.json").read_text())
    if sys.argv[1] == "verify":
        problems = verify(m)
        print("replay OK: full 9-byte state sealed" if not problems else "\n".join(problems))
        return 0 if not problems else 1
    m["links"][0]["state_after_hex"] = "ff" + m["links"][0]["state_after_hex"][2:]
    problems = verify(m)
    print("tamper REJECTS: " + problems[0] if problems else "tamper accepted")
    return 0 if problems else 1


if __name__ == "__main__":
    sys.exit(main())
