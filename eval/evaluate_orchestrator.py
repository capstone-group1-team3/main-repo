from __future__ import annotations
from eval.scoring import tool_path_metrics


def score(expected_paths: list[list[str]], actual_paths: list[list[str]], forbidden: list[list[str]] | None = None):
    return tool_path_metrics(expected_paths, actual_paths, forbidden)
