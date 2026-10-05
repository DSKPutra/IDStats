"""Bab 15–22 + Appendix: dicocokkan dengan contoh Hillier & Lieberman dan pustaka acuan."""

import numpy as np
import pytest

from app.core.errors import SolverError
from app.solvers import appendix, decision, forecasting, inventory, markov, mdp, queueing, simulation

GOF = ([[700, -100], [90, 90]], [0.25, 0.75])
MDP = "0 | 1 | 0 | 0 7/8 1/16 1/16\n1 | 1 | 1000 | 0 3/4 1/8 1/8\n1 | 3 | 6000 | 1 0 0 0\n2 | 1 | 3000 | 0 0 1/2 1/2\n2 | 2 | 4000 | 0 1 0 0\n2 | 3 | 6000 | 1 0 0 0\n3 | 3 | 6000 | 1 0 0 0"


def test_goferbroke():
    c = decision.criteria(*GOF, ["Bor", "Jual"], None).result["choices"]
    assert c["Aturan keputusan Bayes"] == "Bor" and c["Maksimin"] == "Jual"
    e = decision.experimentation(*GOF, [[0.6, 0.4], [0.2, 0.8]], None, 30, None, None).result
    assert (
        e["evpi"] == pytest.approx(142.5)
        and e["ep_experiment"] == pytest.approx(153)
        and e["evsi"] == pytest.approx(53)
    )
    assert e["posterior"][0][0] == pytest.approx(0.5) and e["posterior"][1][0] == pytest.approx(1 / 7)


def test_decision_tree_rollback_and_validation():
    tree = "[D] Pilih\n  A -> [C] Untung?\n    Ya (p=0.4) = 100\n    Tidak (p=0.6) = -20\n  B (biaya=5) = 30"
    r = decision.decision_tree(tree).result
    assert r["value"] == pytest.approx(28)
    with pytest.raises(SolverError, match="berjumlah 1"):
        decision.decision_tree("[D] X\n  A -> [C] Y\n    a (p=0.5) = 1\n    b (p=0.4) = 2")


def test_markov_inventory_example():
    p = [[0.08, 0.184, 0.368, 0.368], [0.632, 0.368, 0, 0], [0.264, 0.368, 0.368, 0], [0.08, 0.184, 0.368, 0.368]]
    r = markov.analyze(p, None, 8, None).result
    assert r["steady_state"] == pytest.approx([0.286, 0.285, 0.263, 0.166], abs=1e-3)
    assert r["first_passage"][3][0] == pytest.approx(3.50, abs=0.01)
    assert np.allclose(r["p_n"], np.linalg.matrix_power(np.array(p), 8))
    with pytest.raises(SolverError, match="berjumlah 1"):
        markov.analyze([[0.5, 0.4], [0.5, 0.5]], None, 2, None)


def test_absorbing_and_ctmc():
    g = [[1, 0, 0, 0, 0], [0.7, 0, 0.3, 0, 0], [0, 0.7, 0, 0.3, 0], [0, 0, 0.7, 0, 0.3], [0, 0, 0, 0, 1]]
    b = np.array(markov.analyze(g, None, 3, None).result["absorption"])
    assert np.allclose(b.sum(axis=1), 1)
    assert markov.ctmc([[0, 2, 0], [2, 0, 1], [0, 2, 0]], None).result["steady_state"] == pytest.approx([0.4, 0.4, 0.2])


def test_queues():
    m1 = queueing.mms(2, 3, 1).result
    assert (m1["l"], m1["wq"]) == pytest.approx((2, 2 / 3))
    assert queueing.mms(2, 3, 2).result["wq"] == pytest.approx(1 / 24)
    pr = queueing.priority([0.2, 0.6, 1.2], 3, 1, False).result["w"]
    assert pr[0] - 1 / 3 == pytest.approx(0.238, abs=1e-3)
    # M/M/1/K vs rumus tertutup
    rho, k = 2 / 3, 3
    p0 = (1 - rho) / (1 - rho ** (k + 1))
    assert queueing.mmsk(2, 3, 1, 3).result["p0"] == pytest.approx(p0)
    assert queueing.mg1(2, 3, 1 / 3).result["lq"] == pytest.approx(
        queueing.mms(2, 3, 1).result["lq"]
    )  # σ = 1/μ → M/M/1
    assert queueing.cost_optimization(2, 3, 20, 40).result["best_s"] == 2
    with pytest.raises(SolverError, match="tidak stabil"):
        queueing.mms(3, 2, 1)


def test_inventory():
    assert inventory.eoq(8000, 12000, 0.3).result["q"] == pytest.approx(25298, abs=1)
    assert inventory.eoq(8000, 12000, 0.3, shortage=1.1).result["q"] == pytest.approx(28540, abs=1)
    assert inventory.wagner_whitin([3, 2, 3, 2], 2, 0.2).result["total_cost"] == pytest.approx(4.8)
    assert inventory.newsvendor(10, 6, 2, 0, "normal", [100, 20]).result["q"] == pytest.approx(100)
    assert inventory.quantity_discount(1000, 100, 0.2, [[0, 10], [100, 9.5], [500, 9]]).result["price"] == 9


def test_wagner_whitin_bruteforce():
    rng = np.random.default_rng(1)
    for _ in range(20):
        d = rng.integers(0, 6, 5).tolist()
        k, h = float(rng.integers(1, 10)), float(rng.integers(1, 3))
        best = np.inf
        for mask in range(1 << 5):  # periode produksi
            starts = [t for t in range(5) if mask >> t & 1] + [5]
            if sum(d[: starts[0]]) > 0:
                continue  # permintaan sebelum produksi pertama tidak terpenuhi
            cost = 0.0
            for a, b in zip(starts, starts[1:], strict=False):
                if sum(d[a:b]):
                    cost += k + sum(h * d[t] * (t - a) for t in range(a, b))
            best = min(best, cost)
        assert inventory.wagner_whitin(d, k, h).result["total_cost"] == pytest.approx(best)


def test_forecasting():
    y = [382, 409, 429, 439, 440, 416, 434, 422, 428, 435, 431, 447]
    assert forecasting.moving_average(y, 3, 1).result["future"] == [pytest.approx(np.mean(y[-3:]))]
    es = forecasting.exp_smoothing(y, 0.5, None, 1).result
    assert es["forecast"][1] == pytest.approx(382) and es["forecast"][2] == pytest.approx(395.5)
    rng = np.random.default_rng(0)
    e = rng.normal(0, 1, 300)
    x = np.zeros(300)
    for t in range(1, 300):
        x[t] = 0.6 * x[t - 1] + e[t]
    params = forecasting.arima((x + 10).tolist(), 1, 0, 0, 1).result["params"]
    assert params[1] == pytest.approx(0.6, abs=0.1)


def test_mdp_machine_maintenance():
    pi = mdp.policy_improvement(MDP, None).result
    assert pi["policy"] == {"0": "1", "1": "1", "2": "2", "3": "3"} and pi["value"] == pytest.approx(1666.667, abs=0.01)
    assert mdp.lp_formulation(MDP).result["value"] == pytest.approx(1666.667, abs=0.01)
    disc = mdp.policy_improvement(MDP, 0.9).result["policy"]
    assert mdp.value_iteration(MDP, 0.9, 1000, 1e-9).result["policy"] == disc


def test_simulation():
    assert simulation.lcg(5, 3, 16, 4, 20).result["period"] == 16
    x = simulation.random_variates("inverse", "exponential", [2], 20000, 1, None, None, None).result
    assert x["mean"] == pytest.approx(0.5, abs=0.02)
    rj = simulation.random_variates("rejection", "", [], 5000, 1, "6x*(1-x)", 0, 1).result
    assert rj["mean"] == pytest.approx(0.5, abs=0.02)
    q = simulation.queue_simulation(2, 3, 1, 3000, 30, 1).result
    assert q["wq_ci"][0] - 0.1 < q["analytic_wq"] < q["wq_ci"][1] + 0.1
    mc = simulation.monte_carlo("D ~ normal(100, 15)\nP ~ uniform(8, 12)", "D*P - 600", 20000, 1, True).result
    assert mc["mean"] == pytest.approx(400, abs=5)


def test_appendix():
    assert appendix.convexity("x1^2 + x1*x2 + x2^2", [-5, -5], [5, 5]).result["verdict"] == "konveks"
    assert appendix.convexity("-x^2", [-3], [3]).result["verdict"] == "konkaf"
    c = appendix.classical("x1*x2", "x1 + x2 = 10", -20, 20).result
    assert c["points"][0] == pytest.approx([5, 5], abs=1e-6) and c["multipliers"][0] == pytest.approx([5], abs=1e-6)
    m = appendix.matrix_ops([[1, 2, 3], [0, 4, 5], [1, 0, 6]], None, "inverse").result
    assert np.allclose(m["inverse"], np.linalg.inv([[1, 2, 3], [0, 4, 5], [1, 0, 6]]))
    assert m["determinant"] == pytest.approx(22)
    with pytest.raises(SolverError, match="singular"):
        appendix.matrix_ops([[1, 2], [2, 4]], None, "inverse")
