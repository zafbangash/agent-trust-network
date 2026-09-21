# tests/test_message.py
from agentframe import identity as idmod
from agentframe import message as m
from agentframe import passport as pp
from agentframe.replay import ReplayGuard

GRANT = "publish@blog.example.com"

def _world():
    root = idmod.Identity.generate()
    sender = idmod.Identity.generate()
    passport = pp.issue(root, sender.agent_id, "alice", [GRANT],
                        issued=0, expires=10_000)
    return root, sender, passport

def _msg(sender, passport, ts=1000):
    return m.build_request(sender, to="orion", capability="publish_blog",
                           payload={"title": "Hi", "markdown": "Body"},
                           passport=passport, ts=ts)

def test_valid_request_verifies():
    root, sender, passport = _world()
    msg = _msg(sender, passport)
    ok, reason = m.verify_request(msg, sender.pub_b64, root.pub_b64, GRANT,
                                  ReplayGuard(), now=1000)
    assert (ok, reason) == (True, "ok")

def test_tampered_payload_fails_signature():
    root, sender, passport = _world()
    msg = _msg(sender, passport)
    msg["payload"]["markdown"] = "EVIL"
    ok, reason = m.verify_request(msg, sender.pub_b64, root.pub_b64, GRANT,
                                  ReplayGuard(), now=1000)
    assert (ok, reason) == (False, "bad_signature")

def test_replay_rejected_on_second_use():
    root, sender, passport = _world()
    msg = _msg(sender, passport)
    g = ReplayGuard()
    assert m.verify_request(msg, sender.pub_b64, root.pub_b64, GRANT, g, now=1000)[0]
    ok, reason = m.verify_request(msg, sender.pub_b64, root.pub_b64, GRANT, g, now=1000)
    assert (ok, reason) == (False, "replay_or_stale")

def test_missing_grant_unauthorized():
    root, sender, passport = _world()
    msg = _msg(sender, passport)
    ok, reason = m.verify_request(msg, sender.pub_b64, root.pub_b64,
                                  "delete@blog.example.com", ReplayGuard(), now=1000)
    assert (ok, reason) == (False, "unauthorized")

def test_pubkey_not_matching_from_is_id_mismatch():
    root, sender, passport = _world()
    other = idmod.Identity.generate()
    msg = _msg(sender, passport)
    ok, reason = m.verify_request(msg, other.pub_b64, root.pub_b64, GRANT,
                                  ReplayGuard(), now=1000)
    assert (ok, reason) == (False, "id_mismatch")

def test_signed_receipt_roundtrip():
    orion = idmod.Identity.generate()
    receipt = m.sign_envelope(orion, {"status": "ok", "url": "/posts/x.html", "ts": 5})
    assert m.verify_envelope(orion.pub_b64, receipt) is True
    receipt["url"] = "/posts/evil.html"
    assert m.verify_envelope(orion.pub_b64, receipt) is False
