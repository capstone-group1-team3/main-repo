from __future__ import annotations
from eval.scoring import classification_metrics, entity_slot_metrics


def score_intents(expected: list[str], actual: list[str]):
    return classification_metrics(expected, actual)


def score_entities(expected: list[dict], actual: list[dict]):
    return entity_slot_metrics(expected, actual)
