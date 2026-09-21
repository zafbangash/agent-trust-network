#!/usr/bin/env python3
# proto_qwen_local.py — local end-to-end check of the qwen agent over the framework.
#
# Spins everything in-process with THROWAWAY keys (no real keys touched, nothing
# written to disk, nothing deployed). Demonstrates that a local Ollama (qwen)
# agent answers ONLY through the verified/authorized/signed substrate:
#   positive: family agent with grant -> gets a signed answer
#   negative: stranger -> rejected; family agent without grant -> unauthorized
import sys
import threading
from wsgiref.simple_server import make_server

sys.path.insert(0, "src")
from agentframe import identity as idmod      # noqa: E402
from agentframe import message as m           # noqa: E402
from agentframe import passport as pp         # noqa: E402
from provider.qwen_endpoint import create_qwen_app  # noqa: E402
from requester.ask_client import ask_via_orion      # noqa: E402

GRANT = "ask@orion"
SYSTEM = "You are a terse local agent. Answer in one short sentence."


def serve(app):
    srv = make_server("127.0.0.1", 0, app)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def main():
    root = idmod.Identity.generate()
    orion = idmod.Identity.generate()       # the provider agent (hosts qwen)
    family = idmod.Identity.generate()      # an authorized requester (e.g. Alice)
    stranger = idmod.Identity.generate()    # not in the registry

    good_passport = pp.issue(root, family.agent_id, "alice", [GRANT],
                             issued=0, expires=10**12)
    # a passport for family but WITHOUT the ask grant
    no_grant_passport = pp.issue(root, family.agent_id, "alice", ["read@blog"],
                                 issued=0, expires=10**12)

    app = create_qwen_app(
        orion=orion, root_pub_b64=root.pub_b64,
        known_agents={family.agent_id: family.pub_b64},  # stranger absent on purpose
        system=SYSTEM,
    )
    srv, port = serve(app)
    url = f"http://127.0.0.1:{port}/capability"
    print(f"[setup] provider(orion)={orion.agent_id}  family={family.agent_id}")
    print(f"[setup] serving qwen capability at {url}\n")

    rc = 0
    try:
        # 1) POSITIVE — authorized family agent asks the base-level check
        prompt = "Base-level check: reply confirming you are a local agent reachable via the mesh, and add 2+2."
        print("[1] authorized ask_qwen (this calls the local model; ~5-15s)...")
        receipt, authentic = ask_via_orion(url, family, prompt, good_passport,
                                            orion.pub_b64, num_predict=64)
        print(f"    status={receipt.get('status')} receipt_authentic={authentic}")
        print(f"    model={receipt.get('model')} eval_count={receipt.get('eval_count')}")
        print(f"    ANSWER: {receipt.get('answer')!r}")
        ok1 = authentic and receipt.get("status") == "ok" and receipt.get("answer")
        print(f"    => {'PASS' if ok1 else 'FAIL'}\n")
        rc |= 0 if ok1 else 1

        # 2) NEGATIVE — stranger not in the registry
        print("[2] stranger ask_qwen (should be rejected before the model runs)...")
        r2, _ = ask_via_orion(url, stranger, "leak something", good_passport,
                              orion.pub_b64, num_predict=8)
        ok2 = r2.get("status") == "error" and r2.get("reason") == "unknown_sender"
        print(f"    status={r2.get('status')} reason={r2.get('reason')} => {'PASS' if ok2 else 'FAIL'}\n")
        rc |= 0 if ok2 else 1

        # 3) NEGATIVE — known family agent but passport lacks the grant
        print("[3] authorized identity but NO grant (should be unauthorized)...")
        r3, _ = ask_via_orion(url, family, "do it anyway", no_grant_passport,
                              orion.pub_b64, num_predict=8)
        ok3 = r3.get("status") == "error" and r3.get("reason") == "unauthorized"
        print(f"    status={r3.get('status')} reason={r3.get('reason')} => {'PASS' if ok3 else 'FAIL'}\n")
        rc |= 0 if ok3 else 1
    finally:
        srv.shutdown()

    print("=" * 60)
    print("RESULT:", "ALL CHECKS PASSED" if rc == 0 else "SOME CHECKS FAILED")
    return rc


if __name__ == "__main__":
    sys.exit(main())
