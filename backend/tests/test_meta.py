def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_modules_registry(client):
    body = client.get("/api/meta/modules").json()
    ids = [c["id"] for c in body["categories"]]
    assert ids == ["stats", "or", "ml", "general"]
    all_methods = [m["id"] for c in body["categories"] for m in c["methods"]]
    assert len(all_methods) == len(set(all_methods)), "id metode harus unik"


def test_example_found_and_missing(client):
    ok = client.get("/api/examples/stats/descriptive")
    assert ok.status_code == 200
    assert len(ok.json()["input"]["data"]) == 20
    assert client.get("/api/examples/stats/tidak-ada").status_code == 404
    assert client.get("/api/examples/..%2F..%2Fetc/passwd").status_code == 404
