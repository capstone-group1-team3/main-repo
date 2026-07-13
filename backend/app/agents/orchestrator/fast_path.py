"""Fast-path selector — skips planner for clear single-intent requests."""
import re
_MULTI_GOAL = re.compile(r'\b(and also|as well as|both|either|not sure|which should)\b', re.I)
_AMBIG_DMG  = re.compile(r'\b(damaged|broken)\b.{0,60}\b(not sure|should I|what should)\b', re.I)
_SENSITIVE  = {"refund_request","return_request","replacement_request",
               "cancel_order","warranty_claim","damaged_product"}

def should_use_fast_path(state) -> tuple[bool, str]:
    if state.confidence < 0.85:
        return False, f"low confidence ({state.confidence:.2f})"
    if _MULTI_GOAL.search(state.message):
        return False, "multi-goal markers"
    if _AMBIG_DMG.search(state.message):
        return False, "ambiguous damaged-product"
    if state.intent in _SENSITIVE and not state.entities.get("order_id") and state.order_data is None:
        return False, "sensitive action without order context"
    return True, f"clear request ({state.intent}, conf={state.confidence:.2f})"
