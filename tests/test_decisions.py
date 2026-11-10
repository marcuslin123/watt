import unittest
from datetime import date

from pydantic import ValidationError

from watt.decisions import Scenario, calculate_scenario, follow_up, apply_resolution, Resolution


class ScenarioTests(unittest.TestCase):
    def test_displayed_increment_reconciles_after_cent_rounding(self):
        result = calculate_scenario(Scenario(customers=1, contribution_cents=1,
            baseline_bps=4900, offer_bps=5100, outreach_cents=0, incentive_cents=0))
        self.assertEqual((result["baseline_cents"], result["offer_cents"], result["incremental_cents"]), (0, 1, 1))

    def test_expected_values_and_break_even(self):
        result = calculate_scenario(Scenario(customers=60, contribution_cents=30000,
            baseline_bps=7000, offer_bps=8000, outreach_cents=300, incentive_cents=2500))
        self.assertEqual(result["baseline_cents"], 1260000)
        self.assertEqual(result["offer_cents"], 1302000)
        self.assertEqual(result["incremental_cents"], 42000)
        self.assertEqual(result["break_even_offer_bps"], 7746)

    def test_no_feasible_uplift(self):
        result = calculate_scenario(Scenario(customers=2, contribution_cents=100,
            baseline_bps=5000, offer_bps=10000, outreach_cents=100, incentive_cents=200))
        self.assertIsNone(result["break_even_offer_bps"])
        self.assertLess(result["incremental_cents"], 0)

    def test_rejects_invalid_inputs(self):
        for override in ({"offer_bps": 10001}, {"customers": 0}, {"incentive_cents": -1}):
            kwargs = dict(customers=5, contribution_cents=1000, baseline_bps=4000,
                          offer_bps=9000, outreach_cents=0, incentive_cents=0)
            with self.assertRaises(ValidationError):
                Scenario(**(kwargs | override))


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.findings = [
            {"key": "bridge", "status": "calculated", "title": "Margin", "amount_cents": -240000, "evidence": []},
            {"key": "usage", "status": "unresolved", "title": "Usage", "detail": "Unresolved", "amount_cents": -30000,
             "evidence": [{"tool": "usage", "id": "usage-drops", "count": 20,
                           "sample": ["contract-00000"]}]},
        ]

    def resolution(self, **kw):
        values = dict(contract_id="contract-00000", record_date=date(2025, 12, 15),
                      source="Synthetic service note", note="Service ended on December 15.")
        return Resolution(**(values | kw))

    def test_revision_keeps_unrelated_findings_and_preserves_uncertainty(self):
        result = apply_resolution(self.findings, date(2025, 12, 1), self.resolution(), "review-1")
        self.assertEqual(result[0], self.findings[0])
        self.assertEqual(result[1]["status"], "unresolved")
        self.assertEqual(result[1]["amount_cents"], -30000)
        self.assertEqual(result[1]["evidence"][-1]["record"]["provenance"], "analyst supplied")
        self.assertEqual(len(self.findings[1]["evidence"]), 1)
        with self.assertRaises(ValueError):
            apply_resolution(result, date(2025, 12, 1), self.resolution(), "review-2")

    def test_rejects_wrong_contract_and_later_record(self):
        for change in ({"contract_id": "contract-99999"}, {"record_date": date(2026, 1, 1)}):
            with self.assertRaises(ValueError):
                apply_resolution(self.findings, date(2025, 12, 1), self.resolution(**change), "review-1")

    def test_follow_up_is_scoped_and_does_not_invent_cause(self):
        self.assertEqual(follow_up(self.findings, "Did they move out?")["rows"][0]["status"], "unresolved")
        self.assertFalse(follow_up(self.findings, "Should we hedge next winter?")["rows"])
