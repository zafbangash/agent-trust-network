# tests/test_canonical.py
from agentframe.canonical import canonical_bytes

def test_key_order_does_not_matter():
    assert canonical_bytes({"b": 1, "a": 2}) == canonical_bytes({"a": 2, "b": 1})

def test_compact_and_sorted():
    assert canonical_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'

def test_unicode_preserved():
    assert canonical_bytes({"t": "café"}) == '{"t":"café"}'.encode("utf-8")

def test_nan_rejected():
    import pytest
    with pytest.raises(ValueError):
        canonical_bytes({"x": float("nan")})
