import numpy as np
import pytest
from scipy import stats

from app.solvers.descriptive import summary

DATA = [72, 85, 64, 90, 78, 85, 69, 74, 88, 95, 58, 81, 77, 85, 70, 66, 92, 79, 83, 75]


def test_matches_scipy_and_numpy():
    r = summary(DATA).result
    x = np.array(DATA, dtype=float)
    assert r["n"] == 20
    assert r["mean"] == pytest.approx(x.mean())
    assert r["median"] == pytest.approx(np.median(x))
    assert r["modes"] == [85.0]
    assert r["variance"] == pytest.approx(x.var(ddof=1))
    assert r["std"] == pytest.approx(x.std(ddof=1))
    for key, p in (("q1", 25), ("q2", 50), ("q3", 75)):
        assert r[key] == pytest.approx(np.percentile(x, p))
    assert r["skewness"] == pytest.approx(stats.skew(x, bias=False))
    assert r["kurtosis"] == pytest.approx(stats.kurtosis(x, bias=False))


def test_response_contract():
    out = summary(DATA)
    assert len(out.steps) == 7
    assert {c.id for c in out.charts} == {"histogram", "boxplot", "qqplot"}
    assert out.warnings == []


def test_small_sample_warnings_and_no_mode():
    out = summary([1, 2])
    assert out.result["skewness"] is None
    assert out.result["kurtosis"] is None
    assert any("modus" in w for w in out.warnings)


def test_endpoint_validation_messages(client):
    res = client.post("/api/descriptive/summary", json={"data": [1]})
    assert res.status_code == 422
    assert "Input tidak valid" in res.json()["detail"]
    res = client.post("/api/descriptive/summary", json={"data": ["abc", 2]})
    assert res.status_code == 422


def test_endpoint_ok(client):
    res = client.post("/api/descriptive/summary", json={"data": DATA})
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"result", "steps", "charts", "warnings"}
