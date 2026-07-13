from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SECTIONS = [
    "Run Information", "Environment and Services", "Executive Summary",
    "Threshold Results", "Security and Privacy", "Data Integrity", "Graph Integrity",
    "Business Rules", "Intent Detection", "Entity Extraction", "RAG Retrieval",
    "Grounding and Citations", "Orchestrator", "Confirmation Safety", "Actions",
    "API", "End-to-End Results", "Performance", "Failed Scenarios", "Skipped Checks",
    "Recommendations",
]


def write_json(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


def _fmt(value: Any) -> str:
    if value is None:
        return "Not measured"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def write_markdown(result: dict[str, Any], path: Path) -> None:
    measured = result.get("metrics", {})
    content = ["# FusionMind Evaluation Report", ""]
    section_text = {
        "Run Information": f"Run ID: `{result['run']['run_id']}`  \nStarted: `{result['run']['started_at']}`",
        "Environment and Services": "\n".join(f"- {k}: {_fmt(v)}" for k, v in result.get("environment", {}).items()),
        "Executive Summary": f"Overall status: **{result.get('status', 'unknown').upper()}**. Measured checks use only calculated values; unavailable integrations are skipped.",
        "Threshold Results": "\n".join(f"- {k}: {'PASS' if v.get('pass') else 'FAIL'} (value={_fmt(v.get('value'))}, threshold={v.get('operator')} {v.get('threshold')})" for k, v in result.get("thresholds", {}).items()) or "No thresholds measured.",
        "Data Integrity": f"Status: `{result.get('data_integrity', {}).get('status', 'skipped')}`; pass rate: {_fmt(result.get('data_integrity', {}).get('pass_rate'))}",
        "Graph Integrity": f"Status: `{result.get('graph_integrity', {}).get('status', 'skipped')}`; pass rate: {_fmt(result.get('graph_integrity', {}).get('pass_rate'))}",
        "Business Rules": f"Status: `{result.get('business_rules', {}).get('status', 'skipped')}`; rule compliance rate: {_fmt(result.get('business_rules', {}).get('pass_rate'))}",
        "Intent Detection": json.dumps(measured.get("intent", {}), indent=2),
        "Entity Extraction": json.dumps(measured.get("entities", {}), indent=2),
        "Performance": json.dumps(measured.get("performance", {}), indent=2),
        "Failed Scenarios": "\n".join(f"- `{x.get('id')}`: {x.get('category')} expected `{x.get('expected')}`, got `{x.get('actual')}`" for x in result.get("failures", [])) or "None.",
        "Skipped Checks": "\n".join(f"- {x}" for x in result.get("skipped", [])) or "None.",
        "Recommendations": "\n".join(f"- {x}" for x in result.get("recommendations", [])) or "No recommendations generated.",
    }
    status_map = result.get("category_status", {})
    for section in SECTIONS:
        content.extend([f"## {section}", ""])
        text = section_text.get(section)
        if text is None:
            key = section.lower().replace(" and ", "_").replace("-", "_").replace(" ", "_")
            status = status_map.get(key, "skipped")
            text = f"Status: `{status}`."
        if text.strip().startswith("{"):
            content.extend(["```json", text, "```"])
        else:
            content.append(text)
        content.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(content), encoding="utf-8")
