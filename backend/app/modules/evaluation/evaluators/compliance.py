"""Business Policy and Regulatory Compliance Evaluator."""

from __future__ import annotations

from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


class ComplianceEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "compliance"

    def evaluate(
        self,
        query: str,
        expected_answer: str,
        actual_answer: str,
        retrieved_chunks: list[dict[str, Any]] | None = None,
        citations: list[dict[str, Any]] | None = None,
        is_unanswerable: bool = False,
        configuration: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MetricScoreResult:
        config = configuration or {}
        policy_rules: list[dict[str, Any]] = config.get("policies", [])

        if not policy_rules:
            # Default corporate compliance check: answer should not advise bypassing established policies
            bypass_terms = ["bypass approval", "ignore kyc", "skip compliance", "without authorization"]
            actual_lower = actual_answer.lower()
            detected_bypasses = [t for t in bypass_terms if t in actual_lower]
            compliant = len(detected_bypasses) == 0

            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=1.0 if compliant else 0.0,
                normalized_score=100.0 if compliant else 0.0,
                status=MetricStatus.MEASURED,
                evaluator_version=self.version,
                details={
                    "compliant": compliant,
                    "policy_rules_evaluated": 1,
                    "detected_violations": detected_bypasses,
                    "disclaimer": "Automated policy check only; does not constitute legal counsel.",
                },
            )

        passed_rules = 0
        failed_rules = []
        actual_lower = actual_answer.lower()

        for rule in policy_rules:
            rule_id = rule.get("control_id", "rule")
            required_phrase = rule.get("required_phrase")
            forbidden_phrase = rule.get("forbidden_phrase")

            passed = True
            if required_phrase and required_phrase.lower() not in actual_lower:
                passed = False
            if forbidden_phrase and forbidden_phrase.lower() in actual_lower:
                passed = False

            if passed:
                passed_rules += 1
            else:
                failed_rules.append(rule_id)

        ratio = passed_rules / len(policy_rules)

        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=round(ratio, 4),
            normalized_score=round(ratio * 100.0, 2),
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "total_policies": len(policy_rules),
                "passed_policies": passed_rules,
                "failed_policies": failed_rules,
                "disclaimer": "Automated policy check only; does not constitute legal counsel.",
            },
        )
