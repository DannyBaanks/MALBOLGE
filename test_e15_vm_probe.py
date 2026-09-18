import unittest

import malbolge
import e15_vm_probe as probe


class E15VmProbeTests(unittest.TestCase):
    def test_chunked_crazy_matches_classic_for_e10(self):
        vectors = ((0, 0), (1, 2), (42, 59048), (12345, 54321))
        for a, b in vectors:
            self.assertEqual(probe.crazy_width(a, b, 10), malbolge.crazy(a, b))

    def test_negative_offset_rejects_source_before_fill(self):
        result = probe.execute("ubO", 15, (1, 105, 116), b"Z", 10)
        self.assertEqual(result["status"], "INVALID")
        self.assertFalse(result["full_crazy_fill_completed"])


if __name__ == "__main__":
    unittest.main()
