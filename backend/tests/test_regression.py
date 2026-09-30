import numpy as np
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

from app.core.errors import SolverError
from app.solvers import regression

rng = np.random.default_rng(1)
X1 = rng.normal(10, 2, 30)
X2 = rng.normal(5, 1, 30)
Y = 3 + 2 * X1 - 1.5 * X2 + rng.normal(0, 1, 30)


def test_correlation_pearson_and_spearman():
    r = regression.correlation({"x": X1.tolist(), "y": Y.tolist()}, "pearson", 0.05).result
    ref = stats.pearsonr(X1, Y)
    assert r["r"] == pytest.approx(ref.statistic)
    assert r["p_value"] == pytest.approx(ref.pvalue)
    s = regression.correlation({"x": X1.tolist(), "y": Y.tolist()}, "spearman", 0.05).result
    assert s["r"] == pytest.approx(stats.spearmanr(X1, Y).statistic)


def test_correlation_matrix():
    r = regression.correlation({"a": X1.tolist(), "b": X2.tolist(), "y": Y.tolist()}, "pearson", 0.05).result
    assert np.allclose(r["matrix"], np.corrcoef([X1, X2, Y]))


def test_simple_regression_matches_statsmodels():
    out = regression.simple(X1.tolist(), Y.tolist(), 0.05, predict=[10.0])
    ref = sm.OLS(Y, sm.add_constant(X1)).fit()
    r = out.result
    assert r["coefficients"] == pytest.approx(ref.params)
    assert r["standard_errors"] == pytest.approx(ref.bse)
    assert r["r_squared"] == pytest.approx(ref.rsquared)
    pred = ref.get_prediction(np.array([[1, 10.0]])).summary_frame(alpha=0.05)
    row = r["predictions"][0]
    assert row[1] == pytest.approx(pred["mean"].iloc[0])
    assert row[2] == pytest.approx(pred["mean_ci_lower"].iloc[0])
    assert row[4] == pytest.approx(pred["obs_ci_lower"].iloc[0])


def test_multiple_regression_matches_statsmodels():
    r = regression.multiple(Y.tolist(), {"x1": X1.tolist(), "x2": X2.tolist()}, 0.05).result
    ref = sm.OLS(Y, sm.add_constant(np.column_stack([X1, X2]))).fit()
    assert r["coefficients"] == pytest.approx(ref.params)
    assert r["p_values"] == pytest.approx(ref.pvalues)
    assert r["adj_r_squared"] == pytest.approx(ref.rsquared_adj)
    assert r["f"] == pytest.approx(ref.fvalue)


def test_perfect_multicollinearity_rejected():
    with pytest.raises(SolverError, match="singular"):
        regression.multiple(Y.tolist(), {"x1": X1.tolist(), "x1_dup": (2 * X1).tolist()}, 0.05)


def test_assumptions_match_statsmodels():
    r = regression.assumptions(Y.tolist(), {"x1": X1.tolist(), "x2": X2.tolist()}, 0.05).result
    X = sm.add_constant(np.column_stack([X1, X2]))
    fit = sm.OLS(Y, X).fit()
    lm, lm_p, _, _ = het_breuschpagan(fit.resid, X)
    assert r["breusch_pagan"]["lm"] == pytest.approx(lm)
    assert r["breusch_pagan"]["p_value"] == pytest.approx(lm_p)
    assert r["durbin_watson"] == pytest.approx(durbin_watson(fit.resid))
    assert r["vif"][0][2] == pytest.approx(variance_inflation_factor(X, 1))
