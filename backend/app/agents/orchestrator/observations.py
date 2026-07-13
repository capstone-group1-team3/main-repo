"""Compact observation builder after tool calls."""
from __future__ import annotations
from datetime import date
from typing import Any

def build_order_observation(result: dict) -> dict:
    order = result.get("order_data") or {}
    if not result.get("ownership_ok", True):
        return {"tool":"order_graph","status":"ownership_failed","summary":{"ownership_verified":False}}
    days = None
    d = order.get("delivered_date")
    if d:
        try: days = (date.today() - date.fromisoformat(d)).days
        except: pass
    return {"tool":"order_graph","status":"success","summary":{
        "order_found": order.get("order_id") is not None,
        "ownership_verified": True,
        "order_status": order.get("status"),
        "delivered_days_ago": days,
        "item_count": len(order.get("items") or []),
    }}

def build_rag_observation(result: dict) -> dict:
    return {"tool":"rag_policy","status":"success","summary":{
        "chunks_retrieved": len(result.get("candidate_ids",[])),
        "top_source": (result.get("sources") or [None])[0],
    }}

def build_action_observation(result: dict) -> dict:
    action = result.get("action","")
    return {"tool":"action","status":"denied" if action.endswith("_denied") else "success",
            "summary":{"action":action,"request_id":result.get("request_id")}}

def build_error_observation(tool: str, exc: Exception) -> dict:
    return {"tool":tool,"status":"failed","error_type":type(exc).__name__,
            "retryable":"timeout" in type(exc).__name__.lower(),"summary":{}}
