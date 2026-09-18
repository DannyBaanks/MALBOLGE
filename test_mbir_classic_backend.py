import unittest

from mbir_2l import ADD, HALT, IN_BYTE, OUT_BYTE, PUSH_CONST, encode
from mbir_classic_backend import ClassicUnsupported, lower, run


class MbirClassicBackendTests(unittest.TestCase):
    def test_byte_io_slice_lowers_and_runs(self):
        blob = encode([(IN_BYTE, None), (OUT_BYTE, None), (HALT, None)])
        self.assertEqual(lower(blob), "ubO")
        self.assertEqual(run(blob, b"Z"), ("HALTED", 3, b"Z"))

    def test_unproven_arithmetic_is_rejected(self):
        blob = encode([(PUSH_CONST, 2), (PUSH_CONST, 3), (ADD, None), (HALT, None)])
        with self.assertRaises(ClassicUnsupported):
            lower(blob)


if __name__ == "__main__":
    unittest.main()
