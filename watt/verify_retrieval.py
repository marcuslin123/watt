"""Run the prepared-evidence golden cases against local PostgreSQL."""
import unittest

import psycopg

from .evidence import search_evidence


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = psycopg.connect(autocommit=True)
        cls.connection.execute("SET ROLE watt_analyst")
        cls.connection.execute("SET default_transaction_read_only = on")

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def ids(self, snapshot, month, words="", **scope):
        return {item["evidence_id"] for item in
                search_evidence(self.connection, snapshot, month, words, **scope)}

    def test_initial_version(self):
        self.assertEqual(self.ids("initial", "2025-11-01", "export credit", group="solar"),
                         {"solar-plan-v1"})

    def test_applicable_replacement(self):
        self.assertEqual(self.ids("refreshed", "2025-12-01", "export credit", group="solar"),
                         {"solar-plan-v2"})

    def test_latest_version_not_yet_effective_in_november(self):
        self.assertEqual(self.ids("refreshed", "2025-11-01", "export credit", group="solar"),
                         {"solar-plan-v1"})

    def test_superseded_text_does_not_resurface_on_keyword_match(self):
        self.assertEqual(self.ids("refreshed", "2025-12-01", "introductory", group="solar"), set())

    def test_settlement_posting_and_snapshot(self):
        self.assertEqual(self.ids("initial", "2025-11-01", "settlement", group="solar"), set())
        self.assertEqual(self.ids("refreshed", "2025-12-01", "settlement", group="solar", kind="settlement"),
                         {"solar-settlement-dec"})

    def test_future_month_rejected_by_snapshot(self):
        self.assertEqual(self.ids("initial", "2025-12-01", "export credit", group="solar"), set())

    def test_exact_contract_evidence_and_scope(self):
        scope = {"group": "solar", "evidence_id": "service-review-00001"}
        self.assertEqual(self.ids("refreshed", "2025-12-01", contract_id="contract-00001", **scope),
                         {"service-review-00001"})
        self.assertEqual(self.ids("refreshed", "2025-12-01", contract_id="contract-00000", **scope),
                         set())
        self.assertEqual(self.ids("refreshed", "2025-12-01", **scope), set())

    def test_unknown_cause_has_no_move_out_evidence(self):
        self.assertEqual(self.ids("refreshed", "2025-12-01", "move-out",
                                  group="solar", contract_id="contract-00000"), set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
