import unittest

from classic_encoder import encode


class ClassicEncoderTests(unittest.TestCase):
    def test_nop_examples(self):
        self.assertEqual(encode(68, 3), (65, 65, "A"))
        self.assertEqual(encode(68, 5), (63, 63, "?"))
        self.assertEqual(encode(68, 17), (51, 51, "3"))

    def test_wrap(self):
        self.assertEqual(encode(68, 36), (32, 126, "~"))
        self.assertEqual(encode(68, 37), (31, 125, "}"))
        self.assertEqual(encode(68, 68), (0, 94, "^"))

    def test_known_opcode_names_are_encodable(self):
        for opcode in (4, 5, 23, 39, 40, 62, 68, 81):
            residue, ascii_code, char = encode(opcode, 17)
            self.assertEqual(ascii_code, ord(char))
            self.assertTrue(33 <= ascii_code <= 126)


if __name__ == "__main__":
    unittest.main()
