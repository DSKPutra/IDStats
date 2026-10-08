"""Modul C2–C3: metaheuristik, uji statistik, dan aplikasinya."""

import numpy as np
import pytest
from scipy import stats

from app.core.errors import SolverError
from app.solvers.ml import meta_apps
from app.solvers.ml import metaheuristics as MH


@pytest.mark.parametrize("algo", list(MH.ALGORITHMS))
def test_every_algorithm_improves_sphere(algo):
    f = MH.BENCHMARKS["sphere"][1]
    start = MH.run(algo, f, [-100] * 5, [100] * 5, 20, 1, 0).best_f
    res = MH.run(algo, f, [-100] * 5, [100] * 5, 20, 150, 0)
    assert res.best_f < start and res.best_f < 50
    assert np.all(res.best_x >= -100) and np.all(res.best_x <= 100)
    assert len(res.curve) == 150 and all(a >= b for a, b in zip(res.curve, res.curve[1:], strict=False))


def test_strong_algorithms_reach_optimum():
    f = MH.BENCHMARKS["sphere"][1]
    for algo in ("hho", "cmaes", "de", "aoa"):
        assert MH.run(algo, f, [-5] * 5, [5] * 5, 30, 300, 1).best_f < 1e-6, algo


def test_reproducible_with_seed():
    f = MH.BENCHMARKS["rastrigin"][1]
    a = MH.run("pso", f, [-5] * 3, [5] * 3, 10, 20, 7).best_f
    assert a == MH.run("pso", f, [-5] * 3, [5] * 3, 10, 20, 7).best_f


def test_friedman_matches_scipy():
    rng = np.random.default_rng(0)
    m = rng.random((12, 4))
    chi2, p, _ = meta_apps.friedman(m)
    ref = stats.friedmanchisquare(*m.T)
    assert chi2 == pytest.approx(ref.statistic) and p == pytest.approx(ref.pvalue)


def test_benchmark_and_limits():
    r = meta_apps.benchmark("sphere", 5, ["de", "sa"], 10, 30, 5, 1)
    assert np.array(r.result["finals"]).shape == (5, 2)
    with pytest.raises(SolverError):
        meta_apps.benchmark("sphere", 50, ["de"] * 8, 100, 1000, 30, 1)


def test_or_applications_match_exact():
    assert (
        meta_apps.knapsack_meta(
            [12, 7, 11, 8, 9, 6, 5, 14, 3, 10], [24, 13, 23, 15, 16, 11, 8, 30, 5, 20], 40, 1
        ).result["sa"]
        == 82
    )
    s = meta_apps.scheduling([3, 2, 4, 5, 1, 6, 2, 3], [2, 1, 3, 2, 1, 4, 1, 2], [5, 6, 9, 12, 3, 15, 8, 10], 1).result
    assert s["sa"] == s["exact"]
    t = meta_apps.tsp(None, 9, 3).result
    assert t["optimal"] <= min(v for k, v in t.items() if k != "optimal") + 1e-9


def test_gridworld_learns_reasonable_policy():
    r = meta_apps.gridworld(". . . G\n. # . T\nS . . .", 10, -10, 0.1, 0.9, 0.3, 0.3, 4000, 0.0, 1).result
    assert r["policy_agreement"] >= 0.6
    with pytest.raises(SolverError):
        meta_apps.gridworld("S . X", 10, -10, 0.1, 0.9, 0.3, 0.3, 10, 0, 1)


def test_hpo_and_feature_selection_small():
    h = meta_apps.hyperparameter("iris", "knn", ["random", "bayes"], 6, 0).result
    assert max(e["score"] for e in h["random"]) > 0.85
    fs = meta_apps.feature_selection("wine", ["pso"], 4, 0.99, 0).result
    assert fs["rows"][0][0] == "Semua fitur"
