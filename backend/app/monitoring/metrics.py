"""Bounded-cardinality Prometheus metrics for FusionMind.

Labels deliberately exclude identifiers, messages, URLs, Cypher, and evidence.
"""
from prometheus_client import Counter, Gauge, Histogram

# HTTP
HTTP_REQUESTS = Counter(
    "fusionmind_http_requests_total", "Completed HTTP requests",
    ["method", "route", "status_class"],
)
HTTP_DURATION = Histogram(
    "fusionmind_http_request_duration_seconds", "HTTP request duration",
    ["method", "route"],
    buckets=(.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30),
)
HTTP_INFLIGHT = Gauge(
    "fusionmind_http_inflight_requests", "Currently in-flight HTTP requests"
)
HTTP_ERRORS = Counter(
    "fusionmind_http_errors_total", "HTTP errors",
    ["method", "route", "error_category"],
)

# Detection
INTENT_DETECTED = Counter(
    "fusionmind_intent_detections_total", "Intent detection results",
    ["intent", "outcome"],
)
INTENT_DURATION = Histogram(
    "fusionmind_intent_detection_duration_seconds", "Intent detection duration",
    ["outcome"],
)
INTENT_FALLBACK = Counter(
    "fusionmind_intent_fallback_total", "LLM intent fallback attempts", ["outcome"]
)
ENTITY_DURATION = Histogram(
    "fusionmind_entity_extraction_duration_seconds", "Entity extraction duration",
    ["outcome"],
)
ENTITY_FAILURES = Counter(
    "fusionmind_entity_extraction_failures_total", "Entity extraction failures",
    ["error_category"],
)
MISSING_SLOTS = Counter(
    "fusionmind_missing_required_slots_total", "Missing bounded entity slots", ["slot"]
)

# Orchestrator and tools
ORCHESTRATOR_DURATION = Histogram(
    "fusionmind_orchestrator_duration_seconds", "Orchestrator duration", ["outcome"]
)
ORCHESTRATOR_COMPLETIONS = Counter(
    "fusionmind_orchestrator_completions_total", "Orchestrator completion outcomes",
    ["outcome"],
)
LOOP_ITERATIONS = Histogram(
    "fusionmind_orchestrator_iterations", "Iterations per orchestrator run", ["outcome"],
    buckets=(0, 1, 2, 3, 4, 5, 6, 8, 10),
)
TOOLS_CALLED = Counter(
    "fusionmind_tool_calls_total", "Tool calls", ["tool", "outcome"]
)
TOOL_DURATION = Histogram(
    "fusionmind_tool_duration_seconds", "Tool execution duration", ["tool", "outcome"]
)
NO_PROGRESS_STOPS = Counter(
    "fusionmind_no_progress_stops_total", "No-progress loop stops"
)

# Retrieval
RAG_REQUESTS = Counter(
    "fusionmind_rag_retrieval_total", "RAG retrieval requests", ["mode", "outcome"]
)
RAG_DURATION = Histogram(
    "fusionmind_rag_retrieval_duration_seconds", "RAG retrieval duration", ["mode"]
)
RAG_RESULT_COUNT = Histogram(
    "fusionmind_rag_result_count", "Retrieved result count", ["mode"],
    buckets=(0, 1, 2, 3, 4, 5, 10, 20),
)
RAG_EMPTY = Counter(
    "fusionmind_rag_empty_evidence_total", "Retrievals with no sufficient evidence", ["mode"]
)
RAG_FAILURES = Counter(
    "fusionmind_rag_failures_total", "RAG failures", ["error_category"]
)

# Neo4j
NEO4J_QUERIES = Counter(
    "fusionmind_neo4j_queries_total", "Neo4j operations",
    ["operation", "query_type", "outcome"],
)
NEO4J_DURATION = Histogram(
    "fusionmind_neo4j_query_duration_seconds", "Neo4j operation duration",
    ["operation", "query_type", "outcome"],
)
NEO4J_FAILURES = Counter(
    "fusionmind_neo4j_failures_total", "Neo4j failures",
    ["operation", "error_category"],
)

# Actions
ACTION_ATTEMPTS = Counter(
    "fusionmind_action_attempts_total", "Action attempts", ["action"]
)
ACTION_DURATION = Histogram(
    "fusionmind_action_duration_seconds", "Action duration", ["action", "outcome"]
)
ACTION_RESULTS = Counter(
    "fusionmind_action_results_total", "Action results", ["action", "outcome"]
)

# Planner/routing
PLANNER_CALLS = Counter("fusionmind_planner_calls_total", "LLM planner calls")
PLANNER_FAILURES = Counter("fusionmind_planner_failures_total", "Planner failures")
PLANNER_TIMEOUTS = Counter("fusionmind_planner_timeouts_total", "Planner timeouts")
PLANNER_LATENCY = Histogram("fusionmind_planner_duration_seconds", "Planner duration")
PLANNER_CONFIDENCE = Histogram(
    "fusionmind_planner_confidence", "Planner confidence", buckets=(0, .25, .5, .75, .9, 1)
)
FAST_PATH_USED = Counter("fusionmind_fast_path_total", "Fast-path selections")
FALLBACK_USED = Counter("fusionmind_fixed_fallback_total", "Fixed-routing fallbacks")
DECISION_CORRECTIONS = Counter(
    "fusionmind_decision_corrections_total", "Planner corrections", ["type"]
)

# Interaction/safety
CONFIRMATION_REQUESTED = Counter("fusionmind_confirmation_requested_total", "Confirmations requested")
CONFIRMATION_ACCEPTED = Counter("fusionmind_confirmation_accepted_total", "Confirmations accepted")
CONFIRMATION_DECLINED = Counter("fusionmind_confirmation_declined_total", "Confirmations declined")
CONFIRMATION_EXPIRED = Counter("fusionmind_confirmation_expired_total", "Confirmations expired")
CLARIFICATION_ASKED = Counter(
    "fusionmind_clarification_total", "Clarifications requested", ["reason"]
)
UNSAFE_ACTION_PROPOSALS = Counter(
    "fusionmind_unsafe_action_total", "Blocked unsafe actions", ["reason"]
)
ELIGIBILITY_DENIALS = Counter(
    "fusionmind_eligibility_denials_total", "Eligibility denials", ["action"]
)
GROUNDING_ANSWERED = Counter("fusionmind_grounding_answered_total", "Policy answers evaluated")
GROUNDING_PASSED = Counter("fusionmind_grounding_passed_total", "Policy answers with valid citations")
GROUNDING_SOURCE_MISMATCH = Counter(
    "fusionmind_grounding_source_mismatch_total", "Unsupported citation attempts"
)
TASK_COMPLETED = Counter("fusionmind_tasks_completed_total", "Completed actions")

# Compatibility aliases for existing imports. They point to the same collectors.
REQUEST_LATENCY = HTTP_DURATION
REQUESTS_TOTAL = HTTP_REQUESTS
INFLIGHT = HTTP_INFLIGHT
ACTION_EXECUTED = ACTION_RESULTS
ACTION_FAILED = ACTION_RESULTS
REPEATED_DECISIONS = TOOLS_CALLED
