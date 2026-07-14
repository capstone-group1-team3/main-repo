"""Safe FusionMind evaluation runner.

Offline checks are always available. Live checks are opt-in and write-intent
fixtures are skipped unless an isolated environment is explicitly authorized.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from eval.evaluate_data import evaluate as evaluate_data
from eval.evaluate_graph import evaluate as evaluate_graph
from eval.evaluate_business_rules import evaluate as evaluate_business_rules
from eval.models import EvaluationCase
from eval.reporting import write_json, write_markdown
from eval.scoring import classification_metrics, entity_slot_metrics, percentile


def load_cases(location: Path) -> list[EvaluationCase]:
    if location.is_file():
        paths = [location]
    else:
        candidates = [
            location / "heldout.jsonl", location / "new_heldout_cases.jsonl",
            location / "additional_cases.jsonl",
        ]
        paths = [p for p in candidates if p.exists()]
    cases: list[EvaluationCase] = []
    seen: set[str] = set()
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                case = EvaluationCase.from_dict(json.loads(line))
            except Exception as exc:
                raise ValueError(f"invalid fixture {path}:{line_number}: {exc}") from exc
            if case.id in seen:
                raise ValueError(f"duplicate fixture id: {case.id}")
            seen.add(case.id); cases.append(case)
    if not cases:
        raise ValueError(f"no JSONL fixtures found at {location}")
    return cases


def offline_intent_entities(cases: list[EvaluationCase]) -> tuple[dict, dict, list[dict]]:
    from app.agents.orchestrator.intent_detector import detect_intent
    from app.agents.orchestrator.entity_extractor import extract_entities

    gold: list[str] = []; predicted: list[str] = []
    expected_entities: list[dict] = []; actual_entities: list[dict] = []
    failures = []
    for case in cases:
        # A bare confirmation reply only has meaning with persisted pending state.
        # It is covered by contextual confirmation tests, not stateless scoring.
        if case.metadata.get("requires_prior_confirmation"):
            continue
        intent = detect_intent(case.message, use_llm_fallback=False)["intent"]
        entities = extract_entities(case.message, intent=intent)
        gold.append(case.expected_intent); predicted.append(intent)
        if case.expected_entities:
            expected_entities.append(case.expected_entities); actual_entities.append(entities)
        if intent != case.expected_intent:
            failures.append({"id": case.id, "category": "intent", "expected": case.expected_intent, "actual": intent})
    return classification_metrics(gold, predicted), entity_slot_metrics(expected_entities, actual_entities), failures


def live_read_only(cases: list[EvaluationCase], base_url: str, token: str) -> tuple[dict, list[str]]:
    import httpx
    timings = []; errors = 0; count = 0
    skipped = []
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=30.0) as client:
        for case in cases:
            if case.performs_write:
                skipped.append(f"{case.id}: write scenario requires isolated --allow-write-evaluation environment")
                continue
            started = time.perf_counter()
            try:
                response = client.post("/chat", json={"message": case.message})
                errors += int(response.status_code >= 400)
            except Exception:
                errors += 1
            timings.append(time.perf_counter() - started); count += 1
    return {
        "count": count, "p50_latency_seconds": percentile(timings, .50),
        "p95_latency_seconds": percentile(timings, .95),
        "error_rate": None if count == 0 else errors / count,
    }, skipped


def threshold(value: float | None, minimum: float) -> dict[str, Any] | None:
    if value is None:
        return None
    return {"value": value, "operator": ">=", "threshold": minimum, "pass": value >= minimum}


def run(args: argparse.Namespace) -> dict[str, Any]:
    allow_write_evaluation = bool(getattr(args, "allow_write_evaluation", False))
    if allow_write_evaluation and args.graph_read_only:
        raise ValueError("--graph-read-only cannot be combined with --allow-write-evaluation")
    if allow_write_evaluation and os.getenv("FUSIONMIND_EVAL_ISOLATED", "").lower() != "true":
        raise ValueError("FUSIONMIND_EVAL_ISOLATED=true is required for --allow-write-evaluation")

    started_at = datetime.now(timezone.utc).isoformat()
    cases = load_cases(Path(args.fixtures))
    intent, entities, failures = offline_intent_entities(cases)
    data = evaluate_data(Path(args.processed_dir))
    business = evaluate_business_rules(ROOT / "business_rules.yaml")
    graph = {"status": "skipped", "pass_rate": None, "checks": []}
    skipped = [
        "RAG retrieval and grounding: evaluation metadata/live token not configured.",
        "Actions, privacy, confirmation, and E2E writes: isolated records not configured.",
    ]
    contextual_cases = [
        case.id for case in cases
        if case.metadata.get("requires_prior_confirmation")
    ]
    if contextual_cases:
        skipped.append(
            "Context-dependent confirmation fixtures excluded from stateless intent "
            f"scoring: {', '.join(contextual_cases)}."
        )
    if args.graph_read_only:
        try:
            from app.graph.neo4j_client import Neo4jClient
            with Neo4jClient() as client:
                graph = evaluate_graph(client)
        except Exception as exc:
            graph = {"status": "error", "pass_rate": None, "checks": [], "error_category": type(exc).__name__}
    else:
        skipped.insert(0, "Graph integrity: use --graph-read-only to run safe current-database checks.")
    performance = {"count": 0, "p50_latency_seconds": None, "p95_latency_seconds": None, "error_rate": None}
    if args.token and not allow_write_evaluation:
        performance, live_skipped = live_read_only(cases, args.base_url, args.token)
        skipped.extend(live_skipped)

    live_result: dict[str, Any] | None = None
    if allow_write_evaluation:
        # The stateful suite creates isolated evaluation users and obtains its
        # own short-lived JWTs.  It is deliberately imported and called only
        # behind the explicit write flag and isolation gate above.
        from eval.live_suite import run as run_live_suite

        live_result = run_live_suite(args.base_url, allow_writes=True)
        skipped = [
            item for item in skipped
            if not item.startswith("RAG retrieval and grounding:")
            and not item.startswith("Actions, privacy, confirmation, and E2E writes:")
            and not item.startswith("Graph integrity: use --graph-read-only")
        ]

    checks = {
        "data_integrity": threshold(data.get("pass_rate"), 1.0),
        "rule_compliance": threshold(business.get("pass_rate"), 1.0),
        "intent_macro_f1": threshold(intent.get("macro_f1"), args.intent_macro_f1_threshold),
    }
    if entities.get("normalized_match") is not None:
        checks["entity_slot_accuracy"] = threshold(entities["normalized_match"], args.entity_accuracy_threshold)
    if graph.get("pass_rate") is not None:
        checks["graph_integrity"] = threshold(graph["pass_rate"], 1.0)
    checks = {k: v for k, v in checks.items() if v is not None}
    status = "pass" if all(v["pass"] for v in checks.values()) else "fail"
    result = {
        "run": {"run_id": uuid.uuid4().hex, "started_at": started_at, "fixture_count": len(cases)},
        "environment": {
            "base_url": args.base_url,
            "live_token_supplied": bool(args.token),
            "write_evaluation": allow_write_evaluation,
            "isolated_evaluation": os.getenv("FUSIONMIND_EVAL_ISOLATED", "").lower() == "true",
        },
        "status": status, "thresholds": checks,
        "metrics": {"intent": intent, "entities": entities, "performance": performance},
        "data_integrity": data, "graph_integrity": graph, "business_rules": business,
        "failures": failures, "skipped": skipped,
        "category_status": {
            "security_privacy": "skipped", "graph_integrity": graph["status"],
            "business_rules": business["status"], "rag_retrieval": "skipped",
            "grounding_citations": "skipped", "orchestrator": "skipped",
            "confirmation_safety": "skipped", "actions": "skipped", "api": "skipped",
            "end_to_end_results": "skipped",
        },
        "recommendations": [
            "Run graph/RAG/privacy suites only against isolated test services and controlled records.",
            "Treat failed intent classes in the detailed confusion matrix as routing work, not as LLM score tuning.",
        ],
    }

    if live_result is not None:
        # Keep the established live-suite section names so existing consumers
        # and reports can compare read-only and isolated runs directly.
        result.update({
            key: live_result[key]
            for key in (
                "rag_retrieval", "grounding_citations", "graph_integrity",
                "orchestrator", "confirmation_safety", "actions",
                "security_privacy", "api", "end_to_end_results", "performance",
            )
            if key in live_result
        })
        result["failures"].extend(live_result.get("failures", []))
        result["status"] = "pass" if not result["failures"] and status == "pass" else "fail"
        result["category_status"] = {
            "security_privacy": "pass" if live_result.get("security_privacy", {}).get("pass") else "failed",
            "graph_integrity": live_result.get("graph_integrity", {}).get("status", "completed"),
            "business_rules": business["status"],
            "rag_retrieval": "completed",
            "grounding_citations": "pass" if live_result.get("grounding_citations", {}).get("grounding_pass_rate") == 1.0 else "failed",
            "orchestrator": "completed",
            "confirmation_safety": "pass" if live_result.get("confirmation_safety", {}).get("pass_rate") == 1.0 else "failed",
            "actions": "pass" if live_result.get("actions", {}).get("action_accuracy") == 1.0 else "failed",
            "api": "pass" if live_result.get("api", {}).get("pass_rate") == 1.0 else "failed",
            "end_to_end_results": "pass" if live_result.get("end_to_end_results", {}).get("pass_rate") == 1.0 else "failed",
            "performance": "completed",
        }
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", "--base", default="http://localhost:8000")
    p.add_argument("--token", default=os.getenv("FUSIONMIND_EVAL_TOKEN", ""))
    p.add_argument("--fixtures", default=str(ROOT / "eval"))
    p.add_argument("--processed-dir", default=str(ROOT / "data" / "processed"))
    p.add_argument("--json-output", "--out", default=str(ROOT / "eval" / "reports" / "results.json"))
    p.add_argument("--markdown-output", default=str(ROOT / "eval" / "reports" / "report.md"))
    p.add_argument("--intent-macro-f1-threshold", type=float, default=.90)
    p.add_argument("--entity-accuracy-threshold", type=float, default=.85)
    p.add_argument("--graph-read-only", action="store_true")
    p.add_argument(
        "--allow-write-evaluation",
        action="store_true",
        help="Run the stateful live suite; requires FUSIONMIND_EVAL_ISOLATED=true.",
    )
    return p


def main() -> None:
    args = parser().parse_args()
    result = run(args)
    write_json(result, Path(args.json_output))
    write_markdown(result, Path(args.markdown_output))
    print(json.dumps({"status": result["status"], "json": args.json_output, "markdown": args.markdown_output}, indent=2))
    raise SystemExit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
