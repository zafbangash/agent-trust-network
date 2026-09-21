# tests/test_build_blog.py
import json
from provider.build_blog import build_site

def _write_post(posts_dir, slug, title, ts, body="Hello **world**"):
    posts_dir.mkdir(parents=True, exist_ok=True)
    rec = {"slug": slug, "title": title, "subtitle": "", "tags": ["t"],
           "markdown": body, "ts": ts, "url": f"/posts/{slug}.html"}
    (posts_dir / f"{slug}.json").write_text(json.dumps(rec))

def test_build_creates_index_and_post_pages(tmp_path):
    posts = tmp_path / "posts"
    site = tmp_path / "site"
    _write_post(posts, "100-a", "First", ts=100)
    _write_post(posts, "200-b", "Second", ts=200)
    build_site(str(posts), str(site))
    index = (site / "index.html").read_text()
    assert "First" in index and "Second" in index
    # newest first
    assert index.index("Second") < index.index("First")
    post_html = (site / "posts" / "200-b.html").read_text()
    assert "<strong>world</strong>" in post_html  # markdown rendered

def test_build_escapes_title_in_index(tmp_path):
    posts = tmp_path / "posts"
    site = tmp_path / "site"
    _write_post(posts, "1-x", "<script>bad</script>", ts=1)
    build_site(str(posts), str(site))
    index = (site / "index.html").read_text()
    assert "<script>bad" not in index
    assert "&lt;script&gt;" in index
