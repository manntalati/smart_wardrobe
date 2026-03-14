"""
Shared response helpers.
All endpoints return the same envelope: { data, error, meta }.
"""
from typing import Any, Optional


def ok(data: Any, meta: Optional[dict] = None) -> dict:
    return {"data": data, "error": None, "meta": meta or {}}
