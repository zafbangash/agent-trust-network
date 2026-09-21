#!/usr/bin/env python3
"""check_node.py — end-to-end check of a running provider.

Defaults to the local provider. Point it at a relay URL to test cross-network.

  python check_node.py                                      # local
  python check_node.py https://relay.example.com/capability # through the relay

Key/passport paths can be overridden with AGENTFRAME_KEY / AGENTFRAME_PASSPORT.
"""
import json
import os
import sys

sys.path.insert(0, "src")
from agentframe.identity import Identity        # noqa: E402
from requester.ask_client import ask_via_orion  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8081/capability"
PROMPT = sys.argv[2] if len(sys.argv) > 2 else "Confirm you are reachable and compute 7*6."
KEY = os.environ.get("AGENTFRAME_KEY", "keys/requester.pem")
PASSPORT = os.environ.get("AGENTFRAME_PASSPORT", "keys/requester_passport.json")

cfg = json.load(open("node_config.json"))
sender = Identity.load(KEY)
passport = json.load(open(PASSPORT))

print(f"[client] POST {URL}")
print(f"[client] as {sender.agent_id} (grants: {', '.join(passport.get('grants', []))})")
receipt, authentic = ask_via_orion(URL, sender, PROMPT, passport,
                                   cfg["orion_pub_b64"], num_predict=64)
print(f"[client] status={receipt.get('status')} receipt_authentic={authentic}")
if receipt.get("status") != "ok":
    print(f"[client] reason={receipt.get('reason')}")
else:
    print(f"[client] model={receipt.get('model')}")
    print(f"[client] ANSWER: {receipt.get('answer')!r}")
ok = authentic and receipt.get("status") == "ok" and receipt.get("answer")
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
