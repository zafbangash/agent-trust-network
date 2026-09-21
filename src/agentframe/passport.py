# src/agentframe/passport.py
from __future__ import annotations

from . import identity as idmod
from .canonical import canonical_bytes

PASSPORT_FIELDS = ("agent", "principal", "grants", "issued", "expires")


def _payload(p: dict) -> dict:
    return {k: p[k] for k in PASSPORT_FIELDS}


def issue(root: "idmod.Identity", agent_id: str, principal: str,
          grants: list[str], issued: int, expires: int) -> dict:
    body = {
        "agent": agent_id,
        "principal": principal,
        "grants": list(grants),
        "issued": issued,
        "expires": expires,
    }
    body["sig"] = root.sign(canonical_bytes(body))
    return body


def verify(passport: dict, root_pub_b64: str, agent_id: str,
           required_grant: str, now: int) -> bool:
    try:
        if passport["agent"] != agent_id:
            return False
        if not (passport["issued"] <= now <= passport["expires"]):
            return False
        if required_grant not in passport["grants"]:
            return False
        return idmod.verify(
            root_pub_b64, canonical_bytes(_payload(passport)), passport["sig"]
        )
    except (KeyError, TypeError):
        return False
