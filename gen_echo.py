"""Generate a straight-line echo program: [IN, OUT] x n, then HALT.

Every cell is chosen so that the public decode rule `(cell + pos) % 94`
yields the intended operation at that position (23 = in, 5 = out, 81 = halt).
Because the program never jumps and never revisits a cell, this is all that
is needed; the choice is deterministic (lowest printable char that works).
"""

OP_OUT = 5
OP_IN = 23
OP_HALT = 81


def _char_for(op: int, pos: int) -> str:
    for code in range(33, 127):
        if (code + pos) % 94 == op:
            return chr(code)
    raise ValueError(f"no printable char yields op {op} at position {pos}")


def gen_echo(n: int) -> str:
    """Program that reads n bytes and writes them straight back."""
    src = []
    for i in range(n):
        src.append(_char_for(OP_IN, 2 * i))
        src.append(_char_for(OP_OUT, 2 * i + 1))
    src.append(_char_for(OP_HALT, 2 * n))
    return "".join(src)


if __name__ == "__main__":
    import sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 13
    sys.stdout.write(gen_echo(n))
