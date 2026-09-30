import pytest
from scipy import stats

from app.core.errors import SolverError
from app.solvers import nonparametric as npar

A = [14, 18, 21, 25, 12, 30, 17, 22, 19, 28, 24, 16]
B = [10, 15, 11, 13, 20, 9, 14, 12, 16, 8, 11, 13]


@pytest.mark.parametrize("alt", ["two-sided", "greater"])
def test_mann_whitney_matches_scipy_asymptotic(alt):
    r = npar.mann_whitney(A, B, alt, 0.05).result
    ref = stats.mannwhitneyu(A, B, alternative=alt, method="asymptotic", use_continuity=False)
    assert r["u1"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)


def test_wilcoxon_paired_matches_scipy():
    r = npar.wilcoxon(A, "two-sided", 0.05, y=B).result
    ref = stats.wilcoxon(A, B, method="approx", correction=False)
    assert min(r["w_plus"], r["w_minus"]) == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)


def test_wilcoxon_all_zero():
    with pytest.raises(SolverError):
        npar.wilcoxon([1, 2, 3], "two-sided", 0.05, y=[1, 2, 3])


def test_kruskal_matches_scipy():
    groups = [("A", A[:6]), ("B", B[:6]), ("C", [15, 16, 18, 14, 19, 17])]
    r = npar.kruskal_wallis(groups, 0.05).result
    ref = stats.kruskal(*[g for _, g in groups])
    assert r["statistic"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)
