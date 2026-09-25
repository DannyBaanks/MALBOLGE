"""Build the native Zig helpers next to the Python sources.

  python3 build_native.py

Uses ``zig`` from PATH, or the ``ziglang`` PyPI package
(``pip install ziglang==0.16.0``) when zig is not installed.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

from binaries import EXE_SUFFIX, HERE

TARGETS = (
    ("epochtool.zig", "epoch", "ReleaseFast"),
    ("intermediate_vm_runner.zig", "intermediate_vm_runner", "ReleaseSafe"),
)


def zig_command() -> list[str]:
    zig = shutil.which("zig")
    if zig:
        return [zig]
    try:
        import ziglang  # noqa: F401
    except ImportError:
        sys.exit("zig not found: install zig 0.16 or `pip install ziglang==0.16.0`")
    return [sys.executable, "-m", "ziglang"]


def main() -> int:
    zig = zig_command()
    for source, stem, mode in TARGETS:
        out = HERE / (stem + EXE_SUFFIX)
        print(f"{source} -> {out.name} ({mode})")
        subprocess.run([*zig, "build-exe", source, "-O", mode, f"-femit-bin={out}"],
                       cwd=HERE, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
