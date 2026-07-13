"""Progress detector using state fingerprinting."""
import hashlib, json
from typing import Any

def state_fingerprint(state: Any) -> str:
    relevant = {
        "intent": state.intent,
        "has_policy": state.policy_evidence is not None,
        "has_order": state.order_data is not None,
        "ownership": state.ownership_ok,
        "has_action": state.action_result is not None,
        "tools": state.tools_used,
        "confirm_req": state.confirmation_required,
        "confirm_recv": state.confirmation_received,
        "entities": state.entities,
    }
    blob = json.dumps(relevant, sort_keys=True, default=str)
    return hashlib.md5(blob.encode()).hexdigest()[:12]

def no_progress(state: Any) -> bool:
    if len(state.state_fingerprints) < 2:
        return False
    return state.state_fingerprints[-1] == state.state_fingerprints[-2]
