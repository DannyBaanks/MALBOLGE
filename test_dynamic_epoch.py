import json
import unittest

import binaries
import dynamic_epoch

MANIFEST = dynamic_epoch.HERE / "fixtures" / "dynamic_onehot_demo.json"


class OneHotLayoutTests(unittest.TestCase):
    def test_onehot_round_trip(self):
        cells = bytes(range(10, 18))
        for pointer in range(dynamic_epoch.PAIRS):
            payload = dynamic_epoch.onehot(pointer, cells)
            self.assertEqual(len(payload), dynamic_epoch.SIZE)
            self.assertEqual(dynamic_epoch.unpack(payload), (pointer, cells))

    def test_bad_payloads_are_refused(self):
        with self.assertRaises(ValueError):
            dynamic_epoch.onehot(8, bytes(8))
        with self.assertRaises(ValueError):
            dynamic_epoch.unpack(bytes(dynamic_epoch.SIZE))  # no flag set

    def test_program_matches_compiled_source(self):
        self.assertEqual(dynamic_epoch.BF.read_text(encoding="ascii"), dynamic_epoch.program())


@unittest.skipIf(binaries.find_epoch() is None, "epoch binary not built (python3 build_native.py)")
class DynamicEpochTests(unittest.TestCase):
    def test_every_pointer_selects_its_cell(self):
        manifest = dynamic_epoch.build()
        self.assertTrue(all(r["matches_reference"] for r in manifest["records"]))
        self.assertEqual(dynamic_epoch.verify(manifest), [])

    def test_sealed_manifest_replays(self):
        self.assertEqual(dynamic_epoch.verify(json.loads(MANIFEST.read_text(encoding="utf-8"))), [])

    def test_tampered_payload_is_rejected(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["records"][3]["after_hex"] = "00" + manifest["records"][3]["after_hex"][2:]
        self.assertTrue(dynamic_epoch.verify(manifest))


if __name__ == "__main__":
    unittest.main()
