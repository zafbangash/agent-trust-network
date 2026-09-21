# tests/test_replay.py
from agentframe.replay import ReplayGuard

def test_fresh_unseen_nonce_accepted():
    g = ReplayGuard(window_s=300)
    assert g.check_and_record("n1", ts=1000, now=1000.0) is True

def test_same_nonce_rejected_second_time():
    g = ReplayGuard(window_s=300)
    assert g.check_and_record("n1", ts=1000, now=1000.0) is True
    assert g.check_and_record("n1", ts=1001, now=1001.0) is False

def test_stale_timestamp_rejected():
    g = ReplayGuard(window_s=300)
    assert g.check_and_record("n1", ts=1000, now=2000.0) is False

def test_future_timestamp_beyond_window_rejected():
    g = ReplayGuard(window_s=300)
    assert g.check_and_record("n1", ts=2000, now=1000.0) is False

def test_old_nonces_pruned_allowing_reuse_after_window():
    g = ReplayGuard(window_s=300)
    assert g.check_and_record("n1", ts=1000, now=1000.0) is True
    # far in the future: original nonce pruned, a brand-new fresh use is allowed
    assert g.check_and_record("n2", ts=5000, now=5000.0) is True
    assert "n1" not in g._seen
