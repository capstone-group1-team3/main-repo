# FusionMind Evaluation Report

## Run Information

Run ID: `9973e8df1db74e2cb3bffd17800078ce`  
Started: `2026-07-12T07:59:26.000591+00:00`

## Environment and Services

- base_url: http://localhost:8000
- live_token_supplied: False
- write_evaluation: False

## Executive Summary

Overall status: **PASS**. Measured checks use only calculated values; unavailable integrations are skipped.

## Threshold Results

- data_integrity: PASS (value=1.0000, threshold=>= 1.0)
- rule_compliance: PASS (value=1.0000, threshold=>= 1.0)
- intent_macro_f1: PASS (value=0.9524, threshold=>= 0.9)
- entity_slot_accuracy: PASS (value=1.0000, threshold=>= 0.85)
- graph_integrity: PASS (value=1.0000, threshold=>= 1.0)

## Security and Privacy

Status: `skipped`.

## Data Integrity

Status: `pass`; pass rate: 1.0000

## Graph Integrity

Status: `pass`; pass rate: 1.0000

## Business Rules

Status: `pass`; rule compliance rate: 1.0000

## Intent Detection

```json
{
  "count": 90,
  "accuracy": 0.9555555555555556,
  "macro_precision": 0.9671957671957673,
  "macro_recall": 0.9457070707070707,
  "macro_f1": 0.9524111182934712,
  "per_label": {
    "cancel_order": {
      "precision": 1.0,
      "recall": 0.8181818181818182,
      "f1": 0.9,
      "support": 11
    },
    "damaged_product": {
      "precision": 1.0,
      "recall": 0.75,
      "f1": 0.8571428571428571,
      "support": 4
    },
    "order_tracking": {
      "precision": 1.0,
      "recall": 0.8888888888888888,
      "f1": 0.9411764705882353,
      "support": 9
    },
    "payment_issue": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 5
    },
    "policy_question": {
      "precision": 0.9259259259259259,
      "recall": 1.0,
      "f1": 0.9615384615384615,
      "support": 25
    },
    "refund_request": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 11
    },
    "replacement_request": {
      "precision": 0.8888888888888888,
      "recall": 1.0,
      "f1": 0.9411764705882353,
      "support": 8
    },
    "return_request": {
      "precision": 0.8571428571428571,
      "recall": 1.0,
      "f1": 0.923076923076923,
      "support": 6
    },
    "ticket_status": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 4
    },
    "warranty_claim": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 7
    }
  },
  "confusion_matrix": {
    "cancel_order": {
      "cancel_order": 9,
      "damaged_product": 0,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 2,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "damaged_product": {
      "cancel_order": 0,
      "damaged_product": 3,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 1,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "order_tracking": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 8,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 1,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "payment_issue": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 0,
      "payment_issue": 5,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "policy_question": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 25,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "refund_request": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 11,
      "replacement_request": 0,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "replacement_request": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 8,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "return_request": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 6,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "ticket_status": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 0,
      "ticket_status": 4,
      "warranty_claim": 0
    },
    "warranty_claim": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 7
    }
  }
}
```

## Entity Extraction

```json
{
  "count": 23,
  "exact_match": 1.0,
  "normalized_match": 1.0,
  "per_slot": {
    "issue": {
      "count": 6,
      "exact": 1.0,
      "normalized": 1.0
    },
    "order_id": {
      "count": 8,
      "exact": 1.0,
      "normalized": 1.0
    },
    "product": {
      "count": 3,
      "exact": 1.0,
      "normalized": 1.0
    },
    "requested_action": {
      "count": 6,
      "exact": 1.0,
      "normalized": 1.0
    }
  }
}
```

## RAG Retrieval

Status: `skipped`.

## Grounding and Citations

Status: `skipped`.

## Orchestrator

Status: `skipped`.

## Confirmation Safety

Status: `skipped`.

## Actions

Status: `skipped`.

## API

Status: `skipped`.

## End-to-End Results

Status: `skipped`.

## Performance

```json
{
  "count": 0,
  "p50_latency_seconds": null,
  "p95_latency_seconds": null,
  "error_rate": null
}
```

## Failed Scenarios

- `hold-0076`: intent expected `damaged_product`, got `replacement_request`
- `hold-0077`: intent expected `order_tracking`, got `return_request`
- `hold-0078`: intent expected `cancel_order`, got `policy_question`
- `hold-0079`: intent expected `cancel_order`, got `policy_question`

## Skipped Checks

- RAG retrieval and grounding: evaluation metadata/live token not configured.
- Actions, privacy, confirmation, and E2E writes: isolated records not configured.

## Recommendations

- Run graph/RAG/privacy suites only against isolated test services and controlled records.
- Treat failed intent classes in the detailed confusion matrix as routing work, not as LLM score tuning.
