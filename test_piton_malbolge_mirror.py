import unittest

import binaries
from piton_malbolge_mirror import CORPUS, run_case


@unittest.skipIf(binaries.find_piton() is None, "piton not on PATH")
class PitonMalbolgeMirrorTests(unittest.TestCase):
    def test_byte_exact_corpus(self):
        for payload in CORPUS:
            with self.subTest(size=len(payload)):
                result = run_case(payload)
                self.assertTrue(result["codec_plan_matches"])
                self.assertTrue(result["deterministic_replay"])
                self.assertTrue(result["byte_exact_parity"])
                self.assertTrue(result["pass"])


if __name__ == "__main__":
    unittest.main()
