#!/usr/bin/env python3
"""Real benchmarks for the KYA paper's §5.2 [BENCHMARK PLACEHOLDER] markers.

Measures, on this machine's CPU:
  1. Ed25519 keypair generation rate
  2. Message sign / verify throughput for a ~1KB canonical request
  3. Full request-verification pipeline latency (freshness+nonce+signature+passport)
  4. Replay-cache latency and memory at 10^2 / 10^4 / 10^5 seen nonces
  5. In-process Phase-0 vertical-slice throughput (build -> verify -> mock execute -> receipt)

No numbers here are invented; anything that doesn't run is reported as a failure, not omitted.
"""
from __future__ import annotations

import json
import platform
import resource
import statistics
import time

from agentframe import identity as idmod
from agentframe import message as m
from agentframe import passport as p
from agentframe.canonical import canonical_bytes
from agentframe.replay import ReplayGuard

N_KEYGEN = 2000
N_SIGN_VERIFY = 5000
N_PIPELINE = 5000
N_E2E = 2000


def env_report() -> dict:
    cpu = "unknown"
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass
    import cryptography
    return {
        "cpu": cpu,
        "python": platform.python_version(),
        "cryptography_version": cryptography.__version__,
        "os": platform.platform(),
    }


def bench_keygen():
    t0 = time.perf_counter()
    for _ in range(N_KEYGEN):
        idmod.Identity.generate()
    elapsed = time.perf_counter() - t0
    return N_KEYGEN / elapsed, elapsed


def make_1kb_payload() -> dict:
    # pad a prompt so the canonical-encoded request body lands close to 1KB
    return {"prompt": "x" * 780, "num_predict": 256}


def bench_sign_verify():
    a = idmod.Identity.generate()
    payload = make_1kb_payload()
    passport = p.issue(idmod.Identity.generate(), a.agent_id, "root:bench",
                        ["ask@orion"], int(time.time()) - 10, int(time.time()) + 3600)
    body = {"v": 1, "from": a.agent_id, "to": "orion", "capability": "ask_qwen",
            "ts": int(time.time()), "nonce": "bench-nonce", "payload": payload,
            "passport": passport}
    body_bytes = canonical_bytes(body)
    actual_size = len(body_bytes)

    t0 = time.perf_counter()
    sigs = []
    for _ in range(N_SIGN_VERIFY):
        sigs.append(a.sign(body_bytes))
    sign_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    for sig in sigs:
        assert idmod.verify(a.pub_b64, body_bytes, sig)
    verify_elapsed = time.perf_counter() - t0

    return {
        "request_bytes": actual_size,
        "sign_ops_per_sec": N_SIGN_VERIFY / sign_elapsed,
        "verify_ops_per_sec": N_SIGN_VERIFY / verify_elapsed,
    }


def bench_pipeline():
    root = idmod.Identity.generate()
    agent = idmod.Identity.generate()
    passport = p.issue(root, agent.agent_id, "root:bench", ["ask@orion"],
                        int(time.time()) - 10, int(time.time()) + 3600)
    known_agents = {agent.agent_id: agent.pub_b64}
    guard = ReplayGuard()

    latencies = []
    for i in range(N_PIPELINE):
        msg = m.build_request(agent, to="orion", capability="ask_qwen",
                               payload=make_1kb_payload(), passport=passport,
                               ts=int(time.time()), nonce=f"pipeline-{i}")
        t0 = time.perf_counter()
        ok, reason = m.verify_request(msg, known_agents[agent.agent_id],
                                       root.pub_b64, "ask@orion", guard,
                                       now=int(time.time()))
        latencies.append((time.perf_counter() - t0) * 1e6)  # microseconds
        assert ok, reason
    return latencies


def bench_replay_cache_scaling():
    results = {}
    for target_n in (100, 10_000, 100_000):
        guard = ReplayGuard(window_s=10**9)  # huge window so nothing prunes mid-fill
        rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        now = time.time()
        for i in range(target_n):
            guard.check_and_record(f"seed-{i}", int(now), now)
        rss_after_fill = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # time 1000 fresh-nonce checks against this pre-filled guard
        t0 = time.perf_counter()
        for i in range(1000):
            guard.check_and_record(f"probe-{i}", int(now), now)
        elapsed = time.perf_counter() - t0

        results[target_n] = {
            "check_ops_per_sec": 1000 / elapsed,
            "avg_check_latency_us": (elapsed / 1000) * 1e6,
            "rss_kb_after_fill": rss_after_fill,
            "rss_delta_kb_vs_before_fill": rss_after_fill - rss_before,
        }
    return results


def bench_e2e_inprocess():
    """Phase-0 vertical slice, in-process (no network/Flask): build -> verify -> mock execute -> sign receipt."""
    root = idmod.Identity.generate()
    agent = idmod.Identity.generate()
    responder = idmod.Identity.generate()
    passport = p.issue(root, agent.agent_id, "root:bench", ["publish@blog.example.com"],
                        int(time.time()) - 10, int(time.time()) + 3600)
    guard = ReplayGuard()

    t0 = time.perf_counter()
    for i in range(N_E2E):
        msg = m.build_request(agent, to="responder", capability="publish@blog.example.com",
                               payload={"title": "t", "body": "b" * 200}, passport=passport,
                               ts=int(time.time()), nonce=f"e2e-{i}")
        ok, reason = m.verify_request(msg, agent.pub_b64, root.pub_b64,
                                       "publish@blog.example.com", guard, now=int(time.time()))
        assert ok, reason
        # mock execute + signed receipt (step 8)
        receipt = m.sign_envelope(responder, {"status": "ok", "ts": int(time.time())})
        assert m.verify_envelope(responder.pub_b64, receipt)
    elapsed = time.perf_counter() - t0
    return N_E2E / elapsed, elapsed


def main():
    report = {"environment": env_report()}

    rate, elapsed = bench_keygen()
    report["keygen"] = {"ops_per_sec": rate, "n": N_KEYGEN, "elapsed_s": elapsed}

    report["sign_verify"] = bench_sign_verify()

    pipeline_latencies = bench_pipeline()
    report["pipeline_latency_us"] = {
        "n": N_PIPELINE,
        "median": statistics.median(pipeline_latencies),
        "p95": sorted(pipeline_latencies)[int(len(pipeline_latencies) * 0.95) - 1],
        "p99": sorted(pipeline_latencies)[int(len(pipeline_latencies) * 0.99) - 1],
        "min": min(pipeline_latencies),
        "max": max(pipeline_latencies),
    }
    report["pipeline_throughput_single_threaded_ops_per_sec"] = 1e6 / report["pipeline_latency_us"]["median"]

    report["replay_cache_scaling"] = bench_replay_cache_scaling()

    e2e_rate, e2e_elapsed = bench_e2e_inprocess()
    report["e2e_inprocess"] = {"requests_per_sec_single_threaded": e2e_rate,
                                "n": N_E2E, "elapsed_s": e2e_elapsed}

    # wire size comparison: passport + signed request vs a rough JWT-equivalent estimate
    sample_passport = p.issue(idmod.Identity.generate(), "ag:0123456789abcdef",
                               "root:bench", ["ask@orion"],
                               int(time.time()), int(time.time()) + 3600)
    report["credential_sizes_bytes"] = {
        "passport_canonical": len(canonical_bytes({k: v for k, v in sample_passport.items() if k != "sig"})) + len(sample_passport["sig"]),
        "passport_json_wire": len(json.dumps(sample_passport)),
    }

    print(json.dumps(report, indent=2))
    with open("benchmarks/results-2026-07-20.json", "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
