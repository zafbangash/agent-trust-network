# provider_run.py — run Orion's endpoint on the relay host behind nginx TLS
import json, os, sys
sys.path.insert(0, "src")
from agentframe.identity import Identity
from provider.endpoint import create_app

# known_agents now comes from node_config.json (zaff_agent, vega, Polaris) so the
# blog provider recognizes every registered agent and can enforce grant *scope*:
# a known agent lacking publish@blog gets `unauthorized`, not `unknown_sender`.
# Env still overrides for backward-compat with the old WIFE_* launch command.
cfg = json.load(open(os.environ.get("NODE_CONFIG", "node_config.json")))
orion = Identity.load(os.environ.get("ORION_KEY", cfg["orion_key"]))
known = dict(cfg.get("known_agents", {}))
if os.environ.get("WIFE_AGENT_ID") and os.environ.get("WIFE_PUB_B64"):
    known[os.environ["WIFE_AGENT_ID"]] = os.environ["WIFE_PUB_B64"]
app = create_app(
    orion=orion,
    root_pub_b64=os.environ.get("ROOT_PUB_B64", cfg["root_pub_b64"]),
    known_agents=known,
    posts_dir=os.environ.get("BLOG_POSTS_DIR", "blog/posts"),
    site_dir=os.environ.get("BLOG_SITE_DIR", "blog/site"),
)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8081)  # nginx terminates TLS in front
