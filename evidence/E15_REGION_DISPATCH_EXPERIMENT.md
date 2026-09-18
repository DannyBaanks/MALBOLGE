# E15 natural regional-dispatch experiment

Date: 2026-09-12.

## Prior evidence and exploratory search

The earlier full-VM toy executed only in region 0. An explicitly exploratory,
non-confirmatory search tested 128 standard-start sources with prefix
`[MOVD,JMP]` and three synthesized suffix instructions. Raw search result:

```text
candidate_count=128; region_patterns={(0,1):126,(0,1,2):2,(0,):0}
```

The first retained hit was source `(a`r:` with loaded plan
`[40,4,4,23,62]`. No register or instruction-counter state is injected.

## Pre-registration

The selected source, expected milestones, null hypothesis and two offset
controls were frozen before confirmatory execution in
`e15_region_preregistration.json`.

SHA-256:
`06cd718190aae180cc060c6333a6c7ceb9539a3dfa4b2884e822111dc653c089`.

## Confirmatory command and raw result

```powershell
py e15_region_probe.py
```

Exit status: `0`.

The complete raw JSON is preserved without abbreviation in
`e15_region_report.json`. Principal raw fields:

```text
claim=NATURAL_RUNTIME_DISPATCH_E15_REGIONS_0_1_2=DEMONSTRATED
target.status=HALTED
target.halt_reason=halt_opcode
target.steps=139
target.stdout_hex=8dc6
target.final_registers={a:2391493,c:7174468,d:142}
target.first_entries={0:{step:1,a:0,c:0,d:0,opcode:40},1:{step:3,a:0,c:7174483,d:42,opcode:61},2:{step:79,a:14348901,c:14348902,d:82,opcode:70}}
target.initial_tape_sha256=4a639c5cc5674681638de786ee0256d0151fb614e7a3613da6a64beaa0f8d804
target.final_tape_sha256=f86b2859d68b24e8297e300e3de50cf9683b99f08cdcf9dcd85ab7bb5949df32
region1_offset_control: offset 105->106, first region-1 opcode 61->62, HALTED step 19, stdout empty
region2_offset_control: offset 116->117, first region-2 opcode 70->71, HALTED step 198, stdout 8d
target_pass=true
region1_control_pass=true
region2_control_pass=true
null_hypothesis_rejected=true
```

An independent target replay reproduced steps, output, final registers, first
entries, and both full-tape hashes.

## Claims table

| Claim | Status | Evidence |
|---|---|---|
| Standard `a=c=d=0` execution naturally enters E15 regions 0, 1 and 2 | DEMONSTRATED | First entries at steps 1, 3 and 79 |
| E15 region-1 offset participates in runtime dispatch | DEMONSTRATED | `105->106` changes first opcode `61->62` and terminal behavior |
| E15 region-2 offset participates in runtime dispatch | DEMONSTRATED | `116->117` changes first opcode `70->71`, output and halt step |
| Frozen E15 execution is replay-stable | DEMONSTRATED | Full-tape hashes and semantic fields reproduced |
| `NATURAL_RUNTIME_DISPATCH_E15_REGIONS_0_1_2` | DEMONSTRATED | Target and both controls passed pre-registered gates |
| External/canonical E15 semantics | NOT_DEMONSTRATED | No independent E15 interpreter exists |
| Full-VM execution parity for every E11-E18 width | NOT_DEMONSTRATED | Only E15 was executed here |

## Conclusion and next experiment

The null hypothesis is rejected for the frozen E15 parametric profile. Unlike
the original algebraic boundary test, all three offsets now participate in a
single naturally reached VM trajectory after complete crazy-fill.

Next experiment: run the same natural-path synthesis and confirmatory gate
independently at E11, E12, E13, E14, E16, E17 and E18, preserving the first
width for which no bounded natural path is found or replay diverges.
