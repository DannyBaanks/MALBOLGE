import unittest

import offset_epoch_ladder as ladder
import unshackled_codec


class OffsetEpochLadderTests(unittest.TestCase):
    def test_registration_table_has_exact_requested_epochs(self):
        self.assertEqual([row["dimension"] for row in ladder.table()], list(range(11, 19)))

    def test_formula_is_invertible_at_all_boundary_positions(self):
        for dimension in ladder.EPOCHS:
            offsets = ladder.offsets_for(dimension)
            self.assertTrue(ladder.boundary_gate(dimension, offsets)["boundary_pass"])

    def test_toy_roundtrip_is_independent_per_epoch(self):
        for dimension in ladder.EPOCHS:
            self.assertTrue(ladder.run_toy(dimension, ladder.offsets_for(dimension))["roundtrip_pass"])

    def test_generalized_formula_reproduces_the_existing_e19_offsets(self):
        self.assertEqual(ladder.offsets_for(19), unshackled_codec.OFFSETS)


if __name__ == "__main__":
    unittest.main()
