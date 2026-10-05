# Readout line consolidated report (mod59049 in-language state readout)

Date: 2026-10-04. Linux (Ubuntu 24.04), Python 3.12, LMAO
(`vendor/lmao/`, C, compiled `vendor/lmao/bin/lmao`), zig (second interpreter,
`zig build-exe -O ReleaseSafe`), Classic oracle `malbolge.py`
(59,049-cell classic Malbolge, 8 ops).

## Question

Can the cascade's **own state** be read out **from inside the same Malbolge
program** (mod59049 readout, 5 cells), and what are the costs, the mechanism,
and the fundamental limits of doing so?

Sub-questions answered along the line:

1. Does a 5-cell in-language readout match an independent oracle across many
   `T`? (barrido 12/12 + powers of 9)
2. Is a second interpreter needed to trust the readout? (Zig vs Python vs LMAO)
3. Does the readout destroy the cascade state? (destructivity)
4. Can the readout be made non-destructive? (static restoration)
5. Can the cascade be read tick-by-tick (incremental)? (NOT_DEMONSTRATED —
   fundamental limit, mechanism measured)
6. What is the raw offset of the readout and where does it come from?
   (characterized empirically)

## Instruments

- **`mod59049_readout_gen.py`** (repo root; copies under
  `evidence/nondestructivo/` and `evidence/lectura_incremental/`). Generates
  HeLL/LMAO programs with 5 cascade cells (N1..N5), stop cells of length
  {2,4,5,6,9} (the only valid xlat cycles in LMAO), and a mid-wrap readout
  chain. Parameters: `verify`, `pre_v`, `v_cell`, `restore`, `restore_cell`,
  `stop_first`, `non_destructive`, `nd_cap`, `reentry`, `max_steps`, `passes`.
  Compiled with `vendor/lmao/bin/lmao -d`.
- **Oracle `malbolge.py`**: independent classic-Malbolge execution; expected
  positions computed as `((T)//9^i) mod 9`.
- **Second interpreter `intermediate_vm_runner.zig`**: full-VM Zig runner
  (natively rebuilt on Linux for this run; the repo binary is PE32+/Windows).
  sha256 of the Linux build: `101b6876e52ecdbe599b43f7b8e44ac6e7381aece308ed32b1a5d821e987554b`.
- **Regression control after every generator patch**: re-emit the 12 sweep
  `.hell` programs and compare byte-identical (sha256) against the recorded
  sweep (`mod59049_sweep.json`, base sha256 `3e5708e6fb60704f…` for the T=10
  winner).

## Final claims

| Claim | Status |
|---|---|
| `MOD59049_READOUT_INTEGRADO` — 5-cell readout matches the oracle | **DEMONSTRATED** (12/12 sweep: T = 2,4,5,6,8,10,20,45,54,81,90,180; powers of 9: T = 9, 81, 729, 6561, 59049 — the last prints `Z99999`, match=True, i.e. the oracle predicted the same non-digit character) |
| `MOD59049_SECOND_INTERPRETER` | **DEMONSTRATED** (6/6 T: identical output and step count between Python oracle and Zig runner, e.g. T=2 → `79999` at 32,249 steps in both) |
| `READOUT_IS_DESTRUCTIVE` | **DEMONSTRATED** (T=10, stops=[2,5]: cells 1-2 shift 1 position per read — true `8` → `9` after; cells 3-5 untouched; one extra call to the read cell repairs it) |
| `READOUT_NON_DESTRUCTIVE` | **DEMONSTRATED** (T=10: 5/5 cells preserved; re-read `889998` correct vs destructive `889999` wrong. Generality: T=5,6,9,10,12 with 2-cell stop structures (5/5); T=90 reproduced with 3-cell structure `[9,2,5]` in all 4 orderings (true `98899`); the 2-cell `[2,45]` structure **fails** even under an extended 144-config sweep) |
| `LECTURA_REPETIDA_SIN_REPARACION` | **DEMONSTRATED** (re-read inside the same program, without returning to the tick loop) |
| `READOUT_P1` (per-program stop order) | **DEMONSTRATED** (T=1 → `89999`, `stop_first=True`, pre=[1,0,0]) |
| `DIGIT_POSITION_3_REACHABLE` | **DEMONSTRATED** (T=12, stops=[2,6] → `68999`) |
| `LMAO_VALIDATES_LABELS_AT_COMPILE_TIME` | **DEMONSTRATED** (`Cannot find label sa1` at compile, not runtime) |
| `LMAO_FREE_SPACE_BUDGET` | **DEMONSTRATED** (~130 extra restore instructions: compiles with a stderr warning; ~165: `Free space exceeded`, nonzero rc) |
| `LECTURA_INCREMENTAL_MECHANISM` | **DEMONSTRATED** (traced: `OUT` prints the value of the data cell set by the preceding `ROT`, not a literal; between reads the code pointer `c` and data pointer `d` land in uncalibrated addresses) |
| `OFFSET_ORIGIN` | **CARACTERIZADO** (raw offset is a function of the stop-cascade *structure*, not of T or ordering; no first-principles formula without the full LMAO layout) |
| `LECTURA_INCREMENTAL` (read tick-by-tick through the loop) | **NOT_DEMONSTRATED** (fundamental limit — see below) |
| `ESCAPE_ANCLAR_D` ("pin `d` with a `movd`") | **REFUTADO** (traced `c`: the second read is *not* the readout — `OUT` at c=56-92, not c=33019) |
| `K_COPIAS_FRESCAS` ("K fresh copies of the readout") | **REFUTADO** (the cascade's pass 2 contains only 8 jmp / 2 movd vs 55 jmp / 8 movd in pass 1: the cascade is one-shot control flow and never reaches any copy) |

## Measured mechanism

- **`OUT` semantics**: in the compiled `.mb`, `OUT` prints `a % 256` where `a`
  is the value left in the data cell by the preceding `ROT` — the digit is a
  *calibrated value of a mirror cell*, not a literal of the block. The
  per-chain calibration (`pre`/`shift`) absorbs the cascade's phase.
- **Destructivity**: the simple readout consumes exactly **one position** of
  each cell it reads. Repair requires knowing the position after the read —
  which is exactly what the readout is for (circular).
- **Non-destructive readout**: emit a *static* restoration sequence in each
  block `a_kk`: `min(9-kk, nd_cap)` extra calls to the cell. With `nd_cap=1`
  (one call per block, 40 extra instructions at T=10) every cell is preserved
  and the re-read is correct. This is a layout-level decision, so it is free
  in the generator but bounded by LMAO's free-space budget.
- **Incremental readout — why it fails**: the cascade is **one-shot control
  flow**. On the second pass its code is already self-encrypted:
  pass 1 = 55 jmp / 8 movd / 5 out; pass 2 = 8 jmp / 2 movd / 8 out plus a
  soup of ~50 distinct random op codes (21 nop, 12 op71, …). The ROTs of the
  second read land at c=171-180 (vs 159-171 in the first) and the OUTs print
  uncalibrated data-cell values (`54,238,14,26,26` vs `55,56,57,57,57`).
  Neither pinning `d` nor duplicating the readout changes this: the flow of
  control (`c`) does not return to the readout region.

## OFFSET_ORIGIN (characterized, not derived)

The raw readout is off from the true state by a constant offset that depends
only on the **multiset of stop-cell lengths**:

| stops | T | raw | true | raw offset (digits) |
|---|---|---|---|---|
| `[2]`, `[4]`, `[2,5]`, `[5,2]`, `[4,5]`, `[4,4]`, `[2,4,2]`, `[4,2]`, … | 2..20 | e.g. `97999` | e.g. `88999` | `(+1,−1,0,0,0)` |
| any structure containing a 9-length stop, e.g. `[4,9]`, `[2,9]`, `[9,2]` | 18..36 | e.g. `15999` / `17999` | e.g. `95999` | `(−8,0,0,0,0)` |
| many 2-length stops, e.g. ten `[2]` | 2 | `33689` | `20000`… | spread across cells (`−4,−6,−3,−1,0`) |
| stop length 3 (`[3]`, `[3,3]`) | 3, 9 | — | — | not generated: 3 is not a valid xlat cycle |

Properties measured: **order-independent** (`[2,5]` ≡ `[5,2]`, `[4,9]` ≡
`[9,4]`… all pairs tested equal), **T-independent** within a structure,
**structure-dependent** (a 9-length stop shifts cell 1 by −8; many 2-length
stops distribute the offset across cells). The per-chain `pre`/`shift`
calibration used in the generator is exactly this offset absorbed
empirically; a first-principles formula would require LMAO's full address
layout.

## LMAO constraints (measured)

- xlat cycles accepted as stop-cell lengths: **2, 4, 5, 6, 9** (68 as
  composite). Any other length: `Forced xlat cycle doesn't exist` at compile.
- **Label validation at compile time** — forward references to non-existent
  labels fail the build, so the readout's mid-wrap chain must be label-closed.
- **Free-space budget**: ~130 extra instructions beyond the baseline compiles
  with a stderr warning (`Error: Free space exceeded (Add Malbolge com…`);
  ~165 fails with nonzero rc. The non-destructive readout (40 extra at T=10)
  sits well inside.

## Instrument self-corrections (caught by hash comparison, not by assertion)

1. **`stop_first` patch** accidentally removed the stop-cell call from chains
   2-5, silently changing the layout and breaking the base readout
   (`88999` → `68999`). Detected by comparing the re-emitted `.hell` sha256
   against the recorded sweep; base restored byte-identical and all probes
   re-run on the restored base.
2. **`reentry` parameter** appeared in the generator signature but not in the
   call site — the re-entry test was vacuous. Fixed; re-entry control
   re-measured (4 different entry labels, all fail identically → not the
   re-entry point).
3. **`passes > 1`** was dead code (`verify==0 or passes==1` short-circuited
   the branch). Fixed; the second-pass trace above is from the live path.
4. (Earlier in the line, recorded in the manifest's `self_corrections`: a
   report v1 regeneration overwrote v2 — distinguished by `format`; and the
   initial reporter dropped `compile_stderr`, which made the 0/12 runs
   illegible.)

## Honest limits

- **Incremental readout is a fundamental limit of classic Malbolge here**:
  reading the cascade K times would require a K-pass control-flow layout
  (K×T stable routing through self-encrypting code). That is a LMAO layout
  task, not a generator task. Both escape hatches (pin `d`, K fresh copies)
  are refuted by trace, so the NOT_DEMONSTRATED stands as a measured limit,
  not a missing idea.
- **Offset**: characterized, not derived. Empirical function of the stop
  structure; no closed form without the full LMAO layout.
- **Generality of the non-destructive readout**: holds for all tested 2-cell
  structures and for T=90 with a 3-cell structure; the 2-cell `[2,45]`
  structure does not calibrate even under an extended sweep — the boundary is
  on structure, not on T.

## Evidence registry

- **Manifest**: `evidence/readout_chain9_hashes.json` — append-only,
  **223 files**, one sha256 per artifact. Verified against disk on 2026-10-04:
  223/223 match, 0 missing. Manifest sha256:
  `d8882af631a9f61c6a1c5bddf4c2a4267b258354c21ca507a976feb9d4ed0aec`.
- Per-experiment directories (all inside the manifest):
  - `evidence/mod59049_readout/` — 12/12 sweep + powers of 9 (`.hell`/`.mb`/
    `.dbg` per T, `mod59049_sweep.json`, `mod59049_integration.json`)
  - `evidence/second_interpreter/` — 6/6 cross-implementation (winner T=10
    `.hell`/`.mb`, Zig vs Python report)
  - `evidence/nondestructivo/` — consumption, repair, correction,
    non-destructive confirmation, generality sweep, free-space budget
  - `evidence/destructivity/` — destructivity measurement with absolute
    controls
  - `evidence/lectura_incremental/` — ROT→OUT traces, re-entry control,
    escape/K-copies refutations, pass-2 cascade trace, offset characterization
    (by T, by structure, confirmation), T=90 non-destructive
  - `evidence/consumption_p1_p3/` — p=1 and T=12 probes
  - plus the full earlier line (readout3/4/5, xfer, xfer_u, offsets) carried
    in the same manifest.

## Reproduction pointers

- Generator: `mod59049_readout_gen.py` (root). Exposes `run_mod59049(...)` and
  the 2-chain CLI (`--cells`, `--pre`, `--shift`, `--sweep`). Compile with
  `vendor/lmao/bin/lmao -d <prog>.mb`.
- Every claimed number above is stored verbatim in the JSONs listed in the
  evidence registry; the manifest's `document` block carries the running
  claims history (append-only, including the intermediate states).
