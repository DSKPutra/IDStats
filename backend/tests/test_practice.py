import pytest

from app.solvers import practice


@pytest.mark.parametrize("topic", [t["id"] for t in practice.topics()])
def test_every_topic_generates_and_checks(topic):
    for seed in range(5):
        q = practice.question(topic, seed)
        assert q["fields"] and q["prompt"]
        assert practice.question(topic, seed) == q  # deterministik
        g = practice._gen(topic, seed)
        ok = practice.check(topic, seed, dict(g.answers))
        assert ok["correct"] and ok["solution"]["steps"]
        wrong = practice.check(topic, seed, {k: v + 1000 for k, v in g.answers.items()})
        assert not wrong["correct"]


def test_api_roundtrip(client):
    topics = client.get("/api/practice/topics").json()
    q = client.get(f"/api/practice/question/{topics[0]['id']}", params={"seed": 3}).json()
    res = client.post(
        "/api/practice/check", json={"topic": q["topic"], "seed": 3, "answers": {f["key"]: None for f in q["fields"]}}
    ).json()
    assert res["correct"] is False and res["results"][0]["expected"] is not None
    assert client.get("/api/practice/question/tidak-ada", params={"seed": 1}).status_code == 422
