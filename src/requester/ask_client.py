# src/requester/ask_client.py
from __future__ import annotations

import time

import requests

from agentframe import identity as idmod
from agentframe import message as m


def ask_via_orion(endpoint_url: str, sender: "idmod.Identity", prompt: str,
                  passport: dict, orion_pub_b64: str, *,
                  num_predict: int = 256, timeout: int = 130) -> tuple[dict, bool]:
    """Send a signed ask_qwen intent to Orion. Returns (receipt, receipt_authentic)."""
    payload = {"prompt": prompt, "num_predict": num_predict}
    msg = m.build_request(sender, to="orion", capability="ask_qwen",
                          payload=payload, passport=passport, ts=int(time.time()))
    resp = requests.post(endpoint_url, json=msg, timeout=timeout)
    receipt = resp.json()
    authentic = m.verify_envelope(orion_pub_b64, receipt)
    return receipt, authentic
