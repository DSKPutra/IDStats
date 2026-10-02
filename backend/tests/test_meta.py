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


def test_cors_allows_lovable_but_not_arbitrary_origins(client):
    ok = client.get("/api/health", headers={"Origin": "https://idstats.lovable.app"})
    assert ok.headers.get("access-control-allow-origin") == "https://idstats.lovable.app"
    bad = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in bad.headers


def test_every_example_solves(client):
    """Setiap contoh soal harus bisa langsung dihitung oleh endpoint yang tercantum di file contohnya."""
    import json

    from app.core.config import EXAMPLES_DIR

    files = sorted(EXAMPLES_DIR.glob("*/*.json"))
    assert files
    for f in files:
        example = json.loads(f.read_text(encoding="utf-8"))
        assert example["endpoint"].startswith("/"), f
        res = client.post(f"/api{example['endpoint']}", json=example["input"])
        assert res.status_code == 200, (f.name, res.json())
