import numpy as np
import pytest
from scipy import stats
from statsmodels.stats.diagnostic import lilliefors

from app.core.errors import SolverError
from app.solvers import distributions, normality

X = np.random.default_rng(7).normal(50, 8, 40).tolist()


def test_shapiro():
    r = normality.shapiro_wilk(X, 0.05).result
    ref = stats.shapiro(X)
    assert r["statistic"] == pytest.approx(ref.statistic)
    assert r["normal"] is True


def test_ks_known_params_matches_scipy():
    r = normality.kolmogorov_smirnov(X, 0.05, mean=50, sd=8).result
    ref = stats.kstest(X, "norm", args=(50, 8))
    assert r["statistic"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue, abs=1e-6)


def test_lilliefors_close_to_statsmodels():
    r = normality.kolmogorov_smirnov(X, 0.05).result
    d, p = lilliefors(X, dist="norm", pvalmethod="table")
    assert r["statistic"] == pytest.approx(d)
    assert r["p_value"] == pytest.approx(p, abs=0.05)


def test_exponential_data_not_normal():
    x = np.random.default_rng(3).exponential(1, 80).tolist()
    assert normality.shapiro_wilk(x, 0.05).result["normal"] is False


@pytest.mark.parametrize(
    ("dist", "params", "mode", "kw", "expected"),
    [
        ("binomial", {"n": 10, "p": 0.3}, "pdf", {"x": 3}, stats.binom.pmf(3, 10, 0.3)),
        (
            "binomial",
            {"n": 10, "p": 0.3},
            "between",
            {"a": 2, "b": 4},
            stats.binom.cdf(4, 10, 0.3) - stats.binom.cdf(1, 10, 0.3),
        ),
        ("poisson", {"lam": 4}, "cdf", {"x": 2}, stats.poisson.cdf(2, 4)),
        ("normal", {"mu": 100, "sigma": 15}, "sf", {"x": 130}, stats.norm.sf(130, 100, 15)),
        ("normal", {"mu": 0, "sigma": 1}, "ppf", {"p": 0.975}, 1.959963984540054),
        ("exponential", {"lam": 2}, "cdf", {"x": 1}, 1 - np.exp(-2)),
        ("uniform", {"a": 2, "b": 6}, "cdf", {"x": 3}, 0.25),
        ("t", {"df": 10}, "ppf", {"p": 0.95}, stats.t.ppf(0.95, 10)),
        ("chi2", {"df": 4}, "sf", {"x": 9.488}, stats.chi2.sf(9.488, 4)),
        ("f", {"df1": 3, "df2": 12}, "ppf", {"p": 0.95}, stats.f.ppf(0.95, 3, 12)),
        ("gamma", {"k": 3, "lam": 2}, "cdf", {"x": 1}, stats.gamma.cdf(1, 3, scale=0.5)),
    ],
)
def test_distribution_calculator(dist, params, mode, kw, expected):
    assert distributions.compute(dist, params, mode, **kw).result["value"] == pytest.approx(expected)


def test_distribution_validation():
    with pytest.raises(SolverError):
        distributions.compute("binomial", {"n": 10, "p": 1.5}, "pdf", x=1)
    with pytest.raises(SolverError):
        distributions.compute("normal", {"mu": 0, "sigma": 1}, "ppf", p=1.2)
    with pytest.raises(SolverError):
        distributions.compute("normal", {"mu": 0}, "cdf", x=0)


def test_statistical_tables():
    z = distributions.table("z").tables[0]
    assert z.rows[19][7] == pytest.approx(0.9750, abs=1e-4)  # Φ(1.96)
    t = distributions.table("t").tables[0]
    assert t.rows[9][2] == pytest.approx(1.8125, abs=1e-4)  # df=10, α=0.05
    assert distributions.table("f", 0.05).tables[0].rows[0][1] == pytest.approx(161.448, abs=1e-3)


def test_distribution_catalog_endpoint(client):
    body = client.get("/api/distributions").json()
    assert {d["id"] for d in body} >= {"binomial", "poisson", "normal", "gamma"}
