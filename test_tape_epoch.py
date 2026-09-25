import json
import re
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

    def test_default_step_limit_matches_zig(self):
        zig = (tape_epoch.HERE / "vendor" / "malfuck" / "semantic.zig").read_text(encoding="utf-8")
        match = re.search(r"DEFAULT_MAX_STEPS: u64 = ([0-9_]+);", zig)
        self.assertEqual(int(match.group(1).replace("_", "")), tape_epoch.DEFAULT_MAX_STEPS)

    def test_legacy_manifest_step_limit(self):
        self.assertEqual(tape_epoch.manifest_max_steps({"max_steps": 7, "status": "OK", "steps": 3}), 7)
        self.assertEqual(tape_epoch.manifest_max_steps({"status": "MAX_STEPS", "steps": 500_000_000}), 500_000_000)
        self.assertEqual(tape_epoch.manifest_max_steps({"status": "OK", "steps": 3}), tape_epoch.DEFAULT_MAX_STEPS)


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

    def test_legacy_demos_replay_under_their_own_limit(self):
        # Sealed at 50M / 500M steps, before the default dropped to 5M.
        for name in ("tape_epoch_demo.json", "tape_epoch_demo_v2.json", "tape_epoch_demo_v3.json"):
            with self.subTest(name=name):
                self.assertEqual(tape_epoch.verify(load(name)), [])

    def test_tampered_savestate_is_rejected(self):
        manifest = load("tape_epoch32_demo.json")
        manifest["state_after_hex"] = "ff" + manifest["state_after_hex"][2:]
        self.assertTrue(tape_epoch.verify(manifest))


if __name__ == "__main__":
    unittest.main()
