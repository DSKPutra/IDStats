"""Bab 8–10: dicocokkan dengan contoh Hillier & Lieberman, scipy, dan networkx."""

import networkx as nx
import numpy as np
import pytest
from scipy.optimize import linear_sum_assignment, linprog

from app.core.errors import SolverError
from app.solvers import network, project, transport

PT = ([[464, 513, 654, 867], [352, 416, 690, 791], [995, 682, 388, 685]], [75, 125, 100], [80, 65, 70, 85])
PARK = "O A 2\nO B 5\nO C 4\nA B 2\nA D 7\nB C 1\nB D 4\nB E 3\nC E 4\nD E 1\nD T 5\nE T 7"
REL = "A | - | 2\nB | A | 4\nC | B | 10\nD | C | 6\nE | C | 4\nF | E | 5\nG | D | 7\nH | E, G | 9\nI | C | 7\nJ | F, I | 8\nK | J | 4\nL | J | 5\nM | H | 2\nN | K, L | 6"


def _lp_transport(c, s, d):
    c = np.array(c, float)
    m, n = c.shape
    a_ub = [np.kron(np.eye(m)[i], np.ones(n)) for i in range(m)] + [-np.tile(np.eye(n)[j], m) for j in range(n)]
    return linprog(c.ravel(), A_ub=a_ub, b_ub=list(s) + [-x for x in d]).fun


@pytest.mark.parametrize("method", ["nwc", "least_cost", "vam"])
def test_pt_company_optimal(method):
    r = transport.solve_transportation(*PT, method, True)
    assert r.result["total_cost"] == 152535


def test_transport_random_vs_linprog():
    rng = np.random.default_rng(0)
    for _ in range(60):
        m, n = rng.integers(2, 5, 2)
        c, s = rng.integers(1, 30, (m, n)).tolist(), rng.integers(5, 40, m).tolist()
        d = rng.integers(5, 40, n).tolist()
        r = transport.solve_transportation(c, s, d, "vam", True)
        if sum(s) >= sum(d):
            ref = _lp_transport(c, s, d)
        else:
            ref = _lp_transport(c + [[0] * n], s + [sum(d) - sum(s)], d)
        assert r.result["total_cost"] == pytest.approx(ref)


def test_transport_validation():
    with pytest.raises(SolverError, match="penawaran"):
        transport.solve_transportation([[1, 2]], [1, 2], [1, 2], "vam", True)


@pytest.mark.parametrize("maximize", [False, True])
def test_hungarian_random(maximize):
    rng = np.random.default_rng(3)
    for _ in range(80):
        m, n = rng.integers(2, 7, 2)
        c = rng.integers(0, 25, (m, n))
        r, cc = linear_sum_assignment(c, maximize=maximize)
        assert transport.solve_assignment(c.tolist(), maximize).result["total"] == c[r, cc].sum()


def test_job_shop_assignment():
    r = transport.solve_assignment([[13, 16, 12, 11], [15, 99, 13, 20], [5, 7, 10, 6]], False)
    assert r.result["total"] == 29  # Hillier: mesin 1→4, mesin 2→3, mesin 3→1


def test_seervada_park():
    assert network.shortest_path(PARK, "O", "T", False).result["distance"] == 13
    for alg in ("prim", "kruskal"):
        assert network.minimum_spanning_tree(PARK, alg).result["total"] == 14
    mf = "O A 5\nO B 7\nO C 4\nA B 1\nA D 3\nB C 2\nB D 4\nB E 5\nC E 4\nD T 9\nE D 1\nE T 6"
    assert network.max_flow(mf, "O", "T").result["max_flow"] == 14


@pytest.mark.parametrize("fn", [network.min_cost_flow, network.network_simplex])
def test_distribution_unlimited(fn):
    arcs = "A B 2 10\nA C 4 inf\nA D 9 inf\nB C 3 inf\nC E 1 80\nD E 3 inf\nE D 2 inf"
    assert fn(arcs, "A 50\nB 40\nD -30\nE -60").result["total_cost"] == 490


def test_network_random_vs_networkx():
    rng = np.random.default_rng(1)
    checked = 0
    for _ in range(80):
        n = int(rng.integers(4, 8))
        names = [f"N{i}" for i in range(n)]
        g = nx.DiGraph()
        lines = []
        for i in range(n):
            for j in range(n):
                if i != j and rng.random() < 0.45:
                    c, cap = int(rng.integers(1, 10)), int(rng.integers(1, 15))
                    lines.append(f"{names[i]} {names[j]} {c} {cap}")
                    g.add_edge(names[i], names[j], weight=c, capacity=cap)
        nodes = [x for x in names if x in g]
        if len(nodes) < 2 or not nx.has_path(g, nodes[0], nodes[-1]):
            continue
        checked += 1
        sp = "\n".join(" ".join(ln.split()[:3]) for ln in lines)
        assert network.shortest_path(sp, nodes[0], nodes[-1], True).result["distance"] == nx.shortest_path_length(
            g, nodes[0], nodes[-1], weight="weight"
        )
        mf = "\n".join(f"{ln.split()[0]} {ln.split()[1]} {ln.split()[3]}" for ln in lines)
        flow = nx.maximum_flow_value(g, nodes[0], nodes[-1])
        assert network.max_flow(mf, nodes[0], nodes[-1]).result["max_flow"] == flow
        k = int(min(5, flow))
        h = g.copy()
        h.nodes[nodes[0]]["demand"], h.nodes[nodes[-1]]["demand"] = -k, k
        ref = nx.min_cost_flow_cost(h)
        sup = f"{nodes[0]} {k}\n{nodes[-1]} {-k}"
        assert network.min_cost_flow("\n".join(lines), sup).result["total_cost"] == ref
        assert network.network_simplex("\n".join(lines), sup).result["total_cost"] == ref
    assert checked > 40


def test_network_validation():
    with pytest.raises(SolverError, match="tidak ada"):
        network.shortest_path(PARK, "O", "Z", False)
    with pytest.raises(SolverError, match="Total penawaran"):
        network.min_cost_flow("A B 1 5", "A 5\nB -4")


def test_reliable_construction():
    r = project.cpm(REL)
    assert r.result["duration"] == 44
    assert r.result["critical_paths"] == [["A", "B", "C", "E", "F", "J", "L", "N"]]
    pe = "A | - | 1 2 3\nB | A | 2 3.5 8\nC | B | 6 9 18\nD | C | 4 5.5 10\nE | C | 1 4.5 5\nF | E | 4 4 10\nG | D | 5 6.5 11\nH | E, G | 5 8 17\nI | C | 3 7.5 9\nJ | F, I | 3 9 9\nK | J | 4 4 4\nL | J | 1 5.5 7\nM | H | 1 2 3\nN | K, L | 5 5.5 9"
    p = project.pert(pe, 47).result
    assert p["mean_duration"] == 44 and p["variance"] == 9
    assert p["deadline_probability"] == pytest.approx(0.8413, abs=1e-4)


def test_crashing_reliable():
    cr = "A | - | 2 1 180 280\nB | A | 4 2 320 420\nC | B | 10 7 620 860\nD | C | 6 4 260 340\nE | C | 4 3 410 570\nF | E | 5 3 180 260\nG | D | 7 4 900 1020\nH | E, G | 9 6 200 380\nI | C | 7 5 210 270\nJ | F, I | 8 6 430 490\nK | J | 4 3 160 200\nL | J | 5 3 250 350\nM | H | 2 1 100 200\nN | K, L | 6 3 330 510"
    r = project.crashing(cr, 40).result
    assert r["crash_cost"] == 140 and r["duration"] <= 40
    with pytest.raises(SolverError, match="tidak dapat dicapai"):
        project.crashing(cr, 20)


def test_project_validation():
    with pytest.raises(SolverError, match="siklus"):
        project.cpm("A | B | 1\nB | A | 2")
    with pytest.raises(SolverError, match="tidak ada"):
        project.cpm("A | Z | 1")
