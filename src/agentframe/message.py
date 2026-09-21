# src/agentframe/message.py
from __future__ import annotations

import base64
import os

from . import identity as idmod
from .canonical import canonical_bytes
from .passport import verify as verify_passport
from .replay import ReplayGuard


def _new_nonce() -> str:
    return base64.urlsafe_b64encode(os.urandom(16)).decode("ascii").rstrip("=")


def sign_envelope(signer: "idmod.Identity", body: dict) -> dict:
    """Return body + a 'sig' over canonical(body)."""
    out = dict(body)
    out["sig"] = signer.sign(canonical_bytes(body))
    return out


def verify_envelope(pub_b64: str, env: dict) -> bool:
    body = {k: v for k, v in env.items() if k != "sig"}
    return idmod.verify(pub_b64, canonical_bytes(body), env.get("sig", ""))


def build_request(sender: "idmod.Identity", to: str, capability: str,
                  payload: dict, passport: dict, ts: int,
                  nonce: str | None = None) -> dict:
    body = {
        "v": 1,
        "from": sender.agent_id,
        "to": to,
        "capability": capability,
        "ts": ts,
        "nonce": nonce or _new_nonce(),
        "payload": payload,
        "passport": passport,
    }
    return sign_envelope(sender, body)


def verify_request(msg: dict, sender_pub_b64: str, root_pub_b64: str,
                   required_grant: str, guard: ReplayGuard,
                   now: int) -> tuple[bool, str]:
    """Spec §8 verification flow. Returns (ok, reason); reason == 'ok' on success.

    Order matters: cheap structural checks, then signature (authentic), then
    passport (authorized), then replay LAST so only authentic+authorized
    messages consume nonce space.
    """
    try:
        if msg.get("v") != 1:
            return False, "bad_version"
        if msg["from"] != idmod.agent_id_from_pubkey(idmod._unb64(sender_pub_b64)):
            return False, "id_mismatch"
        if not verify_envelope(sender_pub_b64, msg):
            return False, "bad_signature"
        if not verify_passport(msg["passport"], root_pub_b64, msg["from"],
                               required_grant, now):
            return False, "unauthorized"
        if not guard.check_and_record(msg["nonce"], msg["ts"], now):
            return False, "replay_or_stale"
        return True, "ok"
    except (KeyError, TypeError):
        return False, "malformed"
