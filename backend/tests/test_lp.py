"""Linear programming: dicocokkan dengan contoh Hillier & Lieberman dan scipy.optimize.linprog."""

from fractions import Fraction

import numpy as np
import pytest
from scipy.optimize import linprog

from app.core.errors import SolverError
from app.solvers.lp import graphical, other, responses, revised, sensitivity, tableau
from app.solvers.lp.model import parse_model

WYNDOR = "max Z = 3x1 + 5x2\nx1 <= 4\n2x2 <= 12\n3x1 + 2x2 <= 18"
RADIATION = "min Z = 0.4x1 + 0.5x2\n0.3x1 + 0.1x2 <= 2.7\n0.5x1 + 0.5x2 = 6\n0.6x1 + 0.4x2 >= 6"


def _linprog(model):
    sign = -1 if model.sense == "max" else 1
    c = [sign * float(x) for x in model.c()]
    a_ub, b_ub, a_eq, b_eq = [], [], [], []
    for row, op, b in zip(model.a(), model.ops(), model.b(), strict=True):
        row = [float(x) for x in row]
        if op == "<=":
            a_ub.append(row), b_ub.append(float(b))
        elif op == ">=":
            a_ub.append([-x for x in row]), b_ub.append(-float(b))
        else:
            a_eq.append(row), b_eq.append(float(b))
    bounds = [
        (None, None) if v in model.free else (None, 0) if v in model.nonpositive else (0, None) for v in model.variables
    ]
    return linprog(c, A_ub=a_ub or None, b_ub=b_ub or None, A_eq=a_eq or None, b_eq=b_eq or None, bounds=bounds)


def test_parser_variants():
    m = parse_model("maximize: 2x + 3y\nx + y ≤ 4\n-x + y >= -2\nx, y >= 0")
    assert m.sense == "max" and m.variables == ["x", "y"] and len(m.constraints) == 2
    with pytest.raises(SolverError, match="Integer"):
        parse_model("max Z = x1\nx1 <= 3\nint x1")
    assert parse_model("max Z = x1\nx1 <= 3\nint x1", allow_integer=True).integer == {"x1"}
    with pytest.raises(SolverError):
        parse_model("Z = 3x1\nx1 <= 4")
    with pytest.raises(SolverError):
        parse_model("max Z = 3x1\nx1 + <= 4")
    assert parse_model("max Z = 0.5x1 + 1/3x2\nx1 + x2 <= 1").objective["x2"] == Fraction(1, 3)


def test_wyndor_simplex():
    out = tableau.solve(parse_model(WYNDOR))
    assert out.status == "optimal" and out.z == 36 and out.x == {"x1": 2, "x2": 6}
    # Hillier: 2 iterasi (tabel awal + 2 iterasi + optimal)
    assert sum("iterasi" in s.title for s in out.steps) == 2


@pytest.mark.parametrize("method", ["bigm", "twophase"])
def test_radiation_bigm_twophase(method):
    out = tableau.solve(parse_model(RADIATION), method)
    assert out.status == "optimal"
    assert out.z == Fraction(21, 4)
    assert out.x == {"x1": Fraction(15, 2), "x2": Fraction(9, 2)}


def test_unbounded_infeasible_multiple():
    assert tableau.solve(parse_model("max Z = 3x1 + 5x2\nx1 <= 4")).status == "unbounded"
    for method in ("bigm", "twophase"):
        assert tableau.solve(parse_model(WYNDOR + "\n3x1 + 5x2 >= 50"), method).status == "infeasible"
    out = tableau.solve(parse_model("max Z = 3x1 + 2x2\nx1 <= 4\n2x2 <= 12\n3x1 + 2x2 <= 18"))
    assert out.z == 18 and out.alternative is not None


@pytest.mark.parametrize(
    "text",
    [
        "max Z = 2x1 - x2 + x3\n3x1 + x2 + x3 <= 60\nx1 - x2 + 2x3 <= 10\nx1 + x2 - x3 <= 20",
        "min Z = 2x1 + 3x2 + x3\nx1 + 4x2 + 2x3 >= 8\n3x1 + 2x2 >= 6",
        "max Z = x1 + x2\nx1 - x2 >= -3\n2x1 + x2 <= 12\nx1 + x2 = 7",
        "min Z = -x1 + 2x2\nx1 + x2 <= 5\n-x1 + x2 <= -1\nx2 free",
        "max Z = 4x1 + 3x2\nx1 + x2 <= 4\nx1 >= -3\nnonpos x1",
    ],
)
def test_matches_linprog(text):
    model = parse_model(text)
    ref = _linprog(model)
    for method in ("bigm", "twophase"):
        out = tableau.solve(model, method)
        if ref.status == 0:
            assert out.status == "optimal"
            assert float(out.z) == pytest.approx(ref.fun * (-1 if model.sense == "max" else 1))
        elif ref.status == 3:
            assert out.status == "unbounded"
        else:
            assert out.status == "infeasible"


def test_degenerate_does_not_cycle():
    # Beale (1955) — siklus pada aturan Dantzig klasik tanpa pengaman
    m = parse_model(
        "min Z = -0.75x4 + 20x5 - 0.5x6 + 6x7\n0.25x4 - 8x5 - x6 + 9x7 <= 0\n0.5x4 - 12x5 - 0.5x6 + 3x7 <= 0\nx6 <= 1"
    )
    out = tableau.solve(m)
    assert out.status == "optimal" and out.z == Fraction(-5, 4)


def test_wyndor_sensitivity_matches_hillier():
    m = parse_model(WYNDOR)
    s = sensitivity.analyze(m, tableau.solve(m))
    assert s.shadow == [0, Fraction(3, 2), 1]
    assert s.rhs_ranges == [(2, None), (6, 18), (12, 24)]
    assert s.obj_ranges == {"x1": (0, Fraction(15, 2)), "x2": (2, None)}


def test_dual_strong_duality():
    for text in (WYNDOR, RADIATION):
        m = parse_model(text)
        dual, _ = sensitivity.dual_model(m)
        assert tableau.solve(dual, "bigm").z == tableau.solve(m, "bigm").z


def test_graphical_and_revised():
    r = graphical.solve_graphical(parse_model(WYNDOR))
    assert r.result["z"] == 36 and len(r.result["corners"]) == 5
    assert graphical.solve_graphical(parse_model(RADIATION)).result["z"] == pytest.approx(5.25)
    with pytest.raises(SolverError):
        graphical.solve_graphical(parse_model("max Z = x1 + x2 + x3\nx1 <= 1"))
    rv = revised.solve_revised(parse_model(WYNDOR))
    assert rv.result["z"] == 36 and rv.result["shadow_prices"] == [0, 1.5, 1]


def test_dual_simplex_and_upper_bound():
    r = other.dual_simplex(parse_model("min W = 4y1 + 12y2 + 18y3\ny1 + 3y3 >= 3\n2y2 + 2y3 >= 5"))
    assert r.result["z"] == 36 and r.result["x"] == {"y1": 0, "y2": 1.5, "y3": 1}
    ub = other.upper_bound(parse_model("max Z = 3x1 + 5x2\nx1 <= 4\nx2 <= 6\n3x1 + 2x2 <= 18"))
    assert ub.result["z"] == 36
    ub2 = other.upper_bound(
        parse_model("max Z = 2x1 + 3x2 + x3\nx1 + x2 + x3 <= 10\n2x1 + x2 <= 12\nx1 <= 3\nx2 <= 4\nx3 <= 8")
    )
    ref = linprog([-2, -3, -1], A_ub=[[1, 1, 1], [2, 1, 0]], b_ub=[10, 12], bounds=[(0, 3), (0, 4), (0, 8)])
    assert ub2.result["z"] == pytest.approx(-ref.fun)


def test_parametric_matches_hillier_7_2():
    r = other.parametric(parse_model(WYNDOR), "objective", [2, -1], 10)
    assert [row[0] for row in r.tables[0].rows] == ["0 ≤ θ ≤ 9/7", "9/7 ≤ θ ≤ 5", "5 ≤ θ ≤ 10"]
    assert [row[2] for row in r.tables[0].rows] == ["36 − 2θ", "27 + 5θ", "12 + 8θ"]


def test_interior_point_converges():
    r = other.interior_point(parse_model("max Z = x1 + 2x2\nx1 + x2 <= 8"), [2, 2])
    assert r.result["z"] == pytest.approx(16, abs=1e-3)
    assert np.allclose(list(r.result["x"].values()), [0, 8], atol=1e-3)


def test_goal_programming_dewright():
    goals = "P1, w=5: 12x1 + 9x2 + 15x3 >= 125\nP1, w-=4, w+=2: 5x1 + 3x2 + 4x3 = 40\nP1, w=3: 5x1 + 7x2 + 8x3 <= 55"
    r = other.goal_programming(goals, "", "weighted")
    assert r.result["x"] == pytest.approx({"x1": 25 / 3, "x2": 0, "x3": 5 / 3})


def test_simplex_response_contains_sensitivity(client):
    res = client.post("/api/lp/simplex", json={"model": WYNDOR})
    body = res.json()
    assert res.status_code == 200 and body["result"]["z"] == 36
    assert [t["title"] for t in body["tables"]][:1] == ["Solusi optimal"]
    bad = client.post("/api/lp/simplex", json={"model": "Z = 3x1"})
    assert bad.status_code == 422 and "max" in bad.json()["detail"]
    assert responses.simplex_response(parse_model("max Z = x1\nx1 >= 2"), "auto").result["status"] == "unbounded"
