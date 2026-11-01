"""Offline regression tests for arithmetic, validation, and tool-result transport."""

import copy
import json
import unittest

import smoke

# Hand-calculated literals: the expectations do not call the implementation.
EXPECTED = {
    "currency": "JPY",
    "total_pnl_jpy": -4605000,
    "rate_pnl_jpy": -3325000,
    "spread_pnl_jpy": -1280000,
    "positions": [
        {"bond_id": "JGB_2Y", "pnl_jpy": -300000},
        {"bond_id": "JGB_10Y", "pnl_jpy": -2125000},
        {"bond_id": "CORP_5Y", "pnl_jpy": -2180000},
    ],
    "risk_factors": [
        {"factor": "interest_rate", "shock_bp": 25, "pnl_jpy": -3325000, "impact": "loss"},
        {"factor": "credit_spread", "shock_bp": 40, "pnl_jpy": -1280000, "impact": "loss"},
    ],
    "dominant_risk_factor": "interest_rate",
    "worst_bond_id": "CORP_5Y",
}

REPORT = {
    **EXPECTED,
    "comment_ja": "金利上昇と信用スプレッド拡大の双方による損失が生じます。",
    "explanation_ja": {
        "total": "合計損益は-4605000円で損失です。",
        "interest_rate": "金利による損益は-3325000円で損失です。",
        "credit_spread": "信用スプレッドによる損益は-1280000円で損失です。",
        "concentration": "最大損失銘柄はCORP_5Yで、損益は-2180000円です。",
    },
}

ARGS = {"portfolio_id": "fictional-jpy-bonds-v1", "rate_shock_bp": 25, "spread_shock_bp": 40}


class CalculationTests(unittest.TestCase):
    def test_linear_shock_sign_units_and_aggregation(self):
        self.assertEqual(smoke.calculate_pnl(**ARGS), EXPECTED)

    def test_zero_and_reversed_shocks(self):
        zero = smoke.calculate_pnl(ARGS["portfolio_id"], 0, 0)
        self.assertEqual(zero["total_pnl_jpy"], 0)
        reversed_result = smoke.calculate_pnl(ARGS["portfolio_id"], -25, -40)
        self.assertEqual(reversed_result["total_pnl_jpy"], 4605000)
        self.assertEqual(reversed_result["rate_pnl_jpy"], 3325000)

    def test_unknown_portfolio_and_boolean_shock_are_rejected(self):
        for portfolio, rate in [("unknown", 25), (ARGS["portfolio_id"], True)]:
            with self.subTest(portfolio=portfolio, rate=rate), self.assertRaises(ValueError):
                smoke.calculate_pnl(portfolio, rate, 40)

    def test_tool_whitelist_and_scenario_integrity(self):
        self.assertEqual(smoke.execute_tool("calculate_pnl", ARGS), EXPECTED)
        with self.assertRaises(ValueError):
            smoke.execute_tool("run_shell", ARGS)
        with self.assertRaises(ValueError):
            smoke.execute_tool("calculate_pnl", {**ARGS, "rate_shock_bp": 1})


class ValidationTests(unittest.TestCase):
    def test_complete_report_and_reordered_arrays_are_valid(self):
        report = copy.deepcopy(REPORT)
        report["positions"].reverse()
        report["risk_factors"].reverse()
        self.assertEqual(smoke.schema_issues(report), [])
        self.assertEqual(smoke.consistency_issues(report, EXPECTED), [])

    def test_schema_rejects_missing_extra_wrong_type_and_wrong_enum(self):
        examples = []
        missing = copy.deepcopy(REPORT)
        del missing["currency"]
        examples.append(missing)
        examples.append({**REPORT, "unrequested": "field"})
        examples.append({**REPORT, "total_pnl_jpy": True})
        examples.append({**REPORT, "currency": "USD"})
        for report in examples:
            with self.subTest(report=report):
                self.assertTrue(smoke.schema_issues(report))

    def test_consistency_rejects_wrong_total_and_duplicate_bond(self):
        self.assertTrue(smoke.consistency_issues({**REPORT, "total_pnl_jpy": 0}, EXPECTED))
        report = copy.deepcopy(REPORT)
        report["positions"][2] = dict(report["positions"][0])
        self.assertTrue(smoke.consistency_issues(report, EXPECTED))

    def test_narrative_rejects_wrong_number_direction_language_and_bond(self):
        for field, text in [
            ("total", "合計損益は-460500円で損失です。"),
            ("interest_rate", "金利損益は-3325000円で利益です。"),
            ("credit_spread", "Credit spread PNL is -1280000 JPY loss."),
            ("concentration", "最大損失銘柄はJGB_2Yで、損益は-2180000円です。"),
        ]:
            report = copy.deepcopy(REPORT)
            report["explanation_ja"][field] = text
            with self.subTest(field=field):
                self.assertTrue(smoke.consistency_issues(report, EXPECTED))

    def test_nested_secret_values_are_removed_before_logging(self):
        secret = "unit_test_secret_A"
        clean = smoke.redact({"raw": [f"prefix {secret} suffix"]}, [secret])
        self.assertNotIn(secret, json.dumps(clean))
        self.assertEqual(clean, {"raw": ["prefix [REDACTED] suffix"]})

    def test_contradictory_comment_cannot_pass(self):
        report = copy.deepcopy(REPORT)
        report["comment_ja"] = "金利上昇で利益が出ます。"
        self.assertTrue(smoke.consistency_issues(report, EXPECTED))

    def test_negated_explanation_cannot_pass(self):
        report = copy.deepcopy(REPORT)
        report["explanation_ja"]["total"] = "合計損益は-4605000円ではありません。損失は0円です。"
        self.assertTrue(smoke.consistency_issues(report, EXPECTED))


class ProviderLoopTests(unittest.TestCase):
    def fake_transport(self, provider):
        calls = []

        def send(url, headers, body):
            calls.append(body)
            if len(calls) == 1:
                if provider == "openai":
                    self.assertEqual(body["tool_choice"], "auto")
                    response = {
                        "status": "completed",
                        "output": [
                            {
                                "type": "function_call",
                                "name": "calculate_pnl",
                                "call_id": "call_1",
                                "arguments": json.dumps(ARGS),
                            }
                        ],
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                    }
                else:
                    self.assertEqual(body["tool_choice"]["type"], "auto")
                    response = {
                        "stop_reason": "tool_use",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "tool_1",
                                "name": "calculate_pnl",
                                "input": ARGS,
                            }
                        ],
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                    }
            else:
                self.assertEqual(len(calls), 2, "extra generation request would increase cost")
                if provider == "openai":
                    output = body["input"][-1]
                    self.assertEqual(output["call_id"], "call_1")
                    self.assertEqual(json.loads(output["output"]), EXPECTED)
                    response = {
                        "status": "completed",
                        "output": [
                            {
                                "type": "message",
                                "content": [{"type": "output_text", "text": json.dumps(REPORT)}],
                            }
                        ],
                        "usage": {"input_tokens": 20, "output_tokens": 30},
                    }
                else:
                    output = body["messages"][-1]["content"][0]
                    self.assertEqual(output["tool_use_id"], "tool_1")
                    self.assertEqual(json.loads(output["content"]), EXPECTED)
                    response = {
                        "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": json.dumps(REPORT)}],
                        "usage": {"input_tokens": 20, "output_tokens": 30},
                    }
            return {"http_status": 200, "latency_ms": 1.0, "response": response}

        return send, calls

    def test_both_wire_protocols_return_python_result_and_account_usage(self):
        for provider in ["openai", "anthropic"]:
            with self.subTest(provider=provider):
                send, calls = self.fake_transport(provider)
                result = smoke.run_provider(provider, "unit_test_secret_A", "test-model", send)
                self.assertEqual(
                    result["checks"],
                    {"structured_json": "PASS", "tool_calling": "PASS", "multi_step": "PASS"},
                )
                self.assertEqual(len(calls), 2)
                self.assertEqual(result["usage"]["input_tokens"], 30)
                self.assertEqual(result["usage"]["output_tokens"], 35)
                self.assertNotIn("unit_test_secret_A", json.dumps(result))

    def test_http_error_is_not_retried_and_has_no_secret_in_artifact(self):
        calls = []

        def send(url, headers, body):
            calls.append(body)
            return {
                "http_status": 401,
                "latency_ms": 1.0,
                "response": {"error": {"message": "invalid unit_test_secret_A"}},
            }

        result = smoke.run_provider("openai", "unit_test_secret_A", "test-model", send)
        self.assertEqual(len(calls), 1)
        self.assertEqual(set(result["checks"].values()), {"FAIL"})
        self.assertNotIn("unit_test_secret_A", json.dumps(result))

    def test_truncated_first_response_does_not_execute_or_return_tool(self):
        for provider in ["openai", "anthropic"]:
            send, calls = self.fake_transport(provider)

            def truncated(url, headers, body, send=send, calls=calls, provider=provider):
                record = send(url, headers, body)
                if len(calls) == 1:
                    field, value = (
                        ("status", "incomplete")
                        if provider == "openai"
                        else ("stop_reason", "max_tokens")
                    )
                    record["response"][field] = value
                return record

            with self.subTest(provider=provider):
                result = smoke.run_provider(provider, "unit_test_secret_A", "test-model", truncated)
                self.assertEqual(len(calls), 1)
                self.assertEqual(result["tool_trace"], [])
                self.assertEqual(set(result["checks"].values()), {"FAIL"})

    def test_malformed_response_and_usage_preserve_failure_record(self):
        for response in [None, [], {"usage": None}, {"usage": {"input_tokens": "ten"}}]:
            with self.subTest(response=response):

                def malformed(url, headers, body, response=response):
                    return {"http_status": 200, "latency_ms": 1.0, "response": response}

                result = smoke.run_provider("openai", "unit_test_secret_A", "test-model", malformed)
                self.assertEqual(len(result["requests"]), 1)
                self.assertEqual(set(result["checks"].values()), {"FAIL"})
                self.assertTrue(result["failures"])
                json.dumps(result)


if __name__ == "__main__":
    unittest.main()
