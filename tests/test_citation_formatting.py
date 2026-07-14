"""Citation parsing and API-facing cleanup for supported bracket styles."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agents.response.response_formatter import citation_audit
from app.api.routes_chat import _CHUNK_ID_RE


def test_unicode_policy_citation_is_audited_and_removed_from_answer():
    chunk_id = "refund_policy.md::refund-policy::0"
    answer = f"Refunds are available within 14 days 【{chunk_id}】."

    citations, invalid = citation_audit(answer, [chunk_id])
    cleaned = _CHUNK_ID_RE.sub("", answer).strip()

    assert citations == [{"chunk_id": chunk_id}]
    assert invalid == []
    assert chunk_id not in cleaned
    assert cleaned == "Refunds are available within 14 days ."


def test_ascii_policy_citation_remains_supported():
    chunk_id = "faq.md::damaged-items::1"
    citations, invalid = citation_audit(f"Photo required [{chunk_id}].", [chunk_id])

    assert citations == [{"chunk_id": chunk_id}]
    assert invalid == []


def test_invalid_unicode_chunk_id_is_hidden_but_not_accepted():
    answer = "Unsupported claim 【made_up.md::section::9】."

    citations, invalid = citation_audit(answer, [])
    cleaned = _CHUNK_ID_RE.sub("", answer).strip()

    assert citations == []
    assert invalid == ["made_up.md::section::9"]
    assert "made_up.md" not in cleaned
