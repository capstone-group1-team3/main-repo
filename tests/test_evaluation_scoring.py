from pathlib import Path
import json

from eval.models import EvaluationCase
from eval.reporting import write_json, write_markdown
from eval.scoring import (
    classification_metrics, entity_slot_metrics, grounding_metrics,
    percentile, retrieval_metrics, tool_path_metrics,
)


def test_fixture_model_accepts_legacy_input_field():
    case = EvaluationCase.from_dict({"id": "x", "input": "hello", "expected_intent": "policy_question"})
    assert case.message == "hello"


def test_intent_metrics_and_empty_input():
    metrics = classification_metrics(["a", "a", "b"], ["a", "b", "b"])
    assert metrics["accuracy"] == 2 / 3
    empty = classification_metrics([], [])
    assert empty["accuracy"] is None


def test_entity_slot_scoring():
    metrics = entity_slot_metrics([{"order_id": "ORD-1"}], [{"order_id": "ord1"}])
    assert metrics["exact_match"] == 0
    assert metrics["normalized_match"] == 1


def test_retrieval_top_k_and_mrr():
    metrics = retrieval_metrics([{"refund.md"}, {"return.md"}], [["refund.md"], ["x", "return.md"]])
    assert metrics["top_1"] == .5
    assert metrics["top_3"] == 1
    assert metrics["mrr"] == .75


def test_tool_path_and_grounding():
    tools = tool_path_metrics([["rag", "graph"]], [["rag", "graph"]], [["action"]])
    assert tools["exact_path_accuracy"] == 1
    grounding = grounding_metrics([{"candidates": ["c1"], "accepted": ["c1"], "invalid": [], "supported": True}])
    assert grounding["citation_validity"] == 1
    assert grounding["grounding_pass_rate"] == 1


def test_percentile_and_report_generation(tmp_path: Path):
    assert percentile([1, 2, 3, 4], .95) == 4
    result = {
        "run": {"run_id": "test", "started_at": "now"}, "environment": {},
        "status": "pass", "thresholds": {}, "metrics": {}, "data_integrity": {},
        "failures": [], "skipped": [], "recommendations": [], "category_status": {},
    }
    json_path = tmp_path / "result.json"; md_path = tmp_path / "report.md"
    write_json(result, json_path); write_markdown(result, md_path)
    assert json.loads(json_path.read_text())["status"] == "pass"
    text = md_path.read_text()
    assert "# FusionMind Evaluation Report" in text
    assert "## Performance" in text
