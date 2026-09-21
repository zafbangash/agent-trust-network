# src/agentframe/canonical.py
import json

def canonical_bytes(obj: dict) -> bytes:
    """Deterministic UTF-8 encoding of a JSON object for signing/verifying.

    Sorted keys, compact separators, no NaN/Infinity. The same logical object
    always produces the same bytes, on any machine, in any language that follows
    the same rules.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
