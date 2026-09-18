import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import quine_harness


class QuineHarnessTests(unittest.TestCase):
    def test_report_rejects_non_quine_without_running_a_large_program(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mal"
            source.write_text("ubO", encoding="ascii")
            report = quine_harness.reproduce(source, max_steps=1)
        self.assertEqual(report["format"], quine_harness.FORMAT)
        self.assertEqual(report["status"], "OUT_OF_FUEL")
        self.assertFalse(report["quine"])
        self.assertEqual(report["equivalence"], "MISMATCH")

    def test_default_budget_covers_recorded_lutter_witness(self):
        self.assertEqual(quine_harness.DEFAULT_MAX_STEPS, 70_000_000)


if __name__ == "__main__":
    unittest.main()
