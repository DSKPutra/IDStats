"""Bab 11–14: dicocokkan dengan contoh Hillier & Lieberman, scipy.milp, dan linprog."""

from fractions import Fraction

import numpy as np
import pytest
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

from app.core.errors import SolverError
from app.solvers import dynamic, games, integer, nonlinear
from app.solvers.expr import Expr
from app.solvers.lp.model import parse_model

SC = "1 2 2\n1 3 4\n1 4 3\n2 5 7\n2 6 4\n2 7 6\n3 5 3\n3 6 2\n3 7 4\n4 5 4\n4 6 1\n4 7 5\n5 8 1\n5 9 4\n6 8 6\n6 9 3\n7 8 3\n7 9 3\n8 10 3\n9 10 4"


def test_dp_hillier_examples():
    assert dynamic.stagecoach(SC, "1", "10", "min").result["value"] == 11
    whc = dynamic.resource_allocation(
        [[0, 45, 70, 90, 105, 120], [0, 20, 45, 75, 110, 150], [0, 50, 70, 80, 100, 130]], 5, None, "sum", "max"
    )
    assert whc.result["value"] == 170 and list(whc.result["allocation"].values()) == [1, 3, 1]
    sci = dynamic.resource_allocation([[0.4, 0.2, 0.15], [0.6, 0.4, 0.2], [0.8, 0.5, 0.3]], 2, None, "product", "min")
    assert sci.result["value"] == pytest.approx(0.06)
    assert dynamic.betting(3, 5, 3, 2 / 3).result["probability"] == pytest.approx(20 / 27)


def test_knapsack_vs_bruteforce():
    rng = np.random.default_rng(4)
    for _ in range(30):
        n = int(rng.integers(2, 5))
        w, v = rng.integers(1, 8, n).tolist(), rng.integers(1, 15, n).tolist()
        cap, cop = int(rng.integers(5, 20)), rng.integers(1, 3, n).tolist()
        best = 0
        for combo in np.ndindex(*[c + 1 for c in cop]):
            if sum(a * b for a, b in zip(combo, w, strict=True)) <= cap:
                best = max(best, sum(a * b for a, b in zip(combo, v, strict=True)))
        assert dynamic.knapsack(w, v, cap, cop, None).result["value"] == best


def test_branch_and_bound_california_and_random():
    cm = "max Z = 9x1 + 5x2 + 6x3 + 4x4\n6x1 + 3x2 + 5x3 + 2x4 <= 10\nx3 + x4 <= 1\n-x1 + x3 <= 0\n-x2 + x4 <= 0\nbin x1, x2, x3, x4"
    r = integer.branch_and_bound(parse_model(cm, True)).result
    assert r["z"] == 14 and r["x"] == {"x1": 1, "x2": 1, "x3": 0, "x4": 0}
    rng = np.random.default_rng(5)
    for _ in range(25):
        n, m = rng.integers(2, 5), rng.integers(2, 4)
        a, b, c = rng.integers(1, 10, (m, n)), rng.integers(10, 40, m), rng.integers(1, 12, n)
        text = (
            "max Z = "
            + " + ".join(f"{c[j]}x{j + 1}" for j in range(n))
            + "\n"
            + "\n".join(" + ".join(f"{a[i, j]}x{j + 1}" for j in range(n)) + f" <= {b[i]}" for i in range(m))
            + "\nint "
            + ", ".join(f"x{j + 1}" for j in range(n))
        )
        ref = milp(-c, constraints=LinearConstraint(a, -np.inf, b), integrality=np.ones(n), bounds=Bounds(0, np.inf))
        assert integer.branch_and_bound(parse_model(text, True)).result["z"] == pytest.approx(-ref.fun)


def test_mixed_integer():
    mip = "max Z = 4x1 - 2x2 + 7x3 - x4\nx1 + 5x3 <= 10\nx1 + x2 - x3 <= 1\n6x1 - 5x2 <= 0\n-x1 + 2x3 - 2x4 <= 3\nint x1, x2, x3"
    ref = milp(
        -np.array([4, -2, 7, -1]),
        constraints=LinearConstraint(
            [[1, 0, 5, 0], [1, 1, -1, 0], [6, -5, 0, 0], [-1, 0, 2, -2]], -np.inf, [10, 1, 0, 3]
        ),
        integrality=[1, 1, 1, 0],
        bounds=Bounds(0, np.inf),
    )
    assert integer.branch_and_bound(parse_model(mip, True)).result["z"] == pytest.approx(-ref.fun)


def test_binary_formulation_rules():
    r = integer.binary_formulation(
        "max Z = 3x1 + 2x2\nx1 + x2 <= 8\nint x1, x2",
        "either M=100: 3x1 + 2x2 <= 18 | x1 + 4x2 <= 16\nfixed x1: biaya=5, maks=10",
    )
    assert r.result["z"] == 19
    k = integer.binary_formulation("max Z = x1 + x2\nint x1, x2", "k=2 M=100: x1 <= 3 | x2 <= 2 | x1 + x2 <= 4")
    assert k.result["z"] == 5  # dua dari tiga kendala: x1 ≤ 3 dan x2 ≤ 2
    with pytest.raises(SolverError, match="tidak dikenali"):
        integer.binary_formulation("max Z = x1\nx1 <= 3\nint x1", "aturan aneh")


def test_expression_parser():
    assert Expr("12x - 3x^4")([1]) == 9
    assert Expr("ln(x1+1) + 2x2")([0, 1]) == 2
    with pytest.raises(SolverError):
        Expr("__import__('os')")
    with pytest.raises(SolverError):
        Expr("foo(x)")


def test_nlp_hillier_examples():
    assert nonlinear.one_variable("12x - 3x^4 - 2x^6", "bisection", True, 0, 2, None, 0.01).result[
        "x"
    ] == pytest.approx(0.836, abs=2e-3)
    assert nonlinear.one_variable("12x - 3x^4 - 2x^6", "newton", True, None, None, 1, 1e-5).result[
        "x"
    ] == pytest.approx(0.83762, abs=1e-4)
    assert nonlinear.gradient_search("2x1*x2 + 2x2 - x1^2 - 2x2^2", [0, 0], True, 1e-6).result["x"] == pytest.approx(
        [1, 1], abs=1e-4
    )
    k = nonlinear.kkt("ln(x1 + 1) + x2", "2x1 + x2 <= 3", True, True).result
    assert (
        k["x"] == pytest.approx([0, 3], abs=1e-4)
        and k["multipliers"] == pytest.approx([1], abs=1e-3)
        and k["kkt_satisfied"]
    )
    assert nonlinear.quadratic("15x1 + 30x2 + 4x1*x2 - 2x1^2 - 4x2^2", "x1 + 2x2 <= 30").result["x"] == pytest.approx(
        [12, 9]
    )
    assert nonlinear.sumt("x1*x2", "x1^2 + x2 <= 3", [1, 1], True).result["x"] == pytest.approx([1, 2], abs=1e-2)
    fw = nonlinear.frank_wolfe("5x1 - x1^2 + 8x2 - 2x2^2", "3x1 + 2x2 <= 6", [0, 0], True).result
    assert fw["f"] == pytest.approx(11.5, abs=0.02)
    ms = nonlinear.multistart("12x^5 - 975x^4 + 28000x^3 - 345000x^2 + 1800000x", [0], [31], 20, True).result
    assert ms["x"] == pytest.approx([20], abs=1e-2)
    sp = nonlinear.separable("x1: 3x1 - x1^2 ; 0..3\nx2: 5x2 - x2^2 ; 0..5", "x1 + x2 <= 4", 4).result
    assert sp["true_value"] == pytest.approx(8.5, abs=0.3)


def test_qp_rejects_nonconcave():
    with pytest.raises(SolverError, match="konkaf"):
        nonlinear.quadratic("x1^2 + x2", "x1 + x2 <= 4")


def _game_value(a):
    a = np.array(a, float)
    m, n = a.shape
    r = linprog(
        np.r_[np.zeros(m), -1],
        A_ub=np.c_[-a.T, np.ones(n)],
        b_ub=np.zeros(n),
        A_eq=[np.r_[np.ones(m), 0]],
        b_eq=[1],
        bounds=[(0, None)] * m + [(None, None)],
    )
    return -r.fun


def test_games():
    assert games.solve_game([[0, -2, 2], [5, 4, -3], [2, 3, -4]], None, None).result["value"] == pytest.approx(2 / 11)
    assert games.solve_game([[-3, -2, 6], [2, 0, 2], [5, -2, -4]], None, None).result["saddle"] == ["I-2", "II-2"]
    rng = np.random.default_rng(2)
    for _ in range(60):
        m, n = rng.integers(2, 5, 2)
        a = rng.integers(-6, 7, (m, n))
        assert games.solve_game(a.tolist(), None, None).result["value"] == pytest.approx(_game_value(a))


def test_fraction_inputs_exact():
    assert dynamic.resource_allocation([[0, 1, 2]], 2, None, "sum", "max").result["value"] == float(Fraction(2))
