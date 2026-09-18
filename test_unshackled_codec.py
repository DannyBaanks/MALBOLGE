import unittest

from classic_encoder import OPCODES
from unshackled_codec import END, OFFSETS, THIRD, assemble19, decode, decode_program, encode, verify_plan


class UnshackledCodecTests(unittest.TestCase):
    def test_offsets_are_three_region_offsets(self):
        self.assertEqual(OFFSETS[0], 0)
        self.assertEqual(len(OFFSETS), 3)

    def test_round_trip_at_region_boundaries(self):
        positions = (0, 1, THIRD - 1, THIRD, THIRD + 1,
                     2 * THIRD - 1, 2 * THIRD, END - 1)
        for position in positions:
            for opcode in OPCODES:
                self.assertEqual(decode(encode(opcode, position), position), opcode)

    def test_same_toy_in_out_end(self):
        self.assertEqual(assemble19([23, 5, 81]), "ubO")

    def test_direct_opcode_encoding_minimum(self):
        ops = [23, 5, 81]
        source = assemble19(ops)
        self.assertEqual(source, "ubO")
        self.assertEqual(decode_program(source), ops)
        self.assertTrue(verify_plan(ops))

    def test_direct_encoding_with_nonzero_start_c(self):
        ops = [4, 39, 62, 81]
        self.assertTrue(verify_plan(ops, start_c=THIRD + 7))

    def test_all_residues_all_regions_always_printable(self):
        # encode() depends on c only through (op - c - offset) % 94.
        # Checking one full 94-cycle of c in each region therefore covers
        # every position in 0..END-1 for every opcode.
        for region_index, region_start in enumerate((0, THIRD, 2 * THIRD)):
            for c in range(region_start, region_start + 94):
                for opcode in OPCODES:
                    char = encode(opcode, c)
                    self.assertTrue(33 <= ord(char) <= 126,
                                    f"non-printable at c={c} op={opcode}")
                    self.assertEqual(decode(char, c), opcode)
        self.assertEqual(tuple(OFFSETS[i] for i in range(3)), (0, OFFSETS[1], OFFSETS[2]))


if __name__ == "__main__":
    unittest.main()
