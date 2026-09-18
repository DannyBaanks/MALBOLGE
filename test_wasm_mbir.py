import unittest

from mbir_2l import run
from wasm_mbir import WasmUnsupported, compile_module


def wasm_const_add() -> bytes:
    # (func (export "run") (result i32) i32.const 2 i32.const 3 i32.add)
    return bytes.fromhex("0061736d010000000105016000017f030201000707010372756e00000a09010700410241036a0b")


def wasm_expression(expression: bytes) -> bytes:
    body = bytes([0]) + expression + bytes([0x0b])
    code = bytes([1, len(body)]) + body
    return (b"\0asm\1\0\0\0" + bytes([1, 5]) + bytes.fromhex("016000017f") +
            bytes([3, 2, 1, 0]) + bytes([7, 7, 1, 3]) + b"run" + bytes([0, 0]) +
            bytes([10, len(code)]) + code)


class WasmMbirTests(unittest.TestCase):
    def test_wasm_add_lowers_and_runs(self):
        blob = compile_module(wasm_const_add())
        result = run(blob)
        self.assertEqual(result["status"], "HALTED")
        self.assertEqual(result["output_bytes"], [5])

    def test_imports_are_rejected(self):
        module = wasm_const_add().replace(b"\x03\x02\x01\x00", b"\x02\x01\x00")
        with self.assertRaises(WasmUnsupported):
            compile_module(module)

    def test_if_else_lowers_both_arms(self):
        expression = bytes.fromhex("4101044041070541090b")
        self.assertEqual(run(compile_module(wasm_expression(expression)))["output_bytes"], [7])
        expression = bytes.fromhex("4100044041070541090b")
        self.assertEqual(run(compile_module(wasm_expression(expression)))["output_bytes"], [9])


if __name__ == "__main__":
    unittest.main()
