# FusionMind Evaluation Report

## Run Information

Run ID: `0fc2b17f69494491ab255d507c593d0f`
Started: `2026-07-14T09:37:44.849249+00:00`

## Environment and Services

- base_url: http://localhost:18000
- live_token_supplied: False
- write_evaluation: True
- isolated_evaluation: True

## Executive Summary

Overall status: **FAIL**. Measured checks use only calculated values; unavailable integrations are skipped.

## Threshold Results

- data_integrity: PASS (value=1.0000, threshold=>= 1.0)
- rule_compliance: PASS (value=1.0000, threshold=>= 1.0)
- intent_macro_f1: PASS (value=1.0000, threshold=>= 0.9)
- entity_slot_accuracy: PASS (value=1.0000, threshold=>= 0.85)

## Security and Privacy

Status: `completed`.

<details>
<summary>Detailed results</summary>

```json
{
  "count": 6,
  "privacy_pass_rate": 1.0,
  "pass": true,
  "checks": [
    {
      "name": "protected_endpoint_requires_auth",
      "pass": true
    },
    {
      "name": "invalid_token_rejected",
      "pass": true
    },
    {
      "name": "expired_token_rejected",
      "pass": true
    },
    {
      "name": "customer_order_isolation",
      "pass": true
    },
    {
      "name": "cross_customer_chat_denied",
      "pass": true
    },
    {
      "name": "safe_errors_no_secrets",
      "pass": true
    }
  ]
}
```

</details>

## Data Integrity

Status: `pass`; pass rate: 1.0000

## Graph Integrity

Status: `pass`.

<details>
<summary>Detailed results</summary>

```json
{
  "status": "pass",
  "pass_rate": 1.0,
  "checks": [
    {
      "name": "required_constraints",
      "pass": true,
      "missing": []
    },
    {
      "name": "duplicate_customer_ids",
      "pass": true,
      "violations": 0
    },
    {
      "name": "duplicate_order_ids",
      "pass": true,
      "violations": 0
    },
    {
      "name": "orders_without_customer",
      "pass": true,
      "violations": 0
    },
    {
      "name": "tickets_without_customer",
      "pass": true,
      "violations": 0
    },
    {
      "name": "requests_without_customer",
      "pass": true,
      "violations": 0
    },
    {
      "name": "requests_without_order",
      "pass": true,
      "violations": 0
    },
    {
      "name": "payment_issues_without_order",
      "pass": true,
      "violations": 0
    },
    {
      "name": "duplicate_relationship_groups",
      "pass": true,
      "violations": 0
    }
  ]
}
```

</details>

## Business Rules

Status: `pass`; rule compliance rate: 1.0000

## Intent Detection

```json
{
  "count": 88,
  "accuracy": 1.0,
  "macro_precision": 1.0,
  "macro_recall": 1.0,
  "macro_f1": 1.0,
  "per_label": {
    "cancel_order": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 9
    },
    "damaged_product": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 4
    },
    "order_tracking": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 9
    },
    "payment_issue": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 5
    },
    "policy_question": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 25
    },
    "refund_request": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 11
    },
    "replacement_request": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 8
    },
    "return_request": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
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
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "damaged_product": {
      "cancel_order": 0,
      "damaged_product": 4,
      "order_tracking": 0,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 0,
      "ticket_status": 0,
      "warranty_claim": 0
    },
    "order_tracking": {
      "cancel_order": 0,
      "damaged_product": 0,
      "order_tracking": 9,
      "payment_issue": 0,
      "policy_question": 0,
      "refund_request": 0,
      "replacement_request": 0,
      "return_request": 0,
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

Status: `completed`.

<details>
<summary>Detailed results</summary>

```json
{
  "count": 7,
  "top_1": 0.7142857142857143,
  "top_3": 1.0,
  "mrr": 0.8333333333333333,
  "no_result_rate": 0.0,
  "per_policy_top_3": {
    "faq.md": 1.0,
    "payment_policy.md": 1.0,
    "refund_policy.md": 1.0,
    "return_policy.md": 1.0,
    "shipping_policy.md": 1.0,
    "support_guidelines.md": 1.0,
    "warranty_policy.md": 1.0
  },
  "p50_latency_seconds": 2.527822299998661,
  "p95_latency_seconds": 11.337657399999443,
  "cases": [
    {
      "id": "rag-refund",
      "expected_sources": [
        "refund_policy.md"
      ],
      "retrieved_sources": [
        "refund_policy.md",
        "warranty_policy.md",
        "return_policy.md"
      ],
      "latency_seconds": 11.337657399999443
    },
    {
      "id": "rag-return",
      "expected_sources": [
        "return_policy.md"
      ],
      "retrieved_sources": [
        "return_policy.md",
        "faq.md",
        "faq.md"
      ],
      "latency_seconds": 2.5085404999990715
    },
    {
      "id": "rag-warranty",
      "expected_sources": [
        "warranty_policy.md"
      ],
      "retrieved_sources": [
        "warranty_policy.md",
        "warranty_policy.md",
        "warranty_policy.md"
      ],
      "latency_seconds": 2.574417600000743
    },
    {
      "id": "rag-shipping",
      "expected_sources": [
        "shipping_policy.md"
      ],
      "retrieved_sources": [
        "shipping_policy.md",
        "shipping_policy.md",
        "shipping_policy.md"
      ],
      "latency_seconds": 2.601645999995526
    },
    {
      "id": "rag-payment",
      "expected_sources": [
        "payment_policy.md"
      ],
      "retrieved_sources": [
        "payment_policy.md",
        "refund_policy.md",
        "payment_policy.md"
      ],
      "latency_seconds": 2.132841999999073
    },
    {
      "id": "rag-support",
      "expected_sources": [
        "support_guidelines.md"
      ],
      "retrieved_sources": [
        "shipping_policy.md",
        "support_guidelines.md",
        "faq.md"
      ],
      "latency_seconds": 2.158475999996881
    },
    {
      "id": "rag-faq",
      "expected_sources": [
        "faq.md"
      ],
      "retrieved_sources": [
        "shipping_policy.md",
        "shipping_policy.md",
        "faq.md"
      ],
      "latency_seconds": 2.527822299998661
    }
  ]
}
```

</details>

## Grounding and Citations

Status: `completed`.

<details>
<summary>Detailed results</summary>

```json
{
  "count": 6,
  "citation_validity": 1.0,
  "unsupported_citation_count": 0,
  "no_evidence_safety_pass_rate": null,
  "grounding_pass_rate": 0.6666666666666666,
  "llm_judge": "configured"
}
```

</details>

## Orchestrator

Status: `completed`.

<details>
<summary>Detailed results</summary>

```json
{
  "count": 5,
  "exact_path_accuracy": 1.0,
  "required_tool_recall": 1.0,
  "unnecessary_tool_rate": 0.0,
  "missing_critical_tool_rate": 0.0,
  "expected_paths": [
    [
      "rag_policy",
      "order_graph"
    ],
    [
      "rag_policy",
      "order_graph"
    ],
    [
      "rag_policy",
      "order_graph"
    ],
    [
      "rag_policy",
      "order_graph"
    ],
    [
      "order_graph",
      "rag_policy",
      "action"
    ]
  ],
  "actual_paths": [
    [
      "rag_policy",
      "order_graph"
    ],
    [
      "rag_policy",
      "order_graph"
    ],
    [
      "rag_policy",
      "order_graph"
    ],
    [
      "rag_policy",
      "order_graph"
    ],
    [
      "order_graph",
      "rag_policy",
      "action"
    ]
  ]
}
```

</details>

## Confirmation Safety

Status: `failed`.

<details>
<summary>Detailed results</summary>

```json
{
  "checks": [
    {
      "name": "refund_not_before_confirmation",
      "pass": true
    },
    {
      "name": "confirmation_ownership",
      "pass": true
    },
    {
      "name": "refund_executes_once",
      "pass": false
    },
    {
      "name": "duplicate_confirmation_no_replay",
      "pass": true
    },
    {
      "name": "return_not_before_confirmation",
      "pass": true
    },
    {
      "name": "unrelated_not_confirmation",
      "pass": true
    },
    {
      "name": "return_executes_once",
      "pass": false
    },
    {
      "name": "replacement_not_before_confirmation",
      "pass": true
    },
    {
      "name": "replacement_executes_once",
      "pass": false
    },
    {
      "name": "warranty_not_before_confirmation",
      "pass": true
    },
    {
      "name": "warranty_executes_once",
      "pass": false
    },
    {
      "name": "expired_confirmation_rejected",
      "pass": true
    },
    {
      "name": "valid_confirmation_executes",
      "pass": true
    },
    {
      "name": "payment_not_before_confirmation",
      "pass": true
    }
  ],
  "pass_rate": 0.7142857142857143
}
```

</details>

## Actions

Status: `completed`.

<details>
<summary>Detailed results</summary>

```json
{
  "count": 6,
  "action_accuracy": 0.16666666666666666,
  "cases": [
    {
      "expected": {
        "action": "refund_request_created",
        "status": "executed"
      },
      "actual": {
        "action": null,
        "status": "failed"
      }
    },
    {
      "expected": {
        "action": "return_request_created",
        "status": "executed"
      },
      "actual": {
        "action": "return_denied",
        "status": "failed"
      }
    },
    {
      "expected": {
        "action": "replacement_request_created",
        "status": "executed"
      },
      "actual": {
        "action": "replacement_denied",
        "status": "failed"
      }
    },
    {
      "expected": {
        "action": "warranty_claim_created",
        "status": "executed"
      },
      "actual": {
        "action": "warranty_claim_denied",
        "status": "failed"
      }
    },
    {
      "expected": {
        "action": "order_cancelled",
        "status": "executed"
      },
      "actual": {
        "action": "order_cancelled",
        "status": "executed"
      }
    },
    {
      "expected": {
        "action": "ticket_created",
        "status": "executed"
      },
      "actual": {
        "action": null,
        "status": "failed"
      }
    }
  ],
  "denied_checks": [
    {
      "name": "refund_outside_window_denied",
      "pass": true
    },
    {
      "name": "shipped_cancel_denied",
      "pass": true
    }
  ]
}
```

</details>

## API

Status: `pass`.

<details>
<summary>Detailed results</summary>

```json
{
  "checks": [
    {
      "name": "registration",
      "pass": true,
      "actual": [
        201,
        201
      ]
    },
    {
      "name": "login",
      "pass": true,
      "actual": [
        200,
        200
      ]
    },
    {
      "name": "identity",
      "pass": true,
      "actual": 200
    },
    {
      "name": "orders",
      "pass": true,
      "actual": 200
    },
    {
      "name": "tickets",
      "pass": true,
      "actual": 200
    },
    {
      "name": "requests",
      "pass": true,
      "actual": 200
    }
  ],
  "pass_rate": 1.0
}
```

</details>

## End-to-End Results

Status: `failed`.

<details>
<summary>Detailed results</summary>

```json
{
  "checks": [
    {
      "name": "service_requests_visible",
      "pass": false
    },
    {
      "name": "cancel_state_visible",
      "pass": true
    },
    {
      "name": "ticket_visible",
      "pass": false
    }
  ],
  "pass_rate": 0.3333333333333333
}
```

</details>

## Performance

Status: `completed`.

<details>
<summary>Detailed results</summary>

```json
{
  "endpoint": "/orders",
  "count": 20,
  "concurrency": 4,
  "p50_latency_seconds": 0.6966744999954244,
  "p95_latency_seconds": 0.7330376999962027,
  "error_rate": 0.0
}
```

</details>

## Failed Scenarios

- `grounding_case_4`: grounding expected `evidence-grounded answer or safe decline`, got `{'candidates': ['shipping_policy.md::shipping---delivery-policy::5', 'shipping_policy.md::shipping---delivery-policy::3', 'shipping_policy.md::shipping---delivery-policy::1', 'payment_policy.md::replacement---payment-policy::1'], 'accepted': [], 'invalid': [], 'supported': False, 'declined': True}`
- `grounding_case_5`: grounding expected `evidence-grounded answer or safe decline`, got `{'candidates': ['payment_policy.md::replacement---payment-policy::3', 'refund_policy.md::refund-policy::1', 'payment_policy.md::replacement---payment-policy::1', 'refund_policy.md::refund-policy::4'], 'accepted': [], 'invalid': [], 'supported': False, 'declined': True}`
- `action_case_1`: actions expected `{'action': 'refund_request_created', 'status': 'executed'}`, got `{'action': None, 'status': 'failed'}`
- `action_case_2`: actions expected `{'action': 'return_request_created', 'status': 'executed'}`, got `{'action': 'return_denied', 'status': 'failed'}`
- `action_case_3`: actions expected `{'action': 'replacement_request_created', 'status': 'executed'}`, got `{'action': 'replacement_denied', 'status': 'failed'}`
- `action_case_4`: actions expected `{'action': 'warranty_claim_created', 'status': 'executed'}`, got `{'action': 'warranty_claim_denied', 'status': 'failed'}`
- `action_case_6`: actions expected `{'action': 'ticket_created', 'status': 'executed'}`, got `{'action': None, 'status': 'failed'}`
- `refund_executes_once`: confirmation expected `pass`, got `failed`
- `return_executes_once`: confirmation expected `pass`, got `failed`
- `replacement_executes_once`: confirmation expected `pass`, got `failed`
- `warranty_executes_once`: confirmation expected `pass`, got `failed`
- `service_requests_visible`: end_to_end expected `pass`, got `failed`
- `ticket_visible`: end_to_end expected `pass`, got `failed`

## Skipped Checks

- Context-dependent confirmation fixtures excluded from stateless intent scoring: hold-0078, hold-0079.

## Recommendations

- Run graph/RAG/privacy suites only against isolated test services and controlled records.
- Treat failed intent classes in the detailed confusion matrix as routing work, not as LLM score tuning.
