# Evidence reference supersedence ledger — 2026-10-05

**Repo:** `DannyBaanks/MALBOLGE` · **baseline:** `3dac801278fa`

**Scope.** All path→sha256 references recorded in the `files` / `sha256`
contexts of `evidence/**/*.json` — flat `{path: sha256}` and nested
`{path: {sha256: …}}` forms — 288 total. 277 close directly against the
current tree. The 11 that do not were investigated against every revision of
each path (raw / LF / CRLF variants) and are reconciled here. **No original
evidence file was modified** — this ledger is the correction record
(append-only discipline). One `supersedes` note
(`e11_e14_vm_hashes.json → e15_vm_probe.py`) is historical by design and not
counted as a manifest reference. Embedded per-row artifact hashes (e.g.
`rows[*].hell_sha256`) are data, not path references, and are out of scope.

## Classes

| class | meaning | verification predicate |
|---|---|---|
| `eol-artifact` | recorded on a Windows checkout; current bytes differ only in line endings | `sha256(crlf(current)) == recorded` |
| `superseded-by-commit` | recorded bytes are a pre-Linux-port (or pre-generalization) revision | `sha256(blob@rev[,crlf]) == recorded` |
| `artifact-excluded` | build artifact (`.exe`) excluded by `.gitignore` on both sides; regenerable | `sha256(local artifact) == recorded` (when present) |
| `not-recoverable` | recorded revision was never committed; documented gap | none — preserved as-is |

## Entries

| # | evidence file | entry | class | recorded | current |
|---|---|---|---|---|---|
| 1 | `evidence/direct_encoding_20260912.hashes.json` | `quijote_divergence.py` | `superseded-by-commit` | `ccf86ed5ba66…` | `6508bcb1900f…` |
| 2 | `evidence/direct_encoding_20260912.hashes.json` | `evidence/quijote_first_divergence_20260912.json` | `eol-artifact` | `b0d51afcd497…` | `debbedcc7a30…` |
| 3 | `evidence/e15_region_hashes.json` | `evidence/e15_region_report.json` | `eol-artifact` | `832d958f098f…` | `e61c1e139be9…` |
| 4 | `evidence/e15_vm_hashes.json` | `evidence/e15_vm_report.json` | `eol-artifact` | `71b841de0829…` | `a7a722ab141f…` |
| 5 | `evidence/e15_vm_hashes.json` | `evidence/E15_VM_EXPERIMENT.md` | `not-recoverable` | `5510fc18fa77…` | `7a162ff4a057…` |
| 6 | `evidence/intermediate_vm_sweep_hashes.json` | `intermediate_vm_runner.exe` | `artifact-excluded` | `006b585706d4…` | `not in tree` |
| 7 | `evidence/intermediate_vm_sweep_hashes.json` | `run_intermediate_sweep.py` | `superseded-by-commit` | `e92cfd155cdf…` | `76799009320d…` |
| 8 | `evidence/intermediate_vm_sweep_hashes.json` | `GUIA_BARRIDO_E11_E18.md` | `superseded-by-commit` | `4e6b015ebe4a…` | `00a080806a5b…` |
| 9 | `evidence/intermediate_vm_sweep_hashes.json` | `evidence/intermediate_vm_sweep_preregistration_addendum.json` | `eol-artifact` | `8f291e3b2bad…` | `eb0aaa03e249…` |
| 10 | `evidence/intermediate_vm_sweep_hashes.json` | `evidence/intermediate_vm_sweep_report.json` | `eol-artifact` | `e813ee861ff0…` | `d71b12894d9e…` |
| 11 | `evidence/e15_vm_hashes.json` | `e15_vm_probe.py` | `superseded-by-commit` | `ca31bf1c398d…` | `d3034341ad41…` |

## Reproduce

```bash
python3 verify_evidence_refs.py        # exit 0 = every reference closed or classified
python3 verify_evidence_refs.py -v     # one line per reference
```

Manual spot checks:

```bash
git show 82076be:quijote_divergence.py | sha256sum      # superseded revision (#1)
git show 82076be:run_intermediate_sweep.py | sha256sum  # superseded revision (#7)
git show c6eae9f:e15_vm_probe.py | sha256sum            # superseded revision (#11)
```

CRLF predicates and the artifact check are automated in the verifier.

## The not-recoverable gap (#5)

`evidence/E15_VM_EXPERIMENT.md` was recorded at
`5510fc18fa771de785819324f25293164f501f33ff1a6bbb430ca28d53e187ec`; no revision
of the path — including initial commit `82076be` — matches in raw, LF or CRLF
form. The recorded bytes are presumed to be a Windows-era working copy that was
never committed. Current bytes hash `7a162ff4…`. This gap is preserved: it is
the honest record that the exact revision is gone.
