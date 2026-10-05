# Natural all-region witnesses, E11-E18

Date: 2026-10-02. Linux, Zig 0.16.0, Python 3.12.3.

## Question

The frozen E15 witness visits regions 0, 1 and 2 only at E15. Does an independently chosen natural-start program do so at every width E11-E18?

## Exploration (not confirmatory)

Two bounded searches, both from a=c=d=0, empty stdin, max_steps=512.

1. Same family as the E15 search: prefix [MOVD, JMP] plus a length-3 suffix, 512 candidates, native rebuild of intermediate_vm_runner.zig. Every candidate at E11-E14 and E16-E17 visited only regions 0 and 1. That family is a negative for those widths; it is not the witness used below.

2. Low-prefix filter (fill before execute, first 256 cells) over opcodes {4,23,39,40,62,68,81}, length 6 then length 7. A candidate was frozen only if the runner reported visited=7 and HALTED. The first such plan per width was written to region_witness_preregistration.json before the confirmatory replay.

## Confirmatory command

```text
python3 region_witness_confirm.py
```

Exit status: 0. Raw result: evidence/region_witness_report.json.

| k | source | steps | entry steps 0/1/2 | offset1 | offset2 |
|---:|---|---:|---|---|---|
| 11 | `ut&%##` | 13 | 1/10/8 | 17->18 | 32->33 |
| 12 | `u'&$q#\` | 94 | 1/27/8 | 7->8 | 80->81 |
| 13 | `u'&;$]"` | 80 | 1/17/7 | 0->1 | 71->72 |
| 14 | `u'&;$]"` | 18 | 1/17/7 | 18->19 | 60->61 |
| 15 | `u'&$$"o` | 264 | 1/33/23 | 78->79 | 55->56 |
| 16 | `u'&;$]\` | 291 | 1/85/7 | 10->11 | 18->19 |
| 17 | `ut&rq98` | 193 | 1/150/83 | 64->65 | 71->72 |
| 18 | `u'&;^?!` | 395 | 1/59/21 | 66->67 | 17->18 |

Every replay matched the frozen steps, entry opcodes, final a/c/d and both full-tape SHA-256 values. Both offset controls changed the corresponding entry opcode by 1.

## Claims

| Claim | Status |
|---|---|
| Natural visit of regions 0, 1 and 2 at each of E11-E18 | DEMONSTRATED |
| Offset 1 participates in dispatch at each width | DEMONSTRATED |
| Offset 2 participates in dispatch at each width | DEMONSTRATED |
| Replay-stable full-tape hashes | DEMONSTRATED |
| NATURAL_ALL_REGION_E11_TO_E18 | DEMONSTRATED |
| Canonical semantics for k != 10 | NOT_DEMONSTRATED |
| These witnesses are unique or minimal | NOT_CLAIMED |

The historical E15 source remains a separate demonstrated witness. This selection does not replace it.
