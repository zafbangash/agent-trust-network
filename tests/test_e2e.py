# tests/test_e2e.py
import json
import threading
import time
from wsgiref.simple_server import make_server

from agentframe import identity as idmod
from agentframe import passport as pp
from provider.endpoint import create_app
from requester.client import publish_via_orion

GRANT = "publish@blog.example.com"

def _serve(app):
    srv = make_server("127.0.0.1", 0, app)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, srv.server_address[1]

def test_full_publish_flow(tmp_path):
    root = idmod.Identity.generate()
    orion = idmod.Identity.generate()
    Alice = idmod.Identity.generate()
    passport = pp.issue(root, Alice.agent_id, "alice", [GRANT],
                        issued=0, expires=10**12)

    posts_dir = tmp_path / "posts"
    site_dir = tmp_path / "site"
    app = create_app(orion=orion, root_pub_b64=root.pub_b64,
                     known_agents={Alice.agent_id: Alice.pub_b64},
                     posts_dir=str(posts_dir), site_dir=str(site_dir))
    srv, port = _serve(app)
    try:
        url = f"http://127.0.0.1:{port}/capability"
        payload = {"title": "Aria's first post", "subtitle": "hi",
                   "tags": ["family"], "markdown": "It **works**."}
        receipt, authentic = publish_via_orion(url, Alice, payload,
                                                passport, orion.pub_b64)
    finally:
        srv.shutdown()

    assert authentic is True
    assert receipt["status"] == "ok"

    # the post landed on disk and rendered into the site
    files = list(posts_dir.glob("*.json"))
    assert len(files) == 1
    rec = json.loads(files[0].read_text())
    assert rec["title"] == "Aria's first post"
    index = (site_dir / "index.html").read_text()
    assert "Aria&#x27;s first post" in index or "Aria's first post" in index
    post_page = (site_dir / "posts" / f"{rec['slug']}.html").read_text()
    assert "<strong>works</strong>" in post_page
