import unittest
from dataclasses import replace
from datetime import date

from watt.finance import Adjustment, Contract, Month, analyze, classify, margin
from watt.synthetic import DECEMBER, NOVEMBER, make_demo


def d(month, year=2025):
    return date(year, month, 1)


class MarginTests(unittest.TestCase):
    def test_credits_and_all_costs_are_subtracted_once(self):
        row = Month("c", d(12), 30, 500, 80, energy_revenue=10000,
                    fixed_fees=500, bill_credits=100, export_credits=300,
                    wholesale=4000, ancillary=200, transmission=800, other=100)
        self.assertEqual(margin(row), 5000)

    def test_posted_prior_period_adjustments_are_signed_and_normalized(self):
        row = Month("c", d(12), 31, 500, 0, energy_revenue=5000,
                    adjustments=(Adjustment("charge", d(11), 900),
                                 Adjustment("refund", d(11), -300),
                                 Adjustment("current", d(12), 200)))
        self.assertEqual(margin(row), 4200)
        self.assertEqual(margin(row, normalized=True), 4800)
        report = analyze([Contract("c", "customer", True, d(11), d(12))],
                         [Month("c", d(11), 30, 500, 0, energy_revenue=5000), row], d(12))
        self.assertEqual(report.months[d(11)].portfolio.reported, 5000)
        self.assertEqual(report.contracts["c"].normalized, 9800)

    def test_contract_coverage_separates_missing_and_future_months(self):
        active = Contract("active", "a", True, d(1), d(4))
        done = Contract("done", "b", True, d(1), d(2))
        rows = [Month("active", d(1), 31, 100, 0, energy_revenue=80),
                Month("active", d(3), 31, 100, 0, energy_revenue=120),
                Month("active", d(4), 30, 100, 0, energy_revenue=900),
                Month("done", d(1), 31, 100, 0, energy_revenue=70),
                Month("done", d(2), 28, 100, 0, energy_revenue=30)]
        result = analyze([active, done], rows, d(3))
        self.assertEqual(result.contracts["active"].reported, 200)
        self.assertEqual(result.contracts["active"].missing_months, (d(2),))
        self.assertIsNone(result.contracts["active"].completed_margin)
        self.assertEqual(result.contracts["done"].completed_margin, 100)
        self.assertNotIn(d(4), result.months)

    def test_duplicate_month_or_adjustment_is_rejected(self):
        c = Contract("c", "a", True, d(1), d(2))
        row = Month("c", d(1), 31, 50, 0, adjustments=(Adjustment("a", d(1), 10),))
        with self.assertRaises(ValueError):
            analyze([c], [row, row], d(2))
        with self.assertRaises(ValueError):
            analyze([c], [row, replace(row, month=d(2), billed_days=28)], d(2))

    def test_winter_profiles_require_history_and_keep_solar_precedence(self):
        contracts = [Contract(name, name, solar, d(12, 2024), d(12))
                     for name, solar in [("high", False), ("low", False),
                                         ("solar", True), ("missing", False), ("unknown", None)]]
        rows = [Month(name, month, days, use * days, 0)
                for name, use in [("high", 30), ("low", 10), ("solar", 50)]
                for month, days in [(d(12, 2024), 31), (d(1), 31), (d(2), 28)]]
        rows += [Month("missing", d(12), 31, 400, 0, energy_revenue=170)]
        groups = classify(contracts, rows, d(12))
        self.assertEqual(groups, {"high": "high_winter", "low": "low_winter",
                                  "solar": "solar", "missing": "unclassified",
                                  "unknown": "unclassified"})
        self.assertEqual(classify(contracts, rows, d(1))["high"], "unclassified")
        dec = analyze(contracts, rows, d(12)).months[d(12)]
        self.assertEqual(dec.groups["unclassified"].reported, 170)
        self.assertEqual(dec.portfolio.reported, 170)

    def test_future_solar_contract_does_not_change_historical_profile_cutoff(self):
        contracts = [Contract(name, name, False, d(12, 2024), d(12))
                     for name in ("low", "mid", "high")]
        rows = [Month(name, month, days, rate * days, 0)
                for name, rate in [("low", 10), ("mid", 20), ("high", 30)]
                for month, days in [(d(12, 2024), 31), (d(1), 31), (d(2), 28)]]
        future = Contract("future", "low", True, d(1, 2026), d(12, 2026))
        self.assertEqual(classify([*contracts, future], rows, d(12))["mid"], "high_winter")


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = make_demo()
        cls.report = analyze(cls.demo.contracts, cls.demo.months, DECEMBER)

    def test_demo_size_and_golden_changes(self):
        self.assertEqual(len({c.customer_id for c in self.demo.contracts}), 10000)
        self.assertEqual(sum(c.solar is True for c in self.demo.contracts), 200)
        self.assertEqual(len(self.demo.months), 240000)
        nov, dec = (self.report.months[m] for m in (NOVEMBER, DECEMBER))
        self.assertEqual(dec.portfolio.reported - nov.portfolio.reported, -100000)
        self.assertEqual({group: dec.groups[group].reported - nov.groups[group].reported
                          for group in dec.groups},
                         {"high_winter": 220000, "low_winter": -80000, "solar": -240000})
        self.assertEqual(dec.groups["solar"].normalized - dec.groups["solar"].reported, 90000)
        earlier = analyze(self.demo.contracts, self.demo.months, NOVEMBER)
        self.assertNotIn(DECEMBER, earlier.months)
        self.assertEqual(earlier.months[NOVEMBER], nov)

    def test_every_month_group_contract_and_portfolio_reconcile(self):
        for mode in ("reported", "normalized"):
            monthly_total = 0
            for month in self.report.months.values():
                amount = getattr(month.portfolio, mode)
                self.assertEqual(sum(getattr(group, mode) for group in month.groups.values()), amount)
                monthly_total += amount
            self.assertEqual(sum(getattr(c, mode) for c in self.report.contracts.values()), monthly_total)
            for group in ("solar", "high_winter", "low_winter"):
                contract_amount = sum(getattr(c, mode) for key, c in self.report.contracts.items()
                                      if self.report.groups[key] == group)
                monthly_amount = sum(getattr(month.groups[group], mode)
                                     for month in self.report.months.values())
                self.assertEqual(contract_amount, monthly_amount)
