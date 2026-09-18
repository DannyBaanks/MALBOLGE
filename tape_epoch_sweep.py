"""Empirical savestate-size sweep for tape_epoch.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import tape_epoch

HERE = Path(__file__).resolve().parent
SIZES = (1, 2, 4, 8, 16, 32, 64, 96, 111, 112, 128, 256)


def state_for(size: int) -> bytes:
    values = bytearray(size)
    for index in range(size):
        values[index] = (index * 7 + 3) & 0xFF
    return bytes(values)


def main() -> int:
    failures = 0
    for size in SIZES:
        tape_epoch.TAPE_SIZE = size
        tape_epoch.STATE_SIZE = size
        tape_epoch.STATE_PROGRAM = HERE / "fixtures" / f"tape_epoch_{size}.bf"
        tape_epoch.STATE_MAL = HERE / "fixtures" / f"tape_epoch_{size}.mal"
        tape_epoch.STATE_PROGRAM.write_text(tape_epoch.generated_bf(size), encoding="ascii")
        subprocess.run(
            [str(HERE / "epoch.exe"), "compile", str(tape_epoch.STATE_PROGRAM), str(tape_epoch.STATE_MAL)],
            check=True,
        )
        state = state_for(size)
        manifest = tape_epoch.manifest_for(state)
        path = HERE / "fixtures" / f"tape_epoch_{size}.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        ok = manifest["matches_reference"]
        print(
            f"size={size:3d} status={manifest['status']:9s} steps={manifest['steps']:8d} "
            f"transition={'PASS' if ok else 'FAIL'} manifest={path.name}"
        )
        if not ok:
            failures += 1
    print(f"boundary sweep: {len(SIZES) - failures}/{len(SIZES)} pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
