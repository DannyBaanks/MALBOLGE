# Intermediate full-VM sweep E11–E18

Date: 2026-09-12. Windows 11, zig 0.16.0, Python 3.10/3.12, little-endian.

## Question

Does the frozen width-k parametric profile execute on a fully materialized
`3^k`-cell tape with complete crazy-fill at every width from E11 to E18 — and do
two independent implementations of that profile agree on what happens?

## What was broken before this run

The sweep had been designed and pre-registered
(`intermediate_vm_sweep_preregistration.json`) but never produced evidence.
Its orchestrator did not implement the frozen gates, and would have reported
failure at every width regardless of the truth:

| defect | effect |
|---|---|
| parsed `RESULT` from stdout; the runner prints it on stderr | every field missing |
| required `fill is True`; parsing yields the string `"true"` | every gate fails |
| required `visited == 0b111` for the TOY | a region-0 toy can never pass; not in the preregistration |
| ran offset controls for the TOY | not registered |
| invoked the extensionless runner path | not resolved by Windows `CreateProcess` |

The last edit to `intermediate_vm_runner.zig` (accept empty stdin) had also not
been compiled: the binary predated the source.

These were corrected, and one gate added, in
`intermediate_vm_sweep_preregistration_addendum.json`, frozen **before** the
first sweep execution (SHA-256 `8f291e3b2badbe7173ae95c113056b457c8178c36a281c5b0637833f7c40d7e6`).
No preregistered gate was changed.

## Instruments

**`intermediate_vm_runner.exe`** (Zig, ReleaseSafe). VM semantics unchanged.
Added: full `out_hex`, `initial_tape_sha256` and `final_tape_sha256` over the
raw `u32` tape, an `OUTPUT_CAP` status instead of a 512-byte buffer overflow, a
minimum program length of 2, empty stdin, and an `@path` source form (argv is
capped near 32K characters on Windows, so programs above ~16 KB could not be
loaded at all).

**`reference_width_vm.py`** (Python, new). Written from the preregistration's
`vm_profile`, not from the Zig source. It computes crazy through a different
route for the top `k mod 5` trits: a second table built trit by trit for
exactly that many trits, where the runner reuses the 5-trit table and reduces
modulo `3^take`.

Independence is limited to: different language, different author, different
top-chunk algorithm. Both read the same written profile.

## Anchors (run before the sweep)

| anchor | result |
|---|---|
| Zig vs frozen Python evidence (E10 toy, E15 toy, E15 witness + both controls) | **5/5 identical**, including full-tape hashes of 14,348,907 cells |
| Zig E10 vs Classic oracle `malbolge.py` on fixtures | **6/6**: 3 executed identically (hello 40 steps, echo12 25, classic_challenge 7), 3 rejected at load by both |
| Zig E10, Lutter quine (59,032 cells) | output **byte-identical** to the 59,852-byte source file, `HALTED` at 69,547,437 steps |
| reference crazy vs trit-by-trit definition | **27,036 pairs**, k = 10..18, 0 failures |
| reference E10 vs Classic oracle | 3/3 |
| reference E15 vs frozen Python evidence | 4/4, including full-tape hashes |

## Command

```powershell
py run_intermediate_sweep.py
```

Raw progress output:

```text
E11: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=223 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 0.2s)
E12: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=41 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 0.4s)
E13: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=407 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 1.2s)
E14: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=101 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 5.3s)
E15: toy=PASS witness=PASS visited=[0, 1, 2] status=HALTED steps=139 all_region=DEMONSTRATED parity=PASS (4 runs, 34.5s)
E16: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=58 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 69.1s)
E17: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=319 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 243.1s)
E18: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=189 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 560.6s)
```

Exit status `0`. Complete raw results: `intermediate_vm_sweep_report.json`.

## Results

### The toy is width-blind

| k | cells | steps | stdout | a, c, d | initial tape SHA-256 |
|---:|---:|---:|---|---|---|
| 11 | 177,147 | 3 | `5a` | 90, 2, 2 | `c4687c7494e07deb…` |
| 12 | 531,441 | 3 | `5a` | 90, 2, 2 | `8eee3d197742c791…` |
| 13 | 1,594,323 | 3 | `5a` | 90, 2, 2 | `d1e7fd076f5bc7cd…` |
| 14 | 4,782,969 | 3 | `5a` | 90, 2, 2 | `e83c39c1f5213f4f…` |
| 15 | 14,348,907 | 3 | `5a` | 90, 2, 2 | `64dddb6a3ad30122…` |
| 16 | 43,046,721 | 3 | `5a` | 90, 2, 2 | `82b95118549644ee…` |
| 17 | 129,140,163 | 3 | `5a` | 90, 2, 2 | `5500466491759463…` |
| 18 | 387,420,489 | 3 | `5a` | 90, 2, 2 | `ce3f6dbb36720348…` |

Eight distinct tapes, **one** set of observables. `[IN, OUT, END]` keeps `c` in
cells 0–2 and never dereferences `d`, rotates, or applies crazy, so nothing it
emits can depend on k. Its gate is genuine — the tape really is materialized
and filled, and the three steps really execute — but it is evidence that
loading, filling and executing *complete* at each width, not evidence about
width-specific semantics.

### The witness is width-sensitive, and both implementations agree on it

| k | visited | steps | stdout | a | parity (10 fields) |
|---:|---|---:|---|---:|---|
| 11 | 0, 1 | 223 | `00` | 29,535 | identical |
| 12 | 0, 1 | 41 | — | 88,583 | identical |
| 13 | 0, 1 | 407 | `00` | 1,594,322 | identical |
| 14 | 0, 1 | 101 | `0000` | 1,594,342 | identical |
| 15 | **0, 1, 2** | 139 | `8dc6` | 2,391,493 | identical |
| 16 | 0, 1 | 58 | `00` | 0 | identical |
| 17 | 0, 1 | 319 | `00` | 129,140,162 | identical |
| 18 | 0, 1 | 189 | `00` | 64,570,092 | identical |

Steps, output and `a` vary with k (`a = 3^k − 1` at E13 and E17 is the width's
EOF value). The ten parity fields are status, steps, stdout, a, c, d, visited
regions, first-entry step and opcode per region, and full-tape SHA-256 before
and after execution.

At E15 both offset controls were sensitive, as in the original E15 experiment.

### The parity gate is not vacuous

- Zig E11 toy against reference E12 toy: `FAIL` (`initial_tape_sha256`,
  `final_tape_sha256`).
- Reference with a single corrupted entry in the 1-trit remainder table, E11
  witness: `FAIL` (`a`, `final_tape_sha256`).

## Claims

| Claim | Status | Evidence |
|---|---|---|
| `FULL_VM_TOY_E11` … `E18` | DEMONSTRATED | toy gate passed at every width |
| `FULL_VM_TOY_E11_TO_E18` | DEMONSTRATED | no toy failure |
| Toy observables depend on width | **NOT_DEMONSTRATED — shown not to** | one observable set across 8 widths |
| `IMPLEMENTATION_PARITY_E11` … `E18` | DEMONSTRATED | Zig == reference on all runs, 10 fields |
| `IMPLEMENTATION_PARITY_E11_TO_E18` | DEMONSTRATED | no parity failure, no resource failure |
| `NATURAL_ALL_REGION_E15` | DEMONSTRATED | witness visits 0,1,2; both controls sensitive |
| `NATURAL_ALL_REGION_E11_TO_E18` | NOT_DEMONSTRATED | the E15 witness reaches only regions 0,1 at the other seven widths |
| Offset formula falsified at E11–E14, E16–E18 | NOT_CLAIMED | per the frozen failure policy, a witness failure is not a formula failure; the witness was selected for E15 |
| Canonical semantics for k ≠ 10 | NOT_DEMONSTRATED | no external interpreter exists; parity is between two implementations of the same written profile |

## Next experiment

The preregistered follow-up from the E15 region experiment: synthesize a
natural-path witness **independently at each width**, freeze it, then run the
confirmatory gate with controls and parity. Exploration is cheap with the Zig
runner (fill time ≈ 0.1 s at E14, 2 s at E17, 11–15 s at E18). Confirmatory
parity is dominated by the reference at E18, about 5 minutes per run.
