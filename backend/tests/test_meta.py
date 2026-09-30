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
    """Setiap contoh soal harus bisa langsung dihitung oleh endpoint-nya."""
    import json

    from app.core.config import EXAMPLES_DIR

    endpoints = {
        "descriptive": "/descriptive/summary",
        "frequency-table": "/descriptive/frequency-table",
        "scatter": "/descriptive/scatter",
        "distribution-calculator": "/distributions/compute",
        "distribution-table": "/distributions/table",
        "confidence-interval": "/inferential/confidence-interval",
        "z-test": "/inferential/z-test",
        "t-one-sample": "/inferential/t-test/one-sample",
        "t-independent": "/inferential/t-test/independent",
        "t-paired": "/inferential/t-test/paired",
        "proportion-test": "/inferential/proportion-test",
        "chi-square-gof": "/inferential/chi-square/goodness-of-fit",
        "chi-square-independence": "/inferential/chi-square/independence",
        "f-test": "/inferential/f-test",
        "anova-one-way": "/anova/one-way",
        "anova-two-way": "/anova/two-way",
        "tukey-hsd": "/anova/tukey-hsd",
        "correlation": "/regression/correlation",
        "regression-simple": "/regression/simple",
        "regression-multiple": "/regression/multiple",
        "regression-assumptions": "/regression/assumptions",
        "mann-whitney": "/nonparametric/mann-whitney",
        "wilcoxon": "/nonparametric/wilcoxon",
        "kruskal-wallis": "/nonparametric/kruskal-wallis",
        "shapiro-wilk": "/normality/shapiro-wilk",
        "kolmogorov-smirnov": "/normality/kolmogorov-smirnov",
    }
    files = sorted((EXAMPLES_DIR / "stats").glob("*.json"))
    assert {f.stem for f in files} == set(endpoints)
    for f in files:
        body = json.loads(f.read_text(encoding="utf-8"))["input"]
        res = client.post(f"/api{endpoints[f.stem]}", json=body)
        assert res.status_code == 200, (f.stem, res.json())
