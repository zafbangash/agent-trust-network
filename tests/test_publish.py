# tests/test_publish.py
import json
import pytest
from provider.publish import validate_payload, slugify, save_post

def test_validate_requires_title_and_markdown():
    assert validate_payload({"title": "T", "markdown": "B"}) == (True, "ok")
    assert validate_payload({"markdown": "B"})[0] is False
    assert validate_payload({"title": "  ", "markdown": "B"})[0] is False
    assert validate_payload({"title": "T", "markdown": ""})[0] is False

def test_validate_rejects_nonstring_tags():
    ok, reason = validate_payload({"title": "T", "markdown": "B", "tags": [1, 2]})
    assert (ok, reason) == (False, "bad_tags")

def test_slugify_is_url_safe():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("") == "post"

def test_save_post_writes_record(tmp_path):
    rec = save_post(str(tmp_path), {"title": "My Post", "markdown": "Body"}, ts=42)
    assert rec["slug"] == "42-my-post"
    assert rec["url"] == "/posts/42-my-post.html"
    on_disk = json.loads((tmp_path / "42-my-post.json").read_text())
    assert on_disk["title"] == "My Post"
