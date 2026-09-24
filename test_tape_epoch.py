import json
import unittest

import binaries
import tape_epoch

FIXTURES = tape_epoch.HERE / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TapeLayoutTests(unittest.TestCase):
    def test_generated_program_shape(self):
        self.assertEqual(tape_epoch.generated_bf(3), ",+.>,.>,.")

    def test_reference_transition_increments_cell_zero(self):
        self.assertEqual(tape_epoch.expected_transition(b"\xff\x01", 2), b"\x00\x01")
        with self.assertRaises(ValueError):
            tape_epoch.expected_transition(b"\x00", 2)


@unittest.skipIf(binaries.find_epoch() is None, "epoch binary not built (python3 build_native.py)")
class TapeEpochTests(unittest.TestCase):
    def test_sealed_demo_replays(self):
        self.assertEqual(tape_epoch.verify(load("tape_epoch32_demo.json")), [])

    def test_sweep_manifests_replay(self):
        # 1..111 bytes pass the reference; 112+ are sealed negative results.
        for size, passes in ((1, True), (32, True), (111, True), (112, False), (256, False)):
            with self.subTest(size=size):
                manifest = load(f"tape_epoch_{size}.json")
                self.assertEqual(manifest["matches_reference"], passes)
                self.assertEqual(tape_epoch.verify(manifest), [])

    def test_tampered_savestate_is_rejected(self):
        manifest = load("tape_epoch32_demo.json")
        manifest["state_after_hex"] = "ff" + manifest["state_after_hex"][2:]
        self.assertTrue(tape_epoch.verify(manifest))


if __name__ == "__main__":
    unittest.main()
