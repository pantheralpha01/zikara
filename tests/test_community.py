import uuid


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def test_community_topic_post_and_feed_flow(admin_client, client_http):
    topic = admin_client.post(
        "/community/topics",
        json={"name": f"Announcements-{_uid()}", "description": "Community announcements"},
    )
    assert topic.status_code == 201, topic.text
    topic_id = topic.json()["id"]

    sub = client_http.post("/community/subscriptions", json={"topic_id": topic_id})
    assert sub.status_code == 201, sub.text

    post = client_http.post(
        "/community/posts",
        json={
            "topic_id": topic_id,
            "title": "Service update",
            "content": "We have updated support hours.",
            "post_type": "announcement",
        },
    )
    assert post.status_code == 201, post.text
    post_id = post.json()["id"]

    get_post = client_http.get(f"/community/posts/{post_id}")
    assert get_post.status_code == 200, get_post.text
    assert get_post.json()["title"] == "Service update"

    feed = client_http.get("/community/feed")
    assert feed.status_code == 200, feed.text
    ids = [p["id"] for p in feed.json()]
    assert post_id in ids


def test_community_react_comment_flag_and_moderate(admin_client, client_http):
    topic = admin_client.post(
        "/community/topics",
        json={"name": f"General-{_uid()}", "description": "General discussion"},
    )
    assert topic.status_code == 201, topic.text
    topic_id = topic.json()["id"]

    post = client_http.post(
        "/community/posts",
        json={
            "topic_id": topic_id,
            "title": "My idea",
            "content": "Let's improve onboarding.",
            "post_type": "discussion",
        },
    )
    assert post.status_code == 201, post.text
    post_id = post.json()["id"]

    react = client_http.post(f"/community/posts/{post_id}/react", json={"reaction": "like"})
    assert react.status_code == 200, react.text

    comment = client_http.post(f"/community/posts/{post_id}/comments", json={"content": "Great point"})
    assert comment.status_code == 201, comment.text

    flag = client_http.post(f"/community/posts/{post_id}/flag", json={"reason": "Needs review"})
    assert flag.status_code == 200, flag.text

    moderate = admin_client.post(
        f"/community/posts/{post_id}/moderate",
        json={"status": "hidden", "moderation_note": "Temporarily hidden", "flag_resolution": "actioned"},
    )
    assert moderate.status_code == 200, moderate.text
    assert moderate.json()["status"] == "hidden"

    as_admin = admin_client.get(f"/community/posts/{post_id}")
    assert as_admin.status_code == 200, as_admin.text
    assert as_admin.json()["status"] == "hidden"


def test_community_digest_send(admin_client, client_http, monkeypatch):
    sent = {"count": 0}

    async def fake_send_simple_email(recipients, subject, body):
        sent["count"] += 1
        return True

    monkeypatch.setattr("app.routers.community.send_simple_email", fake_send_simple_email)

    topic = admin_client.post(
        "/community/topics",
        json={"name": f"Digest-{_uid()}", "description": "Digest topic"},
    )
    assert topic.status_code == 201, topic.text
    topic_id = topic.json()["id"]

    sub = client_http.post("/community/subscriptions", json={"topic_id": topic_id})
    assert sub.status_code == 201, sub.text

    post = admin_client.post(
        "/community/posts",
        json={
            "topic_id": topic_id,
            "title": "Daily update",
            "content": "Digest content entry.",
            "post_type": "announcement",
        },
    )
    assert post.status_code == 201, post.text

    digest = admin_client.post("/community/digest/send")
    assert digest.status_code == 200, digest.text
    assert digest.json()["emailsSent"] >= 1
    assert sent["count"] >= 1
