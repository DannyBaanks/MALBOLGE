# MBIR-2L Contract v0

MBIR-2L is a local, byte-valued profile for lowering deterministic subsets of
Befunge-93 and WebAssembly. It is compatible with the existing MBIR v0 value
model; it does not modify that contract or import its implementation.

## Blob format

The blob is a sequence of variable-width instructions. Jump operands are
little-endian `u24` byte offsets and must point to instruction boundaries.

| opcode | mnemonic | operand | effect |
|---:|---|---|---|
| `00` | `HALT` | none | stop successfully |
| `01` | `PUSH_CONST` | `u8` | push a byte |
| `02` | `POP` | none | discard top byte |
| `03` | `DUP` | none | duplicate top byte |
| `06` | `ADD` | none | pop `a,b`, push `(a+b) mod 256` |
| `07` | `SUB` | none | pop `a,b`, push `(a-b) mod 256` |
| `08` | `MUL` | none | pop `a,b`, push `(a*b) mod 256` |
| `09` | `CMP_EQ` | none | push `1` if equal, else `0` |
| `0a` | `CMP_LT` | none | push `1` if `a < b`, else `0` |
| `0b` | `CMP_GT` | none | push `1` if `a > b`, else `0` |
| `0c` | `JUMP` | `u24` | set PC to target |
| `0d` | `JUMP_IF_FALSE` | `u24` | pop condition; jump when zero |
| `10` | `OUT_BYTE` | none | pop and emit low byte |
| `11` | `IN_BYTE` | none | push next input byte; EOF is `ff` |

`POP`, `DUP`, locals, calls and returns remain MBIR v0 operations but are not
required by the first two frontends. Unknown operations, truncated operands,
bad targets and stack underflow are errors. Every run has a finite step limit.

## Frontend restrictions

- Befunge: deterministic 80x25 grid, spaces, digits, `+ - *`, `!`, directions,
  `_`, `,`, `~` and `@`, only when a finite lowering exists. `?`, `p`, `g`,
  arbitrary string mode and unsupported control are rejected.
- WebAssembly: valid binary modules with the MVP magic/version and a closed
  subset of `i32.const`, `i32.add/sub/mul`, integer comparisons, nested
  `if/else/end`, byte I/O ABI and return. Imports, memory, floats, WASI,
  threads, SIMD and other instructions are rejected.
- Values crossing the shared profile boundary are bytes. Wasm `i32` values
  must be in `0..255` at constants and are reduced modulo 256 only at the
  explicitly documented arithmetic boundary.

## Result contract

Successful runs return `status=HALTED`, `steps`, `output_bytes`, final stack
and optional deterministic trace. Negative cases return a stable reason such
as `BAD_OPCODE`, `BAD_OPERAND`, `BAD_TARGET`, `STACK_UNDERFLOW`, `MAX_STEPS` or
`UNSUPPORTED`.

Parity is claimed only for declared source pairs whose MBIR blobs and final
results satisfy this contract.
