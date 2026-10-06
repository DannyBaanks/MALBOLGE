# E15 full-VM execution probe

Date: 2026-09-12. Environment: Windows 11, Python 3.12.4, little-endian,
`array('I').itemsize == 4`.

## Pre-registration

Frozen before the first VM execution in `e15_vm_preregistration.json`.
SHA-256: `6e9eb2537dd163c4cbc849a739f0d60f2047a561d3e5ad80685f21e8890e0ee3`.

Null hypothesis: the frozen E19-derived formula does not yield an E15 machine
that executes `[IN, OUT, END]` with all registered output and state criteria.

Success required all of: complete `3^15`-cell crazy-fill, `HALTED`, reason
`halt_opcode`, 3 steps, stdout `5a`, and final `(a,c,d)=(90,2,2)`.

Baseline: the same parametric implementation at E10, compared with
`malbolge.py`. Negative control: change only E15 region-zero offset from 0 to
1 and require load-time rejection.

## Command and raw output

```powershell
py e15_vm_probe.py
```

```text
{"baseline_e10": {"execution_seconds": 0.00011849999987134652, "final_registers": {"a": 90, "c": 2, "d": 2}, "final_tape_sha256": "fe965367d6898f5fe25e8e204c04d3d865d8eac9302153ba4372e436bc8b283f", "full_crazy_fill_completed": true, "halt_reason": "halt_opcode", "initial_tape_sha256": "c177c59e4e6621b749b25fb9985f7c41efbd3bd62756d434bf20c8496c034a7b", "load_seconds": 0.014285500000141838, "memory_cells": 59049, "oracle": {"status": "HALTED", "stdout_hex": "5a", "steps": 3}, "status": "HALTED", "stdout_hex": "5a", "steps": 3}, "baseline_pass": true, "claim": "VM_EXECUTION_PARITY_E15=DEMONSTRATED", "environment": {"array_itemsize": 4, "byteorder": "little", "platform": "Windows-11-10.0.26200-SP0", "python": "3.12.4 (tags/v3.12.4:8e8a4ba, Jun  6 2024, 19:30:16) [MSC v.1940 64 bit (AMD64)]"}, "format": "malbolge-parametric-vm-probe/1", "negative_control_e15": {"full_crazy_fill_completed": false, "halt_reason": "invalid_opcode_24_at_0", "load_seconds": 0.006101599999965401, "status": "INVALID", "stdout_hex": "", "steps": 0}, "negative_control_pass": true, "null_hypothesis_rejected": true, "preregistration_sha256": "6e9eb2537dd163c4cbc849a739f0d60f2047a561d3e5ad80685f21e8890e0ee3", "source": "ubO", "source_hex": "75624f", "target_e15": {"execution_seconds": 0.024580799999966985, "final_registers": {"a": 90, "c": 2, "d": 2}, "final_tape_sha256": "453abfcd3e5eb2ae956c77e0b382678dd464420c472d9eec076af52496339868", "full_crazy_fill_completed": true, "halt_reason": "halt_opcode", "initial_tape_sha256": "64dddb6a3ad30122332426def7983474d528cb5e903efac17692e510546c5d84", "load_seconds": 5.201236999999992, "memory_cells": 14348907, "status": "HALTED", "stdout_hex": "5a", "steps": 3}, "target_pass": true}
```

Exit status: `0`.

Independent replay returned the same semantic fields and both full-tape hashes:

```text
{'status': 'HALTED', 'halt_reason': 'halt_opcode', 'steps': 3, 'stdout_hex': '5a', 'final_registers': {'a': 90, 'c': 2, 'd': 2}, 'full_crazy_fill_completed': True, 'memory_cells': 14348907, 'initial_tape_sha256': '64dddb6a3ad30122332426def7983474d528cb5e903efac17692e510546c5d84', 'final_tape_sha256': '453abfcd3e5eb2ae956c77e0b382678dd464420c472d9eec076af52496339868'}
```

## Claims

| Claim | Result | Evidence |
|---|---|---|
| E10 parametric baseline agrees with Classic oracle for this toy | DEMONSTRATED | Both halt in 3 steps and emit `5a` |
| Negative control is detected | DEMONSTRATED | Offset mutation produces `INVALID`, opcode 24 at position 0 |
| Full E15 crazy-fill completed | DEMONSTRATED | 14,348,907 materialized cells; initial tape hash recorded |
| E15 toy VM execution meets registered state/output gate | DEMONSTRATED | `HALTED`, 3 steps, `a=90,c=2,d=2`, stdout `5a` |
| `VM_EXECUTION_PARITY_E15` for `[IN,OUT,END]` | DEMONSTRATED | Baseline + negative control + target all pass |
| VM parity for E11-E14/E16-E18 | NOT_DEMONSTRATED | Not executed by this experiment |
| Runtime use of region-1/region-2 offsets at E15 | NOT_DEMONSTRATED | Three-instruction toy executes only in region 0 |
| General arbitrary-program or quine parity | NOT_DEMONSTRATED | Outside registered scope |

## Conclusion and next experiment

H0 is rejected for the registered E15 toy. This is real full-tape VM execution,
not codec inversion. The next falsification experiment should force the E15
instruction pointer into regions 1 and 2, so their offsets participate in
runtime dispatch rather than only boundary algebra.
