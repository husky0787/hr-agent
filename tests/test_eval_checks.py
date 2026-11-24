"""Regression checks for Golden assertions, without API calls or database writes."""

import unittest
from unittest.mock import patch

from evals import run_evals


class GoldenAssertionTests(unittest.TestCase):
    def evaluate(self, response, expect):
        result = {"response": response, "tool_calls": [], "citations": []}
        with (
            patch.object(run_evals, "run_agent", return_value=result),
        ):
            return run_evals.run_scenario({"id": "assertion-test", "input": "test", "expect": expect})

    def test_each_forbidden_phrase_fails_independently(self):
        phrases = ["security rules", "orchestrator", "route rules"]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                outcome = self.evaluate(phrase.upper(), {"not_contains": phrases})
                self.assertFalse(outcome["passed"])
                self.assertFalse(outcome["checks"]["not_contains"])

    def test_safe_response_passes_forbidden_phrase_check(self):
        self.assertTrue(self.evaluate("可查詢公司政策。", {"not_contains": ["service down", "hacked"]})["passed"])

    def test_alternative_wording_accepts_either_language(self):
        expect = {"contains_any": ["港幣", "HKD"]}
        for response in ("以港幣申報。", "Submit in hkd."):
            with self.subTest(response=response):
                self.assertTrue(self.evaluate(response, expect)["passed"])
        self.assertFalse(self.evaluate("Submit in EUR.", expect)["passed"])

    def test_alternatives_do_not_replace_required_facts(self):
        expect = {"contains": ["Expensify"], "contains_any": ["未確認", "尚未"]}
        self.assertFalse(self.evaluate("金額未確認。", expect)["passed"])
        self.assertFalse(self.evaluate("透過 Expensify 提交。", expect)["passed"])
        self.assertTrue(self.evaluate("金額尚未確認，透過 Expensify 提交。", expect)["passed"])


if __name__ == "__main__":
    unittest.main()
