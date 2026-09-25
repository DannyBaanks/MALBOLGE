import json
import unittest

import binaries
import v2

MANIFEST = v2.HERE / "fixtures" / "v2_demo.json"


@unittest.skipIf(binaries.find_epoch() is None, "epoch binary not built (python3 build_native.py)")
class V2Tests(unittest.TestCase):
    def test_plus_and_minus_wrap_mod_256(self):
        self.assertEqual(v2.run_epoch(v2.EPOCHS["+"], b"\xff")[2], b"\x00")
        self.assertEqual(v2.run_epoch(v2.EPOCHS["-"], b"\x00")[2], b"\xff")

    def test_register_program(self):
        manifest = v2.build_v2("+++-")
        self.assertEqual(manifest["register_final_hex"], "32")
        self.assertTrue(all(link["status"] == "HALTED" for link in manifest["links"]))
        self.assertEqual(v2.verify(manifest), [])

    def test_sealed_manifest_replays(self):
        self.assertEqual(v2.verify(json.loads(MANIFEST.read_text(encoding="utf-8"))), [])

    def test_tampered_register_is_rejected(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["links"][0]["register_after"] = "30"
        self.assertTrue(v2.verify(manifest))


if __name__ == "__main__":
    unittest.main()
