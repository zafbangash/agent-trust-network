# tests/test_passport.py
from agentframe import identity as idmod
from agentframe import passport as pp

def _setup():
    root = idmod.Identity.generate()
    agent = idmod.Identity.generate()
    return root, agent

def test_issue_then_verify_ok():
    root, agent = _setup()
    p = pp.issue(root, agent.agent_id, "alice",
                 ["publish@blog.example.com"], issued=1000, expires=9000)
    assert pp.verify(p, root.pub_b64, agent.agent_id,
                     "publish@blog.example.com", now=1500) is True

def test_verify_rejects_wrong_agent():
    root, agent = _setup()
    other = idmod.Identity.generate()
    p = pp.issue(root, agent.agent_id, "alice",
                 ["publish@blog.example.com"], issued=1000, expires=9000)
    assert pp.verify(p, root.pub_b64, other.agent_id,
                     "publish@blog.example.com", now=1500) is False

def test_verify_rejects_missing_grant():
    root, agent = _setup()
    p = pp.issue(root, agent.agent_id, "alice",
                 ["publish@blog.example.com"], issued=1000, expires=9000)
    assert pp.verify(p, root.pub_b64, agent.agent_id,
                     "delete@blog.example.com", now=1500) is False

def test_verify_rejects_expired():
    root, agent = _setup()
    p = pp.issue(root, agent.agent_id, "alice",
                 ["publish@blog.example.com"], issued=1000, expires=2000)
    assert pp.verify(p, root.pub_b64, agent.agent_id,
                     "publish@blog.example.com", now=5000) is False

def test_verify_rejects_forged_signature():
    root, agent = _setup()
    attacker = idmod.Identity.generate()
    p = pp.issue(root, agent.agent_id, "alice",
                 ["publish@blog.example.com"], issued=1000, expires=9000)
    # verify against the wrong root key
    assert pp.verify(p, attacker.pub_b64, agent.agent_id,
                     "publish@blog.example.com", now=1500) is False

def test_tampering_with_grants_breaks_signature():
    root, agent = _setup()
    p = pp.issue(root, agent.agent_id, "alice",
                 ["publish@blog.example.com"], issued=1000, expires=9000)
    p["grants"].append("delete@blog.example.com")
    assert pp.verify(p, root.pub_b64, agent.agent_id,
                     "delete@blog.example.com", now=1500) is False
