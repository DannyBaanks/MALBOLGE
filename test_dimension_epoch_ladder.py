import unittest

from dimension_epoch_ladder import DIMENSIONS, build, verify


class DimensionEpochLadderTests(unittest.TestCase):
    def test_all_dimensions_and_chain(self):
        manifest = build()
        self.assertEqual(manifest["dimensions"], list(DIMENSIONS))
        self.assertEqual(len(manifest["epochs"]), 10)
        self.assertEqual(verify(manifest), [])
        self.assertEqual(manifest["final_state_hex"], "5a")

    def test_tamper_is_rejected(self):
        manifest = build()
        manifest["epochs"][4]["state_after_hex"] = "00"
        self.assertTrue(verify(manifest))

    def test_manifest_metadata_is_explicit(self):
        manifest = build()
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["profile"], "TOY_ZERO_OFFSET")
        self.assertEqual(manifest["memory_model"], "SPARSE_TOY")
        self.assertEqual(verify(manifest), [])


if __name__ == "__main__":
    unittest.main()
