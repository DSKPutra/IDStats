"""Proses keputusan Markov (Bab 21): enumerasi + LP, policy improvement (biaya rata-rata & terdiskon),
dan value iteration (successive approximations) dengan faktor diskon.

Format (satu baris per pasangan state–keputusan)::

    state | keputusan | biaya | p(ke state 0) p(ke state 1) …
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items
from app.solvers.lp import tableau
from app.solvers.lp.model import Constraint, LPModel


def _r(x: float) -> float:
    return float(round(x, 6))


@dataclass
class MDP:
    states: list[str]
    actions: dict[int, list[str]]
    cost: dict[tuple[int, str], float]
    prob: dict[tuple[int, str], np.ndarray]


def parse_mdp(text: str) -> MDP:
    rows = []
    for ln, raw in enumerate(text.replace("\r", "").split("\n"), start=1):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 4:
            raise SolverError(f"Baris {ln}: gunakan format “state | keputusan | biaya | peluang transisi …”.")
        try:
            cost = float(parts[2])
            probs = [float(_frac(x)) for x in parts[3].replace(",", " ").split()]
        except ValueError as exc:
            raise SolverError(f"Baris {ln}: biaya dan peluang harus berupa angka (pecahan seperti 7/8 boleh).") from exc
        rows.append((parts[0], parts[1], cost, probs))
    if not rows:
        raise SolverError("Isi data MDP.")
    states = list(dict.fromkeys(r[0] for r in rows))
    m = len(states)
    actions: dict[int, list[str]] = {i: [] for i in range(m)}
    cost, prob = {}, {}
    for s, k, c, p in rows:
        i = states.index(s)
        if len(p) != m:
            raise SolverError(
                f"State {s}, keputusan {k}: harus ada {m} peluang transisi (satu per state, urut seperti kemunculan state)."
            )
        if abs(sum(p) - 1) > 1e-6 or any(x < 0 for x in p):
            raise SolverError(f"State {s}, keputusan {k}: peluang transisi harus nonnegatif dan berjumlah 1.")
        if k in actions[i]:
            raise SolverError(f"Keputusan {k} untuk state {s} ditulis lebih dari sekali.")
        actions[i].append(k)
        cost[(i, k)] = c
        prob[(i, k)] = np.array(p)
    return MDP(states, actions, cost, prob)


def _frac(x: str) -> Fraction:
    return Fraction(x)


def _policy_eval_avg(mdp: MDP, policy: list[str]) -> tuple[float, np.ndarray]:
    """g + vᵢ = Cᵢₖ + Σ pᵢⱼ vⱼ dengan v_m = 0 (state terakhir)."""
    m = len(mdp.states)
    a = np.zeros((m, m))
    b = np.zeros(m)
    for i in range(m):
        k = policy[i]
        p = mdp.prob[(i, k)]
        a[i, 0] = 1.0  # g
        for j in range(m - 1):
            a[i, j + 1] = (1.0 if i == j else 0.0) - p[j]
        b[i] = mdp.cost[(i, k)]
    sol = np.linalg.solve(a, b)
    return float(sol[0]), np.r_[sol[1:], 0.0]


def _policy_eval_disc(mdp: MDP, policy: list[str], alpha: float) -> np.ndarray:
    m = len(mdp.states)
    p = np.array([mdp.prob[(i, policy[i])] for i in range(m)])
    c = np.array([mdp.cost[(i, policy[i])] for i in range(m)])
    return np.linalg.solve(np.eye(m) - alpha * p, c)


def policy_improvement(text: str, discount: float | None) -> SolverResponse:
    mdp = parse_mdp(text)
    m = len(mdp.states)
    policy = [mdp.actions[i][0] for i in range(m)]
    steps: list[Step] = []
    history = []
    for it in range(1, 50):
        if discount is None:
            g, v = _policy_eval_avg(mdp, policy)
            steps.append(
                Step(
                    title=f"Iterasi {it}: penentuan nilai (value determination)",
                    explanation="Selesaikan g + vᵢ = Cᵢₖ + Σⱼ pᵢⱼ(k) vⱼ untuk kebijakan saat ini dengan v terakhir = 0.",
                    latex=rf"g = {g:.4f},\quad \mathbf{{v}} = (" + ", ".join(f"{x:.4f}" for x in v) + ")",
                    table=Table(
                        columns=["State", "Keputusan", "vᵢ"],
                        rows=[[mdp.states[i], policy[i], _r(v[i])] for i in range(m)],
                    ),
                )
            )
            history.append(g)
        else:
            v = _policy_eval_disc(mdp, policy, discount)
            steps.append(
                Step(
                    title=f"Iterasi {it}: penentuan nilai",
                    explanation=f"Selesaikan Vᵢ = Cᵢₖ + α Σⱼ pᵢⱼ(k) Vⱼ dengan α = {discount:g}.",
                    table=Table(
                        columns=["State", "Keputusan", "Vᵢ"],
                        rows=[[mdp.states[i], policy[i], _r(v[i])] for i in range(m)],
                    ),
                )
            )
            history.append(float(v.mean()))
        new_policy = []
        rows = []
        for i in range(m):
            vals = {
                k: mdp.cost[(i, k)] + (discount or 1.0) * float(mdp.prob[(i, k)] @ v) - (0 if discount else v[i])
                for k in mdp.actions[i]
            }
            best_val = min(vals.values())
            keep = policy[i] if abs(vals[policy[i]] - best_val) < 1e-9 else min(vals, key=vals.get)
            new_policy.append(keep)
            rows.append([mdp.states[i], *[f"{k}: {vals[k]:.4f}" for k in mdp.actions[i]], keep])
        width = max(len(r) for r in rows)
        rows = [r[:-1] + [""] * (width - len(r)) + [r[-1]] for r in rows]
        steps.append(
            Step(
                title=f"Iterasi {it}: perbaikan kebijakan (policy improvement)",
                explanation="Untuk setiap state pilih keputusan yang meminimumkan Cᵢₖ + Σⱼ pᵢⱼ(k)vⱼ − vᵢ"
                + (" (dengan faktor diskon)." if discount else "."),
                table=Table(columns=["State", *[f"Pilihan {j + 1}" for j in range(width - 2)], "Terbaik"], rows=rows),
            )
        )
        if new_policy == policy:
            break
        policy = new_policy
    label = "biaya rata-rata jangka panjang" if discount is None else f"biaya terdiskon (α = {discount:g})"
    value = history[-1]
    policy_table = NamedTable(
        title="Kebijakan optimal",
        columns=["State", "Keputusan"],
        rows=[[s, k] for s, k in zip(mdp.states, policy, strict=True)],
    )
    return SolverResponse(
        result={
            "policy": dict(zip(mdp.states, policy, strict=True)),
            "value": value if discount is None else v.tolist(),
        },
        steps=steps,
        tables=[policy_table],
        charts=[
            Chart(
                id="pi-history",
                title="Konvergensi",
                spec=plotly_figure(
                    [{"type": "scatter", "mode": "lines+markers", "x": list(range(1, len(history) + 1)), "y": history}],
                    "Nilai kebijakan per iterasi",
                    xaxis={"title": {"text": "Iterasi"}},
                ),
            )
        ],
        summary=summary_items(
            [(f"Keputusan di state {s}", k) for s, k in zip(mdp.states, policy, strict=True)]
            + (
                [("Biaya rata-rata jangka panjang g", _r(value))]
                if discount is None
                else [(f"V({s})", _r(x)) for s, x in zip(mdp.states, v, strict=True)]
            )
        ),
        conclusion=f"Kebijakan optimal ({label}): "
        + ", ".join(f"state {s} → {k}" for s, k in zip(mdp.states, policy, strict=True))
        + (f"; biaya rata-rata = {value:.4f}." if discount is None else "."),
    )


def value_iteration(text: str, discount: float, iterations: int, tol: float) -> SolverResponse:
    mdp = parse_mdp(text)
    if not 0 < discount < 1:
        raise SolverError("Faktor diskon α harus di antara 0 dan 1.")
    m = len(mdp.states)
    v = np.zeros(m)
    rows = []
    policy = [""] * m
    for n in range(1, iterations + 1):
        new_v = np.zeros(m)
        for i in range(m):
            vals = {k: mdp.cost[(i, k)] + discount * float(mdp.prob[(i, k)] @ v) for k in mdp.actions[i]}
            policy[i] = min(vals, key=vals.get)
            new_v[i] = vals[policy[i]]
        diff = float(np.max(np.abs(new_v - v)))
        rows.append([n, *[_r(x) for x in new_v], ", ".join(policy), _r(diff)])
        v = new_v
        if diff < tol:
            break
    table = NamedTable(
        title="Iterasi value iteration",
        columns=["n", *[f"V({s})" for s in mdp.states], "Kebijakan", "max |ΔV|"],
        rows=rows if len(rows) <= 40 else rows[:30] + rows[-5:],
    )
    return SolverResponse(
        result={"policy": dict(zip(mdp.states, policy, strict=True)), "values": v.tolist(), "iterations": len(rows)},
        steps=[
            Step(
                title="Successive approximations",
                latex=r"V_i^{(n)} = \min_k \left\{C_{ik} + \alpha\sum_j p_{ij}(k)\, V_j^{(n-1)}\right\},\quad V^{(0)} = 0",
                explanation=f"α = {discount:g}. Berhenti bila perubahan maksimum < {tol:g} atau setelah {iterations} iterasi.",
                table=table,
            )
        ],
        tables=[table],
        summary=summary_items(
            [(f"Keputusan di state {s}", k) for s, k in zip(mdp.states, policy, strict=True)] + [("Iterasi", len(rows))]
        ),
        conclusion="Kebijakan (value iteration): "
        + ", ".join(f"state {s} → {k}" for s, k in zip(mdp.states, policy, strict=True))
        + f" setelah {len(rows)} iterasi.",
    )


def lp_formulation(text: str) -> SolverResponse:
    """Min Σ Cᵢₖ yᵢₖ s.t. Σ yᵢₖ = 1, Σₖ yⱼₖ − Σᵢ Σₖ yᵢₖ pᵢⱼ(k) = 0 (j = 1..M−1). Diselesaikan dengan simpleks (pecahan)."""
    mdp = parse_mdp(text)
    m = len(mdp.states)
    pairs = [(i, k) for i in range(m) for k in mdp.actions[i]]
    names = {pk: f"y{pk[0]}_{pk[1]}".replace(" ", "_") for pk in pairs}

    def fr(x: float) -> Fraction:
        return Fraction(x).limit_denominator(10**6)

    obj = {names[pk]: fr(mdp.cost[pk]) for pk in pairs}
    cons = [Constraint({names[pk]: Fraction(1) for pk in pairs}, "=", Fraction(1), name="Σ y = 1")]
    for j in range(m - 1):
        coeffs: dict[str, Fraction] = {}
        for pk in pairs:
            c = (Fraction(1) if pk[0] == j else Fraction(0)) - fr(mdp.prob[pk][j])
            if c:
                coeffs[names[pk]] = coeffs.get(names[pk], Fraction(0)) + c
        cons.append(Constraint(coeffs, "=", Fraction(0), name=f"Keseimbangan state {mdp.states[j]}"))
    model = LPModel("min", obj, cons, [names[pk] for pk in pairs], objective_name="E[C]")
    out = tableau.solve(model, "bigm", record=False)
    if out.status != "optimal":
        raise SolverError("LP tidak memiliki solusi optimal.")
    policy = {}
    rows = []
    for i in range(m):
        total = sum(float(out.x[names[(i, k)]]) for k in mdp.actions[i])
        for k in mdp.actions[i]:
            y = float(out.x[names[(i, k)]])
            d = y / total if total > 1e-12 else (1.0 if k == mdp.actions[i][0] else 0.0)
            rows.append([mdp.states[i], k, _r(y), _r(d)])
            if d > 0.5:
                policy[mdp.states[i]] = k
    table = NamedTable(
        title="Solusi LP: yᵢₖ = P(state i dan keputusan k), Dᵢₖ = yᵢₖ / Σₖ yᵢₖ",
        columns=["State", "Keputusan", "yᵢₖ", "Dᵢₖ"],
        rows=rows,
    )
    return SolverResponse(
        result={"policy": policy, "value": float(out.z)},
        steps=[
            Step(
                title="Formulasi LP",
                latex=r"\min \sum_i\sum_k C_{ik} y_{ik}\ \text{s.t.}\ \sum_i\sum_k y_{ik} = 1,\ \sum_k y_{jk} - \sum_i\sum_k y_{ik}p_{ij}(k) = 0,\ y_{ik} \ge 0",
                explanation="yᵢₖ adalah peluang steady-state tak bersyarat berada di state i dan mengambil keputusan k. Solusi basis optimal memberi kebijakan deterministik.",
            ),
            Step(title="Solusi (simpleks)", table=table, latex=rf"E[C]^* = {float(out.z):.4f}"),
        ],
        tables=[table],
        summary=summary_items(
            [(f"Keputusan di state {s}", k) for s, k in policy.items()]
            + [("Biaya harapan jangka panjang", _r(float(out.z)))]
        ),
        conclusion="Kebijakan optimal (LP): "
        + ", ".join(f"state {s} → {k}" for s, k in policy.items())
        + f"; biaya rata-rata = {float(out.z):.4f}.",
    )
