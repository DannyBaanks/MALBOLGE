"""Caso Quijote: first-divergence probe Classic (k=10) vs Malbolge-19.

This is an analysis probe, not a deliverable VM. It reuses existing trusted
primitives only:

  - classic encode/decode from classic_codec.py (positional inverse)
  - k19 encode/decode from unshackled_codec.py (offset-region inverse)
  - Classic runtime semantics from malbolge.py (imported functions/table)
  - k19 width semantics via reference_width_vm.crazy_k (same documented
    semantics as intermediate_vm_runner.zig; the probe adds a lazy tape so a
    3-step run does not need to materialize 3^19 cells)

Question answered with evidence: for a literal-producing opcode plan, does
Malbolge-19 first diverge at ENCODING (desired op != executed op) or at
SEMANTICS (same op, different effect)?
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import malbolge  # Classic reference
import unshackled_codec  # k19 positional codec
from classic_codec import assemble as assemble_classic, decode as decode_classic
from reference_width_vm import crazy_k

NAMES = {4: "jmp", 5: "out", 23: "in", 39: "rot", 40: "movd", 62: "opr", 68: "nop", 81: "end"}
K19_END = 3 ** 19
K19_THIRD = 3 ** 18


def trace_classic(source: str, stdin_data: bytes, max_steps: int = 64) -> list[dict]:
    """Traced Classic run; step loop copied from malbolge.run."""
    mem = malbolge.load_memory(source)
    a = 0
    c = 0
    d = 0
    stdin_pos = 0
    events: list[dict] = []
    for step in range(1, max_steps + 1):
        cell_before = mem[c]
        decoded = (cell_before + c) % 94
        char_before = chr(mem[c]) if 33 <= mem[c] <= 126 else None
        mem_d_before = mem[d]
        a_before = a
        executed = decoded if decoded in NAMES else None
        if decoded == 4:
            c = mem[d]
        elif decoded == 5:
            out_byte = a % 256
        elif decoded == 23:
            if stdin_pos < len(stdin_data):
                a = stdin_data[stdin_pos]
                stdin_pos += 1
            else:
                a = malbolge.EOF_VALUE
        elif decoded == 39:
            mem[d] = mem[d] // 3 + (mem[d] % 3) * (3 ** 9)
            a = mem[d]
        elif decoded == 40:
            d = mem[d]
        elif decoded == 62:
            mem[d] = malbolge.crazy(a, mem[d])
            a = mem[d]
        elif decoded == 81:
            events.append({"step": step, "c": c, "d": d, "a_before": a_before,
                           "decoded_op": decoded, "executed_op": executed,
                           "source_char": char_before, "cell_before": cell_before,
                           "mem_d_before": mem_d_before, "mem_d_after": mem[d],
                           "a_after": a, "output": None, "halted": True})
            return events
        event = {"step": step, "c": c, "d": d, "a_before": a_before,
                 "decoded_op": decoded, "executed_op": executed,
                 "source_char": char_before, "cell_before": cell_before,
                 "mem_d_before": mem_d_before, "mem_d_after": mem[d],
                 "a_after": a, "output": a % 256 if decoded == 5 else None,
                 "halted": False}
        if 33 <= mem[c] <= 126:
            mem[c] = malbolge._ENCRYPT[mem[c]]
            event["encrypted_to"] = chr(mem[c])
        c = (c + 1) % malbolge.MEMORY_SIZE
        d = (d + 1) % malbolge.MEMORY_SIZE
        events.append(event)
    return events


def trace_k19(source: str, stdin_data: bytes, max_steps: int = 64) -> list[dict]:
    """Traced k19 run with lazy tape. Dispatch and op effects follow
    reference_width_vm.py / intermediate_vm_runner.zig exactly:
    op = (mem[c] + c + offsets[c // THIRD]) % 94, width-19 crazy/rotate,
    eof = 3^19 - 1, Classic printable xlat self-encryption."""
    tape: dict[int, int] = {}

    def cell(i: int) -> int:
        i %= K19_END
        if i not in tape:
            if i < len(source):
                tape[i] = ord(source[i])
            else:
                tape[i] = crazy_k(cell(i - 1), cell(i - 2), 19)
        return tape[i]

    a = 0
    c = 0
    d = 0
    stdin_pos = 0
    events: list[dict] = []
    for step in range(1, max_steps + 1):
        cell_before = cell(c)
        decoded = (cell_before + c + unshackled_codec.OFFSETS[c // K19_THIRD]) % 94
        char_before = chr(cell_before) if 33 <= cell_before <= 126 else None
        mem_d_before = cell(d)
        a_before = a
        executed = decoded if decoded in NAMES else None
        if decoded == 4:
            c = cell(d)
        elif decoded == 23:
            if stdin_pos < len(stdin_data):
                a = stdin_data[stdin_pos]
                stdin_pos += 1
            else:
                a = K19_END - 1
        elif decoded == 39:
            tape[d] = cell(d) // 3 + (cell(d) % 3) * K19_THIRD
            a = tape[d]
        elif decoded == 40:
            d = cell(d)
        elif decoded == 62:
            tape[d] = crazy_k(a, cell(d), 19)
            a = tape[d]
        elif decoded == 81:
            events.append({"step": step, "c": c, "d": d, "a_before": a_before,
                           "decoded_op": decoded, "executed_op": executed,
                           "source_char": char_before, "cell_before": cell_before,
                           "mem_d_before": mem_d_before, "mem_d_after": cell(d),
                           "a_after": a, "output": None, "halted": True})
            return events
        event = {"step": step, "c": c, "d": d, "a_before": a_before,
                 "decoded_op": decoded, "executed_op": executed,
                 "source_char": char_before, "cell_before": cell_before,
                 "mem_d_before": mem_d_before, "mem_d_after": cell(d),
                 "a_after": a, "output": a % 256 if decoded == 5 else None,
                 "halted": False}
        if 33 <= cell(c) <= 126:
            tape[c] = malbolge._ENCRYPT[cell(c)]
            event["encrypted_to"] = chr(tape[c])
        c = (c + 1) % K19_END
        d = (d + 1) % K19_END
        events.append(event)
    return events


def first_divergence(plan: list[int], stdin_data: bytes) -> dict:
    classic_source = assemble_classic(plan)
    k19_source = unshackled_codec.assemble19(plan)
    classic_decoded = [decode_classic(ch, i) for i, ch in enumerate(classic_source)]
    k19_decoded = [unshackled_codec.decode(ch, i) for i, ch in enumerate(k19_source)]
    encoding_intact = k19_decoded == plan and classic_decoded == plan

    classic_trace = trace_classic(classic_source, stdin_data)
    k19_trace = trace_k19(k19_source, stdin_data)

    divergence = None
    for left, right in zip(classic_trace, k19_trace):
        if left["decoded_op"] != right["decoded_op"]:
            divergence = {"step": left["step"], "kind": "ENCODING",
                          "classic": left, "k19": right}
            break
        for field in ("mem_d_before", "mem_d_after", "a_after", "output"):
            if left[field] != right[field]:
                divergence = {"step": left["step"], "kind": "SEMANTIC",
                              "field": field,
                              "classic": left, "k19": right}
                break
        if divergence:
            break

    return {
        "plan": plan,
        "plan_names": [NAMES[op] for op in plan],
        "stdin_hex": stdin_data.hex(),
        "classic_source": classic_source,
        "k19_source": k19_source,
        "sources_identical": classic_source == k19_source,
        "encoding_intact": encoding_intact,
        "classic_trace": classic_trace,
        "k19_trace": k19_trace,
        "first_divergence": divergence,
    }


def zig_crosscheck(source: str, stdin_hex: str, exe: Path) -> dict:
    """Run the real 3^19 Zig runtime and return its final observable state."""
    import subprocess
    cmd = [str(exe), "19", source.encode("latin-1").hex(), stdin_hex or "00",
           "100", "0", "117", "140"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "NOT_RUN", "reason": str(exc)}
    line = next((ln for ln in proc.stderr.splitlines() if ln.startswith("RESULT ")), "")
    fields = dict(token.split("=", 1) for token in line.split() if "=" in token)
    return {"status": "RUN", "command": " ".join(cmd),
            "vm_status": fields.get("status"), "steps": fields.get("steps"),
            "a": int(fields.get("a", "-1")), "out_hex": fields.get("out_hex")}


def main() -> int:
    with_zig = "--with-zig" in sys.argv
    plans = [
        ("echo_control", [23, 5, 81], b"H"),
        ("literal_opr", [62, 5, 81], b""),
        ("literal_rot", [39, 5, 81], b""),
    ]
    cases = {name: first_divergence(plan, stdin) for name, plan, stdin in plans}

    # Cross-check the Classic side against the untouched reference runner.
    ref = malbolge.run(assemble_classic([62, 5, 81]))
    ref_check = {"reference_run": {"status": ref[0], "steps": ref[1],
                                   "stdout_hex": ref[2].hex()},
                 "probe_trace_output": [
                     e["output"] for e in cases["literal_opr"]["classic_trace"]
                     if e["output"] is not None]}

    # Cross-check the k19 lazy trace against the real 3^19 Zig runtime.
    zig_check: dict = {"status": "NOT_RUN"}
    if with_zig:
        exe = HERE / "intermediate_vm_runner.exe"
        results = []
        for name in ("echo_control", "literal_opr"):
            case = cases[name]
            run = zig_crosscheck(case["k19_source"], case["stdin_hex"], exe)
            lazy = case["k19_trace"]
            lazy_out = [e["output"] for e in lazy if e["output"] is not None]
            lazy_a = lazy[-1]["a_after"] if lazy else None
            ok = (run.get("vm_status") == "HALTED"
                  and run.get("a") == lazy_a
                  and bytes(lazy_out).hex() == (run.get("out_hex") or "")
                  and int(run.get("steps", -1)) == len(lazy))
            results.append({"case": name, "zig": run, "lazy_out_hex": bytes(lazy_out).hex(),
                            "lazy_final_a": lazy_a, "match": ok})
        zig_check = {"status": "RUN", "results": results,
                     "all_match": all(r["match"] for r in results)}

    evidence = {
        "format": "malbolge-quijote-first-divergence/1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "question": "Classic literal flow under Malbolge-19: first divergence encoding or semantic?",
        "offsets_k19": list(unshackled_codec.OFFSETS),
        "cases": cases,
        "classic_reference_crosscheck": ref_check,
        "k19_zig_runner_crosscheck": zig_check,
    }
    case_divergences = {name: (c["first_divergence"] or {}).get("kind")
                        for name, c in cases.items()}
    all_encoding_intact = all(c["encoding_intact"] for c in cases.values())
    semantic_divergence_seen = any(kind == "SEMANTIC" for kind in case_divergences.values())
    evidence["claims"] = {
        "QUIJOTE_ENCODING_INTACT_ON_CASES": all_encoding_intact,
        "FIRST_DIVERGENCE_KINDS": case_divergences,
        "QUIJOTE_OPCODE_PLAN": (
            "DEMONSTRATED_SEMANTIC_DIVERGENCE_NOT_ENCODING"
            if all_encoding_intact and semantic_divergence_seen
            else "NOT_DEMONSTRATED"
        ),
    }
    out = HERE / "evidence" / "quijote_first_divergence_20260912.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    for name, case in cases.items():
        div = case["first_divergence"]
        div_desc = "none" if div is None else f"step={div['step']} kind={div['kind']} field={div.get('field')}"
        print(f"CASE {name}: encoding_intact={case['encoding_intact']} "
              f"sources_identical={case['sources_identical']} divergence={div_desc}")
    print(f"CLASSIC_REFERENCE_CROSSCHECK={'PASS' if ref[0] == 'HALTED' else 'FAIL'}")
    if zig_check["status"] == "RUN":
        print(f"K19_ZIG_RUNNER_CROSSCHECK={'PASS' if zig_check['all_match'] else 'FAIL'} "
              f"({len(zig_check['results'])} cases)")
    print("QUIJOTE_OPCODE_PLAN=" + evidence["claims"]["QUIJOTE_OPCODE_PLAN"])
    print(f"evidence={out}")
    return 0 if evidence["claims"]["QUIJOTE_OPCODE_PLAN"] != "NOT_DEMONSTRATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
