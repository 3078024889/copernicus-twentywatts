import unittest

from tw10.paired_evaluation import PROTOCOL, summarize_paired


def row(seed, transfer=1.0, retention=0.5, ratio=1.0, updates=100, probes=200):
    return {
        "seed": seed,
        "transfer_pp": transfer,
        "retention_pp": retention,
        "cpu_ratio_inherit_to_reset": ratio,
        "comparable_updates": updates,
        "comparable_probes": probes,
        "budget_operations_equal": True,
    }


class PairedEvaluationTests(unittest.TestCase):
    def test_primary_keeps_cpu_mismatch(self):
        result = summarize_paired([row(1, ratio=1.0), row(2, ratio=1.8)], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 2)
        self.assertEqual(result["cpu_fair_pairs"], 1)
        self.assertEqual(result["primary_transfer_pp"]["n"], 2)
        self.assertEqual(result["cpu_fair_transfer_secondary"]["n"], 1)

    def test_duplicate_seed_excluded_and_retained_in_ledger(self):
        result = summarize_paired([row(1), row(1, transfer=9)], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 1)
        self.assertIn("DUPLICATE_SEED", result["records"][1]["eligibility_reasons"])
        self.assertEqual(result["input_records"], 2)

    def test_operation_budget_mismatch_excluded(self):
        bad = row(2)
        bad["budget_operations_equal"] = False
        result = summarize_paired([row(1), bad], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 1)
        self.assertIn("OPERATION_BUDGET_MISMATCH", result["records"][1]["eligibility_reasons"])

    def test_missing_cpu_does_not_exclude_primary(self):
        item = row(3)
        item["cpu_ratio_inherit_to_reset"] = None
        result = summarize_paired([item], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 1)
        self.assertEqual(result["cpu_fair_pairs"], 0)

    def test_invalid_metric_excluded(self):
        item = row(4)
        item["retention_pp"] = float("nan")
        result = summarize_paired([item], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 0)
        self.assertIn("INVALID_RETENTION_PP", result["records"][0]["eligibility_reasons"])

    def test_deterministic_ledger_hash(self):
        data = [row(7), row(8, transfer=-0.2)]
        a = summarize_paired(data, bootstrap_draws=200)
        b = summarize_paired(data, bootstrap_draws=200)
        self.assertEqual(a["ledger_sha256"], b["ledger_sha256"])
        self.assertEqual(a["primary_transfer_pp"], b["primary_transfer_pp"])

    def test_sealed_outcomes_never_claimed_as_eligibility_input(self):
        result = summarize_paired([row(9)], bootstrap_draws=200)
        self.assertFalse(result["sealed_outcomes_used_for_eligibility"])
        self.assertEqual(result["certified_ais"], 0)
        self.assertEqual(result["mother_promotion"], "LOCKED")

    def test_invalid_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            summarize_paired([row(1)], cpu_tolerance=1.1, bootstrap_draws=200)

    def test_empty_input_is_explicit(self):
        result = summarize_paired([], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 0)
        self.assertIsNone(result["primary_transfer_pp"]["mean"])

    def test_invalid_budget_rejected(self):
        item = row(10, updates=0)
        result = summarize_paired([item], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 0)
        self.assertIn("INVALID_UPDATE_BUDGET", result["records"][0]["eligibility_reasons"])



    def test_missing_operation_budget_fails_closed(self):
        item = row(11)
        item.pop("budget_operations_equal")
        result = summarize_paired([item], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 0)
        self.assertIn("OPERATION_BUDGET_MISMATCH", result["records"][0]["eligibility_reasons"])

    def test_unknown_operation_budget_fails_closed(self):
        item = row(12)
        item["budget_operations_equal"] = None
        result = summarize_paired([item], bootstrap_draws=200)
        self.assertEqual(result["primary_eligible_seeds"], 0)
        self.assertIn("OPERATION_BUDGET_MISMATCH", result["records"][0]["eligibility_reasons"])
if __name__ == "__main__":
    unittest.main()
