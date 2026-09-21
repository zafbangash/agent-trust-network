# src/requester/client.py
from __future__ import annotations

import time

import requests

from agentframe import identity as idmod
from agentframe import message as m


def publish_via_orion(endpoint_url: str, sender: "idmod.Identity", payload: dict,
                      passport: dict, orion_pub_b64: str,
                      timeout: int = 30) -> tuple[dict, bool]:
    """Send a signed publish_blog intent to Orion. Returns (receipt, receipt_authentic)."""
    msg = m.build_request(sender, to="orion", capability="publish_blog",
                          payload=payload, passport=passport, ts=int(time.time()))
    resp = requests.post(endpoint_url, json=msg, timeout=timeout)
    receipt = resp.json()
    authentic = m.verify_envelope(orion_pub_b64, receipt)
    return receipt, authentic
