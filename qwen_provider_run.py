#!/usr/bin/env python3
# qwen_provider_run.py — run the local Orion qwen capability provider.
#
# Reverse-tunnel topology: this runs on the provider machine (where Ollama lives),
# bound to localhost only. An `ssh -R` tunnel exposes it on the relay host:127.0.0.1:8091,
# and the relay host nginx proxies https://relay.example.com/capability -> that tunnel.
# No private keys ever touch the relay host.
import json
import sys

sys.path.insert(0, "src")
from agentframe.identity import Identity          # noqa: E402
from provider.qwen_endpoint import create_qwen_app  # noqa: E402

SYSTEM = ("You are Orion, a terse local assistant agent serving the operator's household. "
          "Answer concisely and helpfully.")


def main(config_path: str = "node_config.json") -> None:
    cfg = json.load(open(config_path))
    orion = Identity.load(cfg["orion_key"])
    app = create_qwen_app(
        orion=orion,
        root_pub_b64=cfg["root_pub_b64"],
        known_agents=cfg["known_agents"],
        model=cfg.get("ollama_model", "qwen2.5:7b"),
        system=SYSTEM,
    )
    host, port = cfg.get("bind_host", "127.0.0.1"), int(cfg.get("bind_port", 8081))
    print(f"[orion-qwen] serving on http://{host}:{port}/capability "
          f"(orion={orion.agent_id}, model={cfg.get('ollama_model')})", flush=True)
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "node_config.json")
