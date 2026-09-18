"""Self-contained Classic Malbolge interpreter (reference implementation).

Written from the public language description (the original 1998 interpreter's
documented behavior, as summarized in Iizawa 2005, Appendix C). No external
dependencies. One language: Classic Malbolge, 59049 cells, values are
non-negative integers below 3**10.

Notable convention: on end-of-input, `a` becomes 59048 (the behavior of the
original interpreter). Documented here because EOF handling is a known
cross-implementation divergence point; none of the bundled fixtures ever
reach EOF, so the choice cannot affect any included result.
"""

MEMORY_SIZE = 3 ** 10  # 59049 cells

_CRAZY = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)

_ORIGINAL = (
    "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
)
_TRANSLATED = (
    "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|jsb9m<."
    "TVac`uY*MK'X~xDl}REokN:#?G\"i@"
)
assert len(_ORIGINAL) == 94 and len(_TRANSLATED) == 94
_ENCRYPT = {ord(o): ord(t) for o, t in zip(_ORIGINAL, _TRANSLATED)}

EOF_VALUE = 59048

# The eight instructions of Classic Malbolge, as decoded by (cell + pos) % 94.
_VALID_OPS = frozenset({4, 5, 23, 39, 40, 62, 68, 81})


def crazy(a: int, b: int) -> int:
    """The tritwise 'crazy' operation over exactly 10 trits."""
    result = 0
    place = 1
    for _ in range(10):
        result += _CRAZY[b % 3][a % 3] * place
        a //= 3
        b //= 3
        place *= 3
    return result


def load_memory(source: str) -> list[int]:
    """Load a program: strip whitespace, then apply the classic load-time
    validation before filling every remaining cell deterministically with
    the crazy chain.

    Classic validation, both checks of the original 1998 loader:
      - every program char must be printable ASCII (33..126), and
      - at its load position it must decode to a valid instruction, i.e.
        (ord(ch) + pos) % 94 must be one of the eight ops.
    A program longer than MEMORY_SIZE cells (after whitespace stripping) is
    rejected outright, as the original does."""
    chars = [c for c in source if not c.isspace()]
    if len(chars) > MEMORY_SIZE:
        raise ValueError(
            f"program too long: {len(chars)} cells (max {MEMORY_SIZE})")
    mem = [0] * MEMORY_SIZE
    for i, ch in enumerate(chars):
        v = ord(ch)
        if not 33 <= v <= 126:
            raise ValueError(f"invalid source character {v!r} at position {i}")
        if (v + i) % 94 not in _VALID_OPS:
            raise ValueError(
                f"cell {i}: {ch!r} does not decode to a valid instruction "
                f"(({(v)} + {i}) % 94 = {(v + i) % 94})")
        mem[i] = v
    for i in range(len(chars), MEMORY_SIZE):
        mem[i] = crazy(mem[i - 1], mem[i - 2])
    return mem


def run(source: str, stdin_data: bytes = b"", max_steps: int = 2_000_000):
    """Run to halt (or until the fuel budget is spent).

    Returns (status, steps, stdout_bytes) where status is "HALTED",
    "OUT_OF_FUEL" or "INVALID".
    """
    try:
        mem = load_memory(source)
    except ValueError as exc:
        return "INVALID", 0, str(exc).encode("ascii", "replace")

    a = 0
    c = 0
    d = 0
    out = bytearray()
    stdin_pos = 0
    steps = 0

    while steps < max_steps:
        steps += 1
        op = (mem[c] + c) % 94
        if op == 4:        # jmp
            c = mem[d]
        elif op == 5:      # out
            out.append(a % 256)
        elif op == 23:     # in
            if stdin_pos < len(stdin_data):
                a = stdin_data[stdin_pos]
                stdin_pos += 1
            else:
                a = EOF_VALUE
        elif op == 39:     # rot
            v = mem[d]
            mem[d] = v // 3 + (v % 3) * (3 ** 9)
            a = mem[d]
        elif op == 40:     # movd
            d = mem[d]
        elif op == 62:     # crazy
            mem[d] = crazy(a, mem[d])
            a = mem[d]
        elif op == 68:     # nop
            pass
        elif op == 81:     # hlt
            return "HALTED", steps, bytes(out)

        # self-encryption of the cell that just executed
        if 33 <= mem[c] <= 126:
            mem[c] = _ENCRYPT[mem[c]]

        c = (c + 1) % MEMORY_SIZE
        d = (d + 1) % MEMORY_SIZE

    return "OUT_OF_FUEL", steps, bytes(out)
