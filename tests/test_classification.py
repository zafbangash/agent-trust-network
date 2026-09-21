# tests/test_classification.py
import pytest
from agentframe.classification import (
    Tier, Classified, NeverClassError, assert_transmittable,
)

def test_public_serializes():
    c = Classified("hello", Tier.PUBLIC)
    assert c.serialize() == "hello"

def test_never_refuses_to_serialize():
    c = Classified("SECRET_KEY", Tier.NEVER)
    with pytest.raises(NeverClassError):
        c.serialize()

def test_repr_hides_value():
    c = Classified("SECRET_KEY", Tier.NEVER)
    assert "SECRET_KEY" not in repr(c)
    assert "NEVER" in repr(c)

def test_assert_transmittable_walks_nested_structures():
    payload = {"ok": "x", "deep": [{"leak": Classified("k", Tier.NEVER)}]}
    with pytest.raises(NeverClassError):
        assert_transmittable(payload)

def test_assert_transmittable_passes_clean_payload():
    payload = {"ok": "x", "list": [1, 2, {"a": "b"}]}
    assert_transmittable(payload) is None
