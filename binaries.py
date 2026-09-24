"""Locate the native helpers built from the Zig sources, on any platform.

  epoch                   <- epochtool.zig            (V2/V3/V4 epoch executor)
  intermediate_vm_runner  <- intermediate_vm_runner.zig (E10..E19 runner)

Linux/macOS builds have no extension; Windows builds end in ``.exe``. Both are
looked up next to this file. ``MALBOLGE_EPOCH`` / ``MALBOLGE_VM_RUNNER`` override
the path. Build them with ``python3 build_native.py``.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""


class MissingBinary(FileNotFoundError):
    pass


def _find(stem: str, env: str) -> Path | None:
    override = os.environ.get(env)
    if override:
        return Path(override)
    for name in (stem + EXE_SUFFIX, stem, stem + ".exe"):
        path = HERE / name
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def _require(stem: str, env: str) -> Path:
    path = _find(stem, env)
    if path is None:
        raise MissingBinary(
            f"{stem}{EXE_SUFFIX} not found in {HERE}; build it with "
            f"`python3 build_native.py` (needs zig 0.16) or set {env}")
    return path


def find_epoch() -> Path | None:
    return _find("epoch", "MALBOLGE_EPOCH")


def epoch() -> Path:
    return _require("epoch", "MALBOLGE_EPOCH")


def find_vm_runner() -> Path | None:
    return _find("intermediate_vm_runner", "MALBOLGE_VM_RUNNER")


def vm_runner() -> Path:
    return _require("intermediate_vm_runner", "MALBOLGE_VM_RUNNER")


def find_piton() -> str | None:
    return shutil.which("piton")
