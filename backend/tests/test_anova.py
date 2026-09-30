import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd

from app.core.errors import SolverError
from app.solvers import anova

GROUPS = [
    ("A", [23, 25, 21, 22, 24]),
    ("B", [30, 28, 29, 31, 27]),
    ("C", [22, 24, 23, 21, 25]),
]


def test_one_way_matches_scipy():
    r = anova.one_way(GROUPS, 0.05).result
    ref = stats.f_oneway(*[g for _, g in GROUPS])
    assert r["statistic"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)
    assert r["ssb"] + r["ssw"] == pytest.approx(r["sst"])


def test_one_way_zero_within_variance():
    with pytest.raises(SolverError):
        anova.one_way([("A", [1, 1]), ("B", [2, 2])], 0.05)


@pytest.mark.parametrize(
    "groups", [GROUPS, [("A", [23, 25, 21, 22]), ("B", [30, 28, 29, 31, 27, 26]), ("C", [22, 24, 23])]]
)
def test_tukey_matches_statsmodels(groups):
    r = anova.tukey_hsd(groups, 0.05).result
    values = np.concatenate([g for _, g in groups])
    labels = np.concatenate([[n] * len(g) for n, g in groups])
    ref = pairwise_tukeyhsd(values, labels, alpha=0.05)
    # Urutan pasangan statsmodels (A-B, A-C, B-C) sama dengan urutan kelompok masukan.
    ours = [p["p_value"] for p in r["pairs"]]
    assert ours == pytest.approx(list(ref.pvalues), abs=1e-3)
    assert [p["significant"] for p in r["pairs"]] == list(ref.reject)


def _long(cells):
    return pd.DataFrame([(a, b, v) for a, b, vals in cells for v in vals], columns=["A", "B", "y"])


def test_two_way_with_interaction_matches_statsmodels():
    cells = [
        ("a1", "b1", [12, 14, 13]),
        ("a1", "b2", [18, 17, 19]),
        ("a2", "b1", [15, 16, 14]),
        ("a2", "b2", [25, 24, 26]),
        ("a3", "b1", [11, 12, 10]),
        ("a3", "b2", [16, 15, 17]),
    ]
    r = anova.two_way(cells, 0.05, "A", "B").result
    ref = sm.stats.anova_lm(ols("y ~ C(A) * C(B)", data=_long(cells)).fit(), typ=2)
    assert r["effects"]["A"]["f"] == pytest.approx(ref.loc["C(A)", "F"])
    assert r["effects"]["B"]["p_value"] == pytest.approx(ref.loc["C(B)", "PR(>F)"])
    assert r["effects"]["Interaksi A × B"]["f"] == pytest.approx(ref.loc["C(A):C(B)", "F"])


def test_two_way_without_replication():
    cells = [
        ("a1", "b1", [5]),
        ("a1", "b2", [7]),
        ("a2", "b1", [6]),
        ("a2", "b2", [9]),
        ("a3", "b1", [4]),
        ("a3", "b2", [8]),
    ]
    r = anova.two_way(cells, 0.05, "A", "B").result
    ref = sm.stats.anova_lm(ols("y ~ C(A) + C(B)", data=_long(cells)).fit(), typ=2)
    assert r["effects"]["A"]["f"] == pytest.approx(ref.loc["C(A)", "F"])


def test_two_way_unbalanced_rejected():
    with pytest.raises(SolverError, match="seimbang"):
        anova.two_way([("a1", "b1", [1, 2]), ("a1", "b2", [3]), ("a2", "b1", [1, 2]), ("a2", "b2", [3, 4])], 0.05)
