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


class CostEffectsTests(unittest.TestCase):
    def test_volume_and_rate_reconcile_with_signed_effects(self):
        from watt.investigation import cost_effects
        self.assertEqual(cost_effects(100, 120, 800, 1080),
                         {"usage_cents": 160, "unit_cost_cents": 120, "direct_cents": 0})

    def test_zero_usage_does_not_invent_a_unit_rate(self):
        from watt.investigation import cost_effects
        self.assertEqual(cost_effects(0, 10, 50, 80),
                         {"usage_cents": 0, "unit_cost_cents": 0, "direct_cents": 30})
