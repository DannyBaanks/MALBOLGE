import json
import unittest

import binaries
import v4

MANIFEST = v4.HERE / "fixtures" / "fullstate_demo.json"


@unittest.skipIf(binaries.find_epoch() is None, "epoch binary not built (python3 build_native.py)")
class FullStateTests(unittest.TestCase):
    def test_full_state_chain(self):
        manifest = v4.build(3)
        self.assertEqual([link["state_after_hex"] for link in manifest["links"]],
                         ["000100000000000000", "000200000000000000", "000300000000000000"])
        self.assertEqual(v4.verify(manifest), [])

    def test_sealed_manifest_replays(self):
        self.assertEqual(v4.verify(json.loads(MANIFEST.read_text(encoding="utf-8"))), [])

    def test_tampered_state_is_rejected(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["links"][1]["state_after_hex"] = "ff" + manifest["links"][1]["state_after_hex"][2:]
        self.assertTrue(v4.verify(manifest))


if __name__ == "__main__":
    unittest.main()
