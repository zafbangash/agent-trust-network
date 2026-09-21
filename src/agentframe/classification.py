# src/agentframe/classification.py
from __future__ import annotations

from enum import Enum


class Tier(str, Enum):
    PUBLIC = "PUBLIC"
    SHAREABLE = "SHAREABLE"
    PRIVATE = "PRIVATE"
    NEVER = "NEVER"


class NeverClassError(Exception):
    """Raised on any attempt to serialize/transmit NEVER-class material."""


class Classified:
    """A value tagged with a trust tier. NEVER-class values cannot be serialized."""

    def __init__(self, value, tier: Tier):
        object.__setattr__(self, "_value", value)
        object.__setattr__(self, "_tier", tier)

    @property
    def tier(self) -> Tier:
        return self._tier

    def reveal(self):
        """Local, in-process access only. Never call inside a serialization path."""
        return self._value

    def serialize(self):
        if self._tier is Tier.NEVER:
            raise NeverClassError("NEVER-class material cannot be serialized")
        return self._value

    def __repr__(self) -> str:
        return f"<Classified tier={self._tier.value} (value hidden)>"


def assert_transmittable(obj) -> None:
    """Wall: raise NeverClassError if any NEVER-class value is in an outbound payload."""

    def walk(o):
        if isinstance(o, Classified):
            if o.tier is Tier.NEVER:
                raise NeverClassError("NEVER-class material in outbound payload")
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                walk(v)

    walk(obj)
