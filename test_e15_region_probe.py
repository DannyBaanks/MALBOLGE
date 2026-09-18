import json
import unittest

import e15_region_probe as probe


class E15RegionProbeTests(unittest.TestCase):
    def test_recorded_target_meets_frozen_criteria(self):
        prereg = json.loads(probe.PREREG.read_text(encoding="utf-8"))
        report = json.loads(probe.REPORT.read_text(encoding="utf-8"))
        self.assertTrue(probe.target_passes(report["target"], prereg["success_criterion"]))

    def test_controls_and_claim_are_recorded_as_pass(self):
        report = json.loads(probe.REPORT.read_text(encoding="utf-8"))
        self.assertTrue(report["region1_control_pass"])
        self.assertTrue(report["region2_control_pass"])
        self.assertEqual(
            report["claim"],
            "NATURAL_RUNTIME_DISPATCH_E15_REGIONS_0_1_2=DEMONSTRATED",
        )


if __name__ == "__main__":
    unittest.main()
