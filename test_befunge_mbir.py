import unittest

from befunge_mbir import BefungeUnsupported, compile_source, run


class BefungeMbirTests(unittest.TestCase):
    def test_arithmetic_program(self):
        result = run("23+,@")
        self.assertEqual(result["status"], "HALTED")
        self.assertEqual(result["output_bytes"], [5])

    def test_byte_io(self):
        self.assertEqual(run("~,@", b"Z")["output_bytes"], [90])

    def test_not_and_unsupported_random(self):
        self.assertEqual(run("0!,@")["output_bytes"], [1])
        with self.assertRaises(BefungeUnsupported):
            compile_source("?@")

    def test_forward_horizontal_branch(self):
        result = run("0_  @")
        self.assertEqual(result["status"], "HALTED")

    def test_two_dimensional_vertical_route(self):
        result = run("23+v\n   >,@")
        self.assertEqual(result["status"], "HALTED")
        self.assertEqual(result["output_bytes"], [5])

    def test_compiled_blob_is_valid(self):
        self.assertEqual(compile_source("23+,@").hex(), "01020c06000001030c0c0000060c110000100c16000000")


if __name__ == "__main__":
    unittest.main()
