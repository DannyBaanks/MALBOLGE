"""Parity of crazy_width_general vs crazy_width (E5/E10/E15) and vs a
tritwise-direct reference (E11-E14, E16-E18).

Covers the 2026-10-02 generalization of e15_vm_probe.load_full/execute:
for dimensions divisible by 5 the general path must be bit-identical to the
frozen crazy_width, and elsewhere it must match direct tritwise crazy.
"""
import random
import unittest

import e15_vm_probe as probe


def tritwise_crazy_direct(a: int, b: int, dimension: int) -> int:
    # Independent reimplementation: trit-by-trit loop (no 5-trit chunks, no
    # remainder path) over the shared CRAZY constant, indexed as the probe does.
    value, place = 0, 1
    for _ in range(dimension):
        value += probe.CRAZY[b % 3][a % 3] * place
        a //= 3
        b //= 3
        place *= 3
    return value


class CrazyWidthGeneralTests(unittest.TestCase):
    def test_identical_to_frozen_for_multiples_of_five(self):
        rng = random.Random(20261002)
        cases = 0
        for dimension in (5, 10, 15):
            bound = 3 ** dimension
            for _ in range(300):
                a, b = rng.randrange(bound), rng.randrange(bound)
                self.assertEqual(probe.crazy_width_general(a, b, dimension),
                                 probe.crazy_width(a, b, dimension),
                                 f"E{dimension} a={a} b={b}")
                cases += 1
        self.assertEqual(cases, 900)

    def test_matches_tritwise_direct_for_intermediate_widths(self):
        rng = random.Random(11121314)
        cases = 0
        for dimension in (11, 12, 13, 14, 16, 17, 18):
            bound = 3 ** dimension
            for _ in range(150):
                a, b = rng.randrange(bound), rng.randrange(bound)
                self.assertEqual(probe.crazy_width_general(a, b, dimension),
                                 tritwise_crazy_direct(a, b, dimension),
                                 f"E{dimension} a={a} b={b}")
                cases += 1
        self.assertEqual(cases, 1050)

    def test_rejects_non_positive_dimension(self):
        with self.assertRaises(ValueError):
            probe.crazy_width_general(1, 2, 0)


if __name__ == "__main__":
    unittest.main()
