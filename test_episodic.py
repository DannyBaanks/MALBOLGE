import json
import unittest

import episodic
import malbolge

MANIFEST = episodic.HERE / "fixtures" / "episodic_demo.json"


def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class EpisodicTests(unittest.TestCase):
    def test_hello_epoch_runs_fresh(self):
        source = (episodic.HERE / episodic.HELLO_FILE).read_text(encoding="latin-1").strip()
        self.assertEqual(malbolge.run(source, b"", episodic.FUEL),
                         ("HALTED", 40, b"Hello World!"))

    def test_sealed_manifest_replays(self):
        manifest = load()
        self.assertEqual(manifest["macro_states"], [0, 1, 2, 3])
        self.assertEqual(episodic.verify(manifest), [])

    def test_feed_gate_rejects_one_bit(self):
        link = load()["links"][0]
        payload = bytearray.fromhex(link["stdout_hex"])
        self.assertTrue(episodic.feed(link["stdout_sha256"], bytes(payload)))
        payload[0] ^= 0x01
        self.assertFalse(episodic.feed(link["stdout_sha256"], bytes(payload)))

    def test_edited_stdout_is_rejected(self):
        manifest = load()
        manifest["links"][1]["stdout_hex"] = "00" + manifest["links"][1]["stdout_hex"][2:]
        self.assertTrue(episodic.verify(manifest))

    def test_broken_frontier_is_rejected(self):
        manifest = load()
        manifest["links"][2]["macro_state_before"] = 7
        self.assertTrue(episodic.verify(manifest))


if __name__ == "__main__":
    unittest.main()
