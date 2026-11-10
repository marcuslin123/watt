import unittest
from watt.investigation import validated_findings


class FindingsTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {
            "bridge": {"status": "calculated", "evidence": [{"tool": "bridge", "id": "b"}]},
            "usage": {"status": "unresolved", "evidence": [{"tool": "usage", "id": "u"}]},
        }

    def test_only_returned_evidence_can_support_a_finding(self):
        with self.assertRaises(ValueError):
            validated_findings(["bridge", "usage"], self.catalog, {"bridge": {"b"}})

    def test_unknown_or_duplicate_claims_are_rejected(self):
        for keys in (["move-out"], ["bridge", "bridge"]):
            with self.assertRaises(ValueError):
                validated_findings(keys, self.catalog, {"bridge": {"b"}})

    def test_valid_findings_preserve_authoritative_status(self):
        out = validated_findings(["usage"], self.catalog, {"usage": {"u"}})
        self.assertEqual(out[0]["status"], "unresolved")
        self.assertEqual(out[0]["key"], "usage")
