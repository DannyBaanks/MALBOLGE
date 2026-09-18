import unittest

from mbir_classic import ClassicPlan


class MbirClassicTests(unittest.TestCase):
    def test_plan_lowers_and_runs_on_native_classic_machine(self):
        plan = ClassicPlan.parse("in,out,rot,movd,opr,nop,end")
        self.assertEqual(plan.lower(), "ub%%:?K")
        self.assertEqual(plan.run(b"Z"), ("HALTED", 7, b"Z"))

    def test_unknown_opcode_is_rejected(self):
        with self.assertRaises(ValueError):
            ClassicPlan.parse("in,99,end")


if __name__ == "__main__":
    unittest.main()
