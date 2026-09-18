import unittest

from parity_mbir_2l import run_parity


class Mbir2LParityTests(unittest.TestCase):
    def test_befunge_and_wasm_converge(self):
        report = run_parity()
        self.assertEqual(report["status"], "PASS")
        case = report["cases"][0]
        self.assertTrue(case["equal"])
        self.assertEqual(case["befunge"]["output_bytes"], [5])
        self.assertEqual(case["wasm"]["output_bytes"], [5])


if __name__ == "__main__":
    unittest.main()
