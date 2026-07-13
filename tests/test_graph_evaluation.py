from eval.evaluate_graph import COUNT_CHECKS, REQUIRED_CONSTRAINTS, evaluate


class FakeGraph:
    def __init__(self, violations=0): self.violations = violations
    def read(self, query, **kwargs):
        if query.startswith("SHOW CONSTRAINTS"):
            return [{"labelsOrTypes": [label], "properties": [prop]} for label, prop in REQUIRED_CONSTRAINTS]
        return [{"violations": self.violations}]


def test_graph_evaluation_passes_complete_schema():
    result = evaluate(FakeGraph())
    assert result["status"] == "pass"
    assert result["pass_rate"] == 1


def test_graph_evaluation_reports_violations():
    result = evaluate(FakeGraph(violations=1))
    assert result["status"] == "fail"
    assert any(not check["pass"] for check in result["checks"])
