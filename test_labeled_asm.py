"""Tests for labeled_asm.py (Labeled Malbolge v0).

    py -m unittest test_labeled_asm -v
"""
from __future__ import annotations

import random
import unittest
from pathlib import Path

import labeled_asm as la

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE / "examples_labeled"


def random_program(rng: random.Random) -> str:
    """Blocks visited in a random order via goto/call/ret, each statement run once."""
    n = rng.randint(2, 6)
    order = list(range(n))
    rng.shuffle(order)
    body = {b: [rng.choice(la.PLAIN) for _ in range(rng.randint(0, 3))] for b in range(n)}
    lines = []
    # entry block must be the first source block: put order[0] first
    source_order = [order[0]] + [b for b in range(n) if b != order[0]]
    use_call = n >= 3 and rng.random() < 0.5
    for b in source_order:
        lines.append(f"b{b}:")
        lines += [f"    {s}" for s in body[b]]
        pos = order.index(b)
        if use_call and pos == 0:
            lines.append(f"    call b{order[1]}")
            lines.append(f"    goto b{order[2]}" if n > 2 else "    end")
        elif use_call and pos == 1:
            lines.append("    ret")
        elif pos == n - 1:
            lines.append("    end")
        else:
            lines.append(f"    goto b{order[pos + 1]}")
    return "\n".join(lines) + "\n"


class ExamplesVerify(unittest.TestCase):
    def test_examples_pass(self):
        for name in ("call_return", "goto_chain", "two_calls"):
            with self.subTest(name=name):
                ok, lines = la.verify((EXAMPLES / f"{name}.mlab").read_text(encoding="utf-8"))
                self.assertTrue(ok, "\n".join(lines))

    def test_compile_is_deterministic(self):
        text = (EXAMPLES / "call_return.mlab").read_text(encoding="utf-8")
        self.assertEqual(la.emit(la.compile_layout(*la.parse(text))),
                         la.emit(la.compile_layout(*la.parse(text))))


class Rejections(unittest.TestCase):
    def assertRejected(self, text, fragment):
        with self.assertRaises(la.CompileError) as ctx:
            la.compile_layout(*la.parse(text))
        self.assertIn(fragment, str(ctx.exception))

    def test_loop_rejected(self):
        self.assertRejected((EXAMPLES / "rejected_loop.mlab").read_text(encoding="utf-8"), "execute twice")

    def test_ret_without_call(self):
        self.assertRejected("in\nret\n", "without a pending 'call'")

    def test_unknown_label(self):
        with self.assertRaises(la.CompileError):
            la.parse("goto nowhere\nend\n")

    def test_falls_off_end(self):
        self.assertRejected("in\nout\n", "without 'end'")

    def test_unsupported_opcode(self):
        with self.assertRaises(la.CompileError):
            la.parse("rot\nend\n")


class MutationControl(unittest.TestCase):
    def test_wrong_data_byte_breaks_path(self):
        text = (EXAMPLES / "call_return.mlab").read_text(encoding="utf-8")
        layout = la.compile_layout(*la.parse(text))
        source = la.emit(layout)
        data = [p for p, r in layout.role.items() if r.startswith("data")]
        self.assertTrue(data)
        cell = data[0]
        other = next(b for b in sorted({la.encode(op, cell)[1] for op in la.malbolge._VALID_OPS})
                     if b != layout.init[cell])
        mutated = source[:cell] + chr(other) + source[cell + 1:]
        self.assertNotEqual(la.trace(mutated, b"AB")[3], layout.executed)


class Fuzz(unittest.TestCase):
    def test_random_programs(self):
        rng = random.Random(319)
        compiled = no_layout = 0
        for i in range(60):
            text = random_program(rng)
            try:
                ok, lines = la.verify(text, seed=i)
            except la.CompileError as exc:
                self.assertIn("no layout found", str(exc), text)
                no_layout += 1
                continue
            compiled += 1
            self.assertTrue(ok, text + "\n" + "\n".join(lines))
        print(f"\nfuzz: compiled+verified={compiled} no_layout={no_layout}")
        self.assertGreater(compiled, 50)


if __name__ == "__main__":
    unittest.main()
