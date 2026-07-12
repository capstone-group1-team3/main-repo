from __future__ import annotations
from eval.scoring import safe_rate


def score(checks: list[dict]):
    """Privacy is an independent hard gate; every controlled check must pass."""
    passed = sum(bool(check.get("pass")) for check in checks)
    rate = safe_rate(passed, len(checks))
    return {"count": len(checks), "privacy_pass_rate": rate, "pass": rate == 1.0 if rate is not None else None}
