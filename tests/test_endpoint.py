# tests/test_endpoint.py
from agentframe import identity as idmod
from agentframe import message as m
from agentframe import passport as pp
from provider.endpoint import create_app

GRANT = "publish@blog.example.com"

def _world(tmp_path):
    root = idmod.Identity.generate()
    orion = idmod.Identity.generate()
    Alice = idmod.Identity.generate()
    passport = pp.issue(root, Alice.agent_id, "alice", [GRANT], issued=0, expires=10**12)
    app = create_app(
        orion=orion,
        root_pub_b64=root.pub_b64,
        known_agents={Alice.agent_id: Alice.pub_b64},
        posts_dir=str(tmp_path / "posts"),
        site_dir=str(tmp_path / "site"),
    )
    return app, root, orion, Alice, passport

def _req(Alice, passport, ts):
    return m.build_request(Alice, to="orion", capability="publish_blog",
                           payload={"title": "Hello", "markdown": "Body **x**"},
                           passport=passport, ts=ts)

def test_valid_request_publishes_and_returns_signed_receipt(tmp_path):
    app, root, orion, Alice, passport = _world(tmp_path)
    import time
    msg = _req(Alice, passport, ts=int(time.time()))
    client = app.test_client()
    resp = client.post("/capability", json=msg)
    assert resp.status_code == 200
    receipt = resp.get_json()
    assert receipt["status"] == "ok"
    assert receipt["url"].startswith("/posts/")
    assert m.verify_envelope(orion.pub_b64, receipt) is True

def test_unknown_sender_rejected(tmp_path):
    app, root, orion, Alice, passport = _world(tmp_path)
    import time
    stranger = idmod.Identity.generate()
    msg = m.build_request(stranger, to="orion", capability="publish_blog",
                          payload={"title": "H", "markdown": "B"},
                          passport=passport, ts=int(time.time()))
    resp = app.test_client().post("/capability", json=msg)
    assert resp.status_code == 403
    assert resp.get_json()["reason"] == "unknown_sender"

def test_tampered_request_rejected(tmp_path):
    app, root, orion, Alice, passport = _world(tmp_path)
    import time
    msg = _req(Alice, passport, ts=int(time.time()))
    msg["payload"]["markdown"] = "EVIL"
    resp = app.test_client().post("/capability", json=msg)
    assert resp.status_code == 403
    assert resp.get_json()["reason"] == "bad_signature"

def test_replay_rejected(tmp_path):
    app, root, orion, Alice, passport = _world(tmp_path)
    import time
    msg = _req(Alice, passport, ts=int(time.time()))
    client = app.test_client()
    assert client.post("/capability", json=msg).status_code == 200
    resp = client.post("/capability", json=msg)
    assert resp.status_code == 403
    assert resp.get_json()["reason"] == "replay_or_stale"
