import json
import unittest

import binaries
import primitives

FIXTURES = primitives.HERE / "fixtures"


def reference_bf(source: str, data: bytes) -> bytes:
    """Plain Brainfuck interpreter used as the oracle for the epoch machine."""
    jumps = primitives.bracket_map(source)
    tape, ptr, pc, pos, out = bytearray(primitives.TAPE_SIZE), 0, 0, 0, bytearray()
    while pc < len(source):
        op = source[pc]
        if op == "+": tape[ptr] = (tape[ptr] + 1) & 0xFF
        elif op == "-": tape[ptr] = (tape[ptr] - 1) & 0xFF
        elif op == ">": ptr = (ptr + 1) & 0xFF
        elif op == "<": ptr = (ptr - 1) & 0xFF
        elif op == ".": out.append(tape[ptr])
        elif op == ",":
            tape[ptr] = data[pos] if pos < len(data) else 0
            pos += 1
        elif op == "[" and tape[ptr] == 0: pc = jumps[pc]
        elif op == "]" and tape[ptr] != 0: pc = jumps[pc]
        pc += 1
    return bytes(out)


@unittest.skipIf(binaries.find_epoch() is None, "epoch binary not built (python3 build_native.py)")
class PrimitivesTests(unittest.TestCase):
    def test_programs_match_reference_brainfuck(self):
        for source, data in (("+++.", b""), (",[.,]", b"ABC"), (">+++<.", b""), ("--.", b"")):
            with self.subTest(source=source):
                manifest = primitives.build(source, data)
                self.assertEqual(bytes.fromhex(manifest["output_hex"]), reference_bf(source, data))
                self.assertEqual(primitives.verify(manifest), [])

    def test_cat_is_eleven_epochs(self):
        manifest = primitives.build(",[.,]", b"ABC")
        self.assertEqual(len(manifest["links"]), 11)
        self.assertEqual(manifest["output_hex"], "414243")

    def test_sealed_fixtures_replay(self):
        for name in ("three.json", "cat.json", "shift.json"):
            with self.subTest(name=name):
                manifest = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
                self.assertEqual(primitives.verify(manifest), [])

    def test_tampered_byte_is_rejected(self):
        manifest = json.loads((FIXTURES / "cat.json").read_text(encoding="utf-8"))
        link = manifest["links"][0]
        link["byte_out"] = f"{int(link['byte_out'], 16) ^ 1:02x}"
        self.assertTrue(primitives.verify(manifest))


if __name__ == "__main__":
    unittest.main()
