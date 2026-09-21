# src/provider/router.py
"""One dispatcher, many faucets.

Every capability is a self-contained descriptor (name, grant, validator, handler).
The router opens exactly the faucet named by the message's `capability` header and
runs the same trust pipeline in front of all of them. Adding a capability is
registering a `Capability`; it is not writing a new endpoint.

The `capability` header is the faucet selector, in the sense SIP's method line
selects a handler: routing is declared by the message, enforcement is built in.

Pipeline order per request:
  header -> faucet lookup -> known-sender -> verify (auth+authz+replay)
  -> inbound injection wall -> schema validate -> handle -> signed receipt.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from flask import Flask, jsonify, request

from agentframe import identity as idmod
from agentframe import injection
from agentframe import message as m
from agentframe.replay import ReplayGuard


@dataclass(frozen=True)
class Capability:
    """A faucet. `validate(payload)->(ok,reason)`; `handle(payload)->dict` of
    receipt fields (status/ts are added by the router). `untrusted_fields` names
    the free-text payload keys that reach a reasoning core and must pass the
    injection wall."""
    name: str
    grant: str
    validate: Callable[[dict], tuple[bool, str]]
    handle: Callable[[dict], dict]
    untrusted_fields: tuple[str, ...] = field(default_factory=tuple)


def create_router_app(orion: "idmod.Identity", root_pub_b64: str,
                      known_agents: dict[str, str],
                      capabilities) -> Flask:
    """capabilities: an iterable of Capability (or a name->Capability dict)."""
    registry = (capabilities if isinstance(capabilities, dict)
                else {c.name: c for c in capabilities})
    app = Flask(__name__)
    guard = ReplayGuard()

    def reject(reason: str, code: int):
        return jsonify(m.sign_envelope(
            orion, {"status": "error", "reason": reason, "ts": int(time.time())})), code

    @app.post("/capability")
    def capability():
        msg = request.get_json(silent=True)
        if not isinstance(msg, dict):
            return reject("malformed", 400)

        cap = registry.get(msg.get("capability"))
        if cap is None:
            return reject("unknown_capability", 400)

        sender_pub = known_agents.get(msg.get("from"))
        if sender_pub is None:
            return reject("unknown_sender", 403)

        ok, reason = m.verify_request(
            msg, sender_pub, root_pub_b64, cap.grant, guard, now=int(time.time()))
        if not ok:
            code = 400 if reason in ("bad_version", "malformed") else 403
            return reject(reason, code)

        payload = msg["payload"]

        iok, ireason = injection.scan_fields(payload, cap.untrusted_fields)
        if not iok:
            return reject(ireason, 400)

        valid, vreason = cap.validate(payload)
        if not valid:
            return reject(vreason, 400)

        try:
            result = cap.handle(payload)
        except Exception as e:  # handler-internal failure (e.g. model down)
            return reject(f"capability_error:{type(e).__name__}", 502)

        receipt = {"status": "ok", "ts": int(time.time())}
        receipt.update(result)
        return jsonify(m.sign_envelope(orion, receipt))

    return app
