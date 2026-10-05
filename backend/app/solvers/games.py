"""Teori permainan (Bab 14): permainan dua pemain jumlah nol — titik pelana, strategi dominan,
strategi campuran dengan metode grafik (2×n / m×2) dan dengan LP (simpleks sendiri)."""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items
from app.solvers.lp import tableau
from app.solvers.lp.model import Constraint, LPModel
from app.solvers.lp.numbers import fmt_frac, frac


def _tbl(a: list[list[Fraction]], rows: list[str], cols: list[str]) -> Table:
    return Table(columns=["", *cols], rows=[[r, *[fmt_frac(x) for x in row]] for r, row in zip(rows, a, strict=True)])


def _dominance(a, rows, cols, steps):
    changed = True
    while changed:
        changed = False
        # baris (pemain I memaksimumkan): baris i didominasi bila ada k dengan a[k] ≥ a[i] di semua kolom
        for i in range(len(a)):
            for k in range(len(a)):
                if i != k and all(a[k][j] >= a[i][j] for j in range(len(cols))):
                    steps.append(
                        Step(
                            title=f"Strategi {rows[i]} didominasi oleh {rows[k]}",
                            explanation=f"Setiap payoff {rows[k]} ≥ payoff {rows[i]} untuk pemain I, sehingga {rows[i]} dihapus.",
                            table=_tbl(a, rows, cols),
                        )
                    )
                    del a[i]
                    del rows[i]
                    changed = True
                    break
            if changed:
                break
        if changed:
            continue
        # kolom (pemain II meminimumkan): kolom j didominasi bila ada l dengan a[:, l] ≤ a[:, j]
        for j in range(len(cols)):
            for l_ in range(len(cols)):
                if j != l_ and all(a[i][l_] <= a[i][j] for i in range(len(a))):
                    steps.append(
                        Step(
                            title=f"Strategi {cols[j]} didominasi oleh {cols[l_]}",
                            explanation=f"Untuk pemain II (meminimumkan payoff pemain I), {cols[l_]} selalu ≤ {cols[j]}, sehingga {cols[j]} dihapus.",
                            table=_tbl(a, rows, cols),
                        )
                    )
                    for r in a:
                        del r[j]
                    del cols[j]
                    changed = True
                    break
            if changed:
                break
    return a, rows, cols


def _lp_solution(a: list[list[Fraction]]):
    """Pemain I: maks v dengan Σᵢ pᵢaᵢⱼ ≥ v, Σ pᵢ = 1; nilai digeser agar positif (v bebas tanda ditangani dengan geser)."""
    m, n = len(a), len(a[0])
    shift = max(Fraction(0), -min(min(r) for r in a) + 1)
    b = [[x + shift for x in r] for r in a]
    ps = [f"p{i + 1}" for i in range(m)]
    cons = [
        Constraint({**{ps[i]: b[i][j] for i in range(m)}, "v": Fraction(-1)}, ">=", Fraction(0), name=f"Kolom {j + 1}")
        for j in range(n)
    ]
    cons.append(Constraint({p: Fraction(1) for p in ps}, "=", Fraction(1), name="Σp = 1"))
    out = tableau.solve(LPModel("max", {"v": Fraction(1)}, cons, ps + ["v"]), "bigm", record=False)
    qs = [f"q{j + 1}" for j in range(n)]
    cons2 = [
        Constraint({**{qs[j]: b[i][j] for j in range(n)}, "w": Fraction(-1)}, "<=", Fraction(0), name=f"Baris {i + 1}")
        for i in range(m)
    ]
    cons2.append(Constraint({q: Fraction(1) for q in qs}, "=", Fraction(1), name="Σq = 1"))
    out2 = tableau.solve(LPModel("min", {"w": Fraction(1)}, cons2, qs + ["w"]), "bigm", record=False)
    return [out.x[p] for p in ps], [out2.x[q] for q in qs], out.z - shift, shift


def solve_game(payoff: list[list[float]], row_names: list[str] | None, col_names: list[str] | None) -> SolverResponse:
    if not payoff or not payoff[0] or any(len(r) != len(payoff[0]) for r in payoff):
        raise SolverError("Matriks payoff harus persegi panjang dan tidak kosong.")
    m, n = len(payoff), len(payoff[0])
    rows = list(row_names) if row_names and len(row_names) == m else [f"I-{i + 1}" for i in range(m)]
    cols = list(col_names) if col_names and len(col_names) == n else [f"II-{j + 1}" for j in range(n)]
    a = [[frac(x) for x in r] for r in payoff]
    orig_rows, orig_cols = list(rows), list(cols)
    steps = [
        Step(
            title="Matriks payoff (untuk pemain I)",
            explanation="Permainan jumlah nol: keuntungan pemain I = kerugian pemain II.",
            table=_tbl(a, rows, cols),
        )
    ]
    row_min = [min(r) for r in a]
    col_max = [max(a[i][j] for i in range(m)) for j in range(n)]
    maximin, minimax = max(row_min), min(col_max)
    steps.append(
        Step(
            title="Kriteria minimaks: cari titik pelana",
            explanation=f"Maksimin (nilai bawah) = maks min baris = {fmt_frac(maximin)}; minimaks (nilai atas) = min maks kolom = {fmt_frac(minimax)}.",
            table=Table(
                columns=["", *cols, "Min baris"],
                rows=[
                    [r, *[fmt_frac(x) for x in row], fmt_frac(mn)] for r, row, mn in zip(rows, a, row_min, strict=True)
                ]
                + [["Maks kolom", *[fmt_frac(x) for x in col_max], ""]],
            ),
        )
    )
    if maximin == minimax:
        i = row_min.index(maximin)
        j = col_max.index(minimax)
        steps.append(
            Step(
                title="Titik pelana ditemukan",
                explanation=f"Maksimin = minimaks = {fmt_frac(maximin)}: permainan stabil dengan strategi murni {rows[i]} vs {cols[j]}.",
            )
        )
        return SolverResponse(
            result={
                "value": float(maximin),
                "saddle": [rows[i], cols[j]],
                "p": [1.0 if k == i else 0.0 for k in range(m)],
                "q": [1.0 if k == j else 0.0 for k in range(n)],
            },
            steps=steps,
            summary=summary_items(
                [
                    ("Nilai permainan", fmt_frac(maximin)),
                    ("Strategi pemain I", rows[i]),
                    ("Strategi pemain II", cols[j]),
                ]
            ),
            conclusion=f"Titik pelana di ({rows[i]}, {cols[j]}); nilai permainan = {fmt_frac(maximin)}. Kedua pemain memakai strategi murni.",
        )
    a, rows, cols = _dominance(a, rows, cols, steps)
    steps.append(Step(title="Matriks setelah eliminasi dominasi", table=_tbl(a, rows, cols)))
    p, q, v, shift = _lp_solution(a)
    charts = []
    if len(rows) == 2 or len(cols) == 2:
        charts.append(_graphical_chart(a, rows, cols, p, q, v))
        steps.append(
            Step(
                title="Metode grafik",
                explanation=(
                    "Pemain I dengan 2 strategi: payoff harapan untuk setiap strategi murni pemain II adalah garis terhadap p₁. "
                    "Pemain I memilih p₁ yang memaksimumkan amplop bawah (titik tertinggi batas bawah)."
                    if len(rows) == 2
                    else "Pemain II dengan 2 strategi: payoff harapan untuk setiap strategi pemain I adalah garis terhadap q₁. "
                    "Pemain II memilih q₁ yang meminimumkan amplop atas."
                ),
            )
        )
    steps.append(
        Step(
            title="Formulasi LP strategi campuran",
            explanation=f"Payoff digeser +{fmt_frac(shift)} agar nilai permainan positif. Pemain I: maks v s.t. Σᵢ pᵢaᵢⱼ ≥ v (semua j), Σpᵢ = 1. "
            "Pemain II adalah dual-nya: min v s.t. Σⱼ qⱼaᵢⱼ ≤ v. Diselesaikan dengan simpleks.",
            latex=r"\max v\quad\text{s.t.}\quad \sum_i p_i a_{ij} \ge v\ (\forall j),\ \sum_i p_i = 1,\ p_i \ge 0",
        )
    )
    p_full = [Fraction(0)] * m
    for name, val in zip(rows, p, strict=True):
        p_full[orig_rows.index(name)] = val
    q_full = [Fraction(0)] * n
    for name, val in zip(cols, q, strict=True):
        q_full[orig_cols.index(name)] = val
    strat = NamedTable(
        title="Strategi campuran optimal",
        columns=["Pemain", "Strategi", "Peluang"],
        rows=[["I", r, fmt_frac(x)] for r, x in zip(orig_rows, p_full, strict=True)]
        + [["II", c, fmt_frac(x)] for c, x in zip(orig_cols, q_full, strict=True)],
    )
    steps.append(Step(title="Solusi", table=strat, latex=rf"v = {fmt_frac(v)}"))
    return SolverResponse(
        result={"value": float(v), "p": [float(x) for x in p_full], "q": [float(x) for x in q_full]},
        steps=steps,
        tables=[strat],
        charts=charts,
        summary=summary_items(
            [("Nilai permainan", fmt_frac(v))]
            + [(f"P(I memilih {r})", fmt_frac(x)) for r, x in zip(orig_rows, p_full, strict=True)]
            + [(f"P(II memilih {c})", fmt_frac(x)) for c, x in zip(orig_cols, q_full, strict=True)]
        ),
        conclusion=f"Tidak ada titik pelana; strategi campuran optimal memberi nilai permainan {fmt_frac(v)}.",
    )


def _graphical_chart(a, rows, cols, p, q, v) -> Chart:
    xs = np.linspace(0, 1, 101)
    traces = []
    if len(rows) == 2:
        for j, c in enumerate(cols):
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": xs.tolist(),
                    "y": [float(a[0][j]) * t + float(a[1][j]) * (1 - t) for t in xs],
                    "name": f"{c}",
                }
            )
        env = [min(float(a[0][j]) * t + float(a[1][j]) * (1 - t) for j in range(len(cols))) for t in xs]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "x": xs.tolist(),
                "y": env,
                "line": {"width": 5, "color": "rgba(239,68,68,0.5)"},
                "name": "Amplop bawah",
            }
        )
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "x": [float(p[0])],
                "y": [float(v)],
                "marker": {"size": 14, "color": "#ef4444", "symbol": "star"},
                "name": "Optimum",
            }
        )
        xt = f"p₁ = P(pemain I memilih {rows[0]})"
    else:
        for i, r in enumerate(rows):
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": xs.tolist(),
                    "y": [float(a[i][0]) * t + float(a[i][1]) * (1 - t) for t in xs],
                    "name": f"{r}",
                }
            )
        env = [max(float(a[i][0]) * t + float(a[i][1]) * (1 - t) for i in range(len(rows))) for t in xs]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "x": xs.tolist(),
                "y": env,
                "line": {"width": 5, "color": "rgba(239,68,68,0.5)"},
                "name": "Amplop atas",
            }
        )
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "x": [float(q[0])],
                "y": [float(v)],
                "marker": {"size": 14, "color": "#ef4444", "symbol": "star"},
                "name": "Optimum",
            }
        )
        xt = f"q₁ = P(pemain II memilih {cols[0]})"
    return Chart(
        id="game-graphical",
        title="Metode grafik",
        spec=plotly_figure(
            traces,
            "Payoff harapan",
            xaxis={"title": {"text": xt}},
            yaxis={"title": {"text": "Payoff harapan pemain I"}},
        ),
    )
