import unittest

import malbolge
from classic_challenge import PLAN
from classic_codec import MEMORY_SIZE, assemble, decode, disassemble, parity
from classic_encoder import OPCODES, encode


class ClassicCodecTests(unittest.TestCase):
    def test_every_opcode_at_wrap_boundaries(self):
        for position in (0, 1, 32, 33, 93, 94, MEMORY_SIZE - 1):
            for opcode in OPCODES:
                character = encode(opcode, position)[2]
                self.assertEqual(decode(character, position), opcode)

    def test_complete_program_round_trip_is_byte_exact(self):
        source = assemble(list(PLAN))
        decoded = [item.opcode for item in disassemble(source)]
        self.assertEqual(decoded, list(PLAN))
        self.assertEqual(assemble(decoded), source)

    def test_round_trip_preserves_execution(self):
        source = assemble(list(PLAN))
        rebuilt = assemble([item.opcode for item in disassemble(source)])
        self.assertEqual(malbolge.run(source, b"Z", 1000),
                         malbolge.run(rebuilt, b"Z", 1000))
        self.assertEqual(malbolge.run(rebuilt, b"Z", 1000),
                         ("HALTED", 7, b"Z"))

    def test_exhaustive_positional_parity(self):
        checked, problems = parity()
        self.assertEqual(checked, MEMORY_SIZE * len(OPCODES))
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
