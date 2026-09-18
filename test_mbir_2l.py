import unittest

from mbir_2l import ADD, HALT, IN_BYTE, OUT_BYTE, PUSH_CONST, encode, run


class Mbir2LTests(unittest.TestCase):
    def test_arithmetic_and_output(self):
        blob = encode([(PUSH_CONST, 2), (PUSH_CONST, 3), (ADD, None),
                       (OUT_BYTE, None), (HALT, None)])
        result = run(blob)
        self.assertEqual(result["status"], "HALTED")
        self.assertEqual(result["output_bytes"], [5])

    def test_input_output(self):
        blob = encode([(IN_BYTE, None), (OUT_BYTE, None), (HALT, None)])
        self.assertEqual(run(blob, b"Z")["output_bytes"], [90])

    def test_underflow_and_bad_blob(self):
        self.assertEqual(run(encode([(ADD, None), (HALT, None)]))["reason"], "STACK_UNDERFLOW")
        self.assertEqual(run(bytes([PUSH_CONST]))["reason"], "BAD_OPERAND")

    def test_deterministic_trace(self):
        blob = encode([(PUSH_CONST, 7), (OUT_BYTE, None), (HALT, None)])
        self.assertEqual(run(blob, trace=True), run(blob, trace=True))


if __name__ == "__main__":
    unittest.main()
