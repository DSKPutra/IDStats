import numpy as np
import pytest
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

from app.core.errors import SolverError
from app.solvers import inferential as inf

A = [12.1, 11.8, 12.5, 12.0, 11.6, 12.3, 12.7, 11.9, 12.2, 12.4]
B = [11.5, 11.9, 11.2, 11.7, 12.0, 11.4, 11.8, 11.1]


@pytest.mark.parametrize("alt", ["two-sided", "less", "greater"])
def test_t_one_sample_matches_scipy(alt):
    r = inf.t_one_sample(12.0, alt, 0.05, data=A).result
    ref = stats.ttest_1samp(A, 12.0, alternative=alt)
    assert r["statistic"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)


def test_t_one_sample_from_summary_equals_from_data():
    x = np.array(A)
    a = inf.t_one_sample(12.0, "two-sided", 0.05, data=A).result
    b = inf.t_one_sample(12.0, "two-sided", 0.05, n=x.size, mean=x.mean(), sd=x.std(ddof=1)).result
    assert a["p_value"] == pytest.approx(b["p_value"])


@pytest.mark.parametrize("equal_var", [True, False])
def test_t_independent_matches_scipy(equal_var):
    r = inf.t_independent(A, B, equal_var, "two-sided", 0.05).result
    ref = stats.ttest_ind(A, B, equal_var=equal_var)
    assert r["statistic"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)


def test_t_paired_matches_scipy():
    r = inf.t_paired(A[:8], B, "greater", 0.05).result
    ref = stats.ttest_rel(A[:8], B, alternative="greater")
    assert r["p_value"] == pytest.approx(ref.pvalue)


def test_t_paired_length_mismatch():
    with pytest.raises(SolverError):
        inf.t_paired(A, B, "two-sided", 0.05)


def test_z_test_textbook():
    # x̄ = 105, σ = 15, n = 36, μ0 = 100 → z = 2.0
    r = inf.z_test(100, 15, "greater", 0.05, n=36, mean=105).result
    assert r["statistic"] == pytest.approx(2.0)
    assert r["p_value"] == pytest.approx(stats.norm.sf(2.0))
    assert r["reject_h0"] is True
    assert r["critical_upper"] == pytest.approx(1.6449, abs=1e-4)


def test_proportion_tests_match_statsmodels():
    r = inf.proportion_test("two-sided", 0.05, 45, 100, p0=0.5).result
    z, p = proportions_ztest(45, 100, value=0.5, prop_var=0.5)
    assert r["statistic"] == pytest.approx(z)
    assert r["p_value"] == pytest.approx(p)
    r2 = inf.proportion_test("two-sided", 0.05, 45, 100, x2=60, n2=110).result
    z2, p2 = proportions_ztest([45, 60], [100, 110])
    assert r2["statistic"] == pytest.approx(z2)
    assert r2["p_value"] == pytest.approx(p2)


def test_chi_square_gof_and_probabilities():
    obs = [18, 22, 20, 15, 25]
    r = inf.chi_square_gof(obs, 0.05).result
    ref = stats.chisquare(obs)
    assert r["statistic"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)
    r2 = inf.chi_square_gof([30, 50, 20], 0.05, expected=[0.25, 0.5, 0.25]).result
    assert r2["statistic"] == pytest.approx(stats.chisquare([30, 50, 20], [25, 50, 25]).statistic)


def test_chi_square_independence_matches_scipy():
    table = [[20, 15, 25], [30, 25, 10]]
    r = inf.chi_square_independence(table, 0.05).result
    ref = stats.chi2_contingency(table, correction=False)
    assert r["statistic"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)
    assert r["df"] == ref.dof


def test_chi_square_independence_zero_row():
    with pytest.raises(SolverError):
        inf.chi_square_independence([[0, 0], [1, 2]], 0.05)


def test_f_test_two_sided():
    r = inf.f_test(A, B, "two-sided", 0.05).result
    f = np.var(A, ddof=1) / np.var(B, ddof=1)
    d = stats.f(len(A) - 1, len(B) - 1)
    assert r["statistic"] == pytest.approx(f)
    assert r["p_value"] == pytest.approx(2 * min(d.cdf(f), d.sf(f)))


def test_confidence_intervals():
    x = np.array(A)
    r = inf.confidence_interval("mean_t", 0.95, data=A).result
    lo, hi = stats.t.interval(0.95, x.size - 1, loc=x.mean(), scale=stats.sem(x))
    assert (r["lower"], r["upper"]) == pytest.approx((lo, hi))
    r = inf.confidence_interval("mean_z", 0.95, n=36, mean=105, sigma=15).result
    assert r["lower"] == pytest.approx(105 - 1.959964 * 2.5, abs=1e-5)
    r = inf.confidence_interval("proportion", 0.9, successes=40, n=100).result
    assert r["estimate"] == 0.4 and r["lower"] < 0.4 < r["upper"]
    r = inf.confidence_interval("variance", 0.95, data=A).result
    s2 = x.var(ddof=1)
    assert r["lower"] == pytest.approx((x.size - 1) * s2 / stats.chi2.ppf(0.975, x.size - 1))


def test_endpoints_smoke(client):
    assert client.post("/api/inferential/t-test/one-sample", json={"data": A, "mu0": 12}).status_code == 200
    assert (
        client.post("/api/inferential/z-test", json={"n": 36, "mean": 105, "mu0": 100, "sigma": 15}).status_code == 200
    )
    res = client.post("/api/inferential/t-test/one-sample", json={"mu0": 12})
    assert res.status_code == 422 and "Isi data" in res.json()["detail"]
