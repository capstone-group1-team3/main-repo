from pathlib import Path
from eval.evaluate_business_rules import evaluate


def test_deterministic_business_rule_evaluator_passes_current_source():
    result = evaluate(Path(__file__).resolve().parents[1] / "business_rules.yaml")
    assert result["status"] == "pass"
    assert result["pass_rate"] == 1
