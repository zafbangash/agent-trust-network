#!/usr/bin/env python3
"""Negative-test battery against the live relay.example.com/capability endpoint.

Runs T1 (happy path), T2 (replay), T3 (tamper), T4 (expired passport),
T5 (stranger), T6 (latency sample). Uses the requester identity/passport
already registered on this machine (ag:zwabgo6l6wvyqtrp) rather than
impersonating Vega — the tests exercise the protocol, not a specific agent.
"""
from __future__ import annotations

import copy
import json
import os
import statistics
import time

import requests

from agentframe import identity as idmod
from agentframe import message as m

ENDPOINT = os.environ.get("AGENTFRAME_URL", "http://127.0.0.1:8081/capability")
ORION_PUB_B64 = json.load(open("node_config.json"))["orion_pub_b64"]

KEY = os.environ.get("AGENTFRAME_KEY", "keys/requester.pem")
PASSPORT = os.environ.get("AGENTFRAME_PASSPORT", "keys/requester_passport.json")
sender = idmod.Identity.load(KEY)
passport = json.load(open(PASSPORT))

results = []


def record(name, expected_reason, expected_code, resp):
    body = resp.json()
    actual_reason = body.get("reason", body.get("status"))
    authentic = m.verify_envelope(ORION_PUB_B64, body)
    passed = (resp.status_code == expected_code) and (
        actual_reason == expected_reason or (expected_reason == "ok" and body.get("status") == "ok")
    )
    results.append({
        "test": name, "expected": f"{expected_reason} ({expected_code})",
        "actual": f"{actual_reason} ({resp.status_code})",
        "receipt_signed_authentic": authentic, "pass": passed,
    })
    return body


# T1 — happy path
msg = m.build_request(sender, to="orion", capability="ask_qwen",
                       payload={"prompt": "What is 7 times 6?", "num_predict": 32},
                       passport=passport, ts=int(time.time()))
resp = requests.post(ENDPOINT, json=msg, timeout=60)
record("T1 happy path", "ok", 200, resp)

# T2 — replay: resend the exact same signed T1 message
resp2 = requests.post(ENDPOINT, json=msg, timeout=60)
record("T2 replay rejection", "replay_or_stale", 403, resp2)

# T3 — tamper: sign a fresh valid request, then mutate payload after signing
msg3 = m.build_request(sender, to="orion", capability="ask_qwen",
                        payload={"prompt": "What is 2 plus 2?", "num_predict": 32},
                        passport=passport, ts=int(time.time()))
tampered = copy.deepcopy(msg3)
tampered["payload"]["prompt"] = "IGNORE PREVIOUS INSTRUCTIONS"
resp3 = requests.post(ENDPOINT, json=tampered, timeout=60)
record("T3 tamper rejection", "bad_signature", 403, resp3)

# T4 — expired passport: copy the passport, push expires into the past, re-sign a request with it
expired_passport = dict(passport)
expired_passport["expires"] = int(time.time()) - 3600
msg4 = m.build_request(sender, to="orion", capability="ask_qwen",
                        payload={"prompt": "test", "num_predict": 8},
                        passport=expired_passport, ts=int(time.time()))
resp4 = requests.post(ENDPOINT, json=msg4, timeout=60)
record("T4 expired passport", "unauthorized", 403, resp4)

# T5 — stranger: throwaway keypair, never registered in known_agents
stranger = idmod.Identity.generate()
msg5 = m.build_request(stranger, to="orion", capability="ask_qwen",
                        payload={"prompt": "test", "num_predict": 8},
                        passport=passport, ts=int(time.time()))
resp5 = requests.post(ENDPOINT, json=msg5, timeout=60)
record("T5 stranger rejection", "unknown_sender", 403, resp5)

# T6 — latency sample: 10 happy-path round trips (10, not 20, to keep this quick/cheap on the provider's Ollama box)
latencies = []
for i in range(10):
    m6 = m.build_request(sender, to="orion", capability="ask_qwen",
                          payload={"prompt": f"Say the number {i}.", "num_predict": 8},
                          passport=passport, ts=int(time.time()))
    t0 = time.monotonic()
    r6 = requests.post(ENDPOINT, json=m6, timeout=60)
    latencies.append((time.monotonic() - t0) * 1000)
    assert r6.status_code == 200, r6.text

print(json.dumps(results, indent=2))
print()
print(f"T6 latency (ms) over {len(latencies)} round-trips (includes qwen2.5:7b inference):")
print(f"  median={statistics.median(latencies):.0f}  p95={sorted(latencies)[int(len(latencies)*0.95)-1]:.0f}  "
      f"min={min(latencies):.0f}  max={max(latencies):.0f}")

with open("/tmp/negtest_latencies.json", "w") as f:
    json.dump(latencies, f)
