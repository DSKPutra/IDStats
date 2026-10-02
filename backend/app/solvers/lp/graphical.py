"""Metode grafik untuk LP dua variabel (Bab 3): garis kendala, daerah layak, titik sudut, garis isoprofit."""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from typing import Any

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step
from app.solvers._base import plotly_figure, summary_items
from app.solvers.lp import tableau
from app.solvers.lp.model import LPModel
from app.solvers.lp.numbers import fmt_frac, latex_frac

Line = tuple[Fraction, Fraction, Fraction]  # a·x + b·y = c


def _intersect(l1: Line, l2: Line) -> tuple[Fraction, Fraction] | None:
    a1, b1, c1 = l1
    a2, b2, c2 = l2
    det = a1 * b2 - a2 * b1
    if det == 0:
        return None
    return (c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det


def _feasible(model: LPModel, p: tuple[Fraction, Fraction], extra: list[tuple[Line, str]] | None = None) -> bool:
    x, y = p
    v1, v2 = model.variables
    for v, val in ((v1, x), (v2, y)):
        if v not in model.free and val < 0:
            return False
    for k in model.constraints:
        lhs = k.coeffs.get(v1, 0) * x + k.coeffs.get(v2, 0) * y
        if (k.op == "<=" and lhs > k.rhs) or (k.op == ">=" and lhs < k.rhs) or (k.op == "=" and lhs != k.rhs):
            return False
    for (a, b, c), op in extra or []:
        lhs = a * x + b * y
        if (op == "<=" and lhs > c) or (op == ">=" and lhs < c):
            return False
    return True


def _lines(model: LPModel) -> list[tuple[Line, str]]:
    v1, v2 = model.variables
    lines = [((k.coeffs.get(v1, Fraction(0)), k.coeffs.get(v2, Fraction(0)), k.rhs), k.name) for k in model.constraints]
    if v1 not in model.free:
        lines.append(((Fraction(1), Fraction(0), Fraction(0)), f"{v1} = 0"))
    if v2 not in model.free:
        lines.append(((Fraction(0), Fraction(1), Fraction(0)), f"{v2} = 0"))
    return lines


def _corners(model: LPModel, lines: list[tuple[Line, str]], extra=None) -> list[tuple[Fraction, Fraction]]:
    pts = []
    for (l1, _), (l2, _) in combinations(lines, 2):
        p = _intersect(l1, l2)
        if p is not None and _feasible(model, p, extra) and p not in pts:
            pts.append(p)
    return pts


def _polygon(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    import math

    if len(points) < 3:
        return points
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return sorted(points, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


def solve_graphical(model: LPModel) -> SolverResponse:
    if len(model.variables) != 2:
        raise SolverError(
            f"Metode grafik hanya untuk 2 variabel keputusan (model ini memiliki {len(model.variables)})."
        )
    v1, v2 = model.variables
    lines = _lines(model)
    corners = _corners(model, lines)
    out = tableau.solve(model, "bigm")
    steps = [
        Step(title="Model", latex=model.latex()),
        Step(
            title="Gambar garis batas setiap kendala",
            explanation="Ubah setiap pertidaksamaan menjadi persamaan untuk mendapatkan garis batasnya, lalu tentukan sisi "
            "yang memenuhi pertidaksamaan. Irisan semua sisi tersebut adalah daerah layak (feasible region).",
            latex=r"\begin{aligned}"
            + r"\\ ".join(
                rf"&{k.name}:\ {_line_latex(k.coeffs.get(v1, Fraction(0)), k.coeffs.get(v2, Fraction(0)), v1, v2)} = {latex_frac(k.rhs)}"
                for k in model.constraints
            )
            + r"\end{aligned}",
        ),
    ]
    rows = []
    best = None
    for p in corners:
        z = model.objective.get(v1, Fraction(0)) * p[0] + model.objective.get(v2, Fraction(0)) * p[1]
        rows.append([fmt_frac(p[0]), fmt_frac(p[1]), fmt_frac(z)])
        if best is None or (z > best[1] if model.sense == "max" else z < best[1]):
            best = (p, z)
    table = NamedTable(title="Titik sudut daerah layak", columns=[f"{v1}", f"{v2}", model.objective_name], rows=rows)

    status = out.status
    if status == "infeasible" or not corners:
        steps.append(
            Step(
                title="Daerah layak kosong",
                explanation="Tidak ada titik yang memenuhi semua kendala: masalah tidak layak.",
            )
        )
        return SolverResponse(
            result={"status": "infeasible"},
            steps=steps,
            charts=[_chart(model, [], None, None)],
            conclusion="Masalah tidak memiliki solusi layak.",
            summary=summary_items([("Status", "Tidak layak")]),
        )
    steps.append(
        Step(
            title="Hitung titik-titik sudut (corner-point feasible solutions)",
            explanation="Titik sudut = perpotongan dua garis batas yang memenuhi semua kendala. Bila solusi optimal ada, "
            "salah satunya pasti berada di titik sudut.",
            table=table,
        )
    )
    if status == "unbounded":
        steps.append(
            Step(
                title="Daerah layak tidak terbatas",
                explanation="Garis isoprofit dapat digeser terus ke arah perbaikan tanpa meninggalkan daerah layak: Z tak terbatas.",
            )
        )
        return SolverResponse(
            result={"status": "unbounded", "corners": [[float(a), float(b)] for a, b in corners]},
            steps=steps,
            tables=[table],
            charts=[_chart(model, corners, None, None)],
            conclusion=f"{model.objective_name} tak terbatas (unbounded).",
            summary=summary_items([("Status", "Tak terbatas")]),
        )
    opt_p = (out.x[v1], out.x[v2])
    z = out.z
    alt = out.alternative
    steps.append(
        Step(
            title="Geser garis isoprofit / bandingkan nilai Z",
            explanation=f"Garis {model.objective_name} = k digeser ke arah {'naiknya' if model.sense == 'max' else 'turunnya'} Z sampai "
            "terakhir kali menyentuh daerah layak. Titik sentuh terakhir adalah solusi optimal."
            + (
                " Garis isoprofit sejajar dengan salah satu kendala, sehingga solusi optimal tidak tunggal."
                if alt
                else ""
            ),
            latex=rf"({v1}^*, {v2}^*) = ({latex_frac(opt_p[0])}, {latex_frac(opt_p[1])}),\quad {model.objective_name}^* = {latex_frac(z)}",
        )
    )
    conclusion = f"Solusi optimal: {v1} = {fmt_frac(opt_p[0])}, {v2} = {fmt_frac(opt_p[1])}, dengan {model.objective_name} = {fmt_frac(z)}."
    if alt:
        conclusion += f" Solusi optimal tidak tunggal; titik ({fmt_frac(alt[v1])}, {fmt_frac(alt[v2])}) juga optimal."
    return SolverResponse(
        result={
            "status": "optimal",
            "x": {v1: float(opt_p[0]), v2: float(opt_p[1])},
            "z": float(z),
            "corners": [[float(a), float(b)] for a, b in corners],
            "multiple": bool(alt),
        },
        steps=steps,
        tables=[table],
        charts=[_chart(model, corners, opt_p, z)],
        summary=summary_items(
            [(v1, fmt_frac(opt_p[0])), (v2, fmt_frac(opt_p[1])), (f"{model.objective_name}*", fmt_frac(z))]
        ),
        conclusion=conclusion,
    )


def _line_latex(a: Fraction, b: Fraction, v1: str, v2: str) -> str:
    from app.solvers.lp.model import linear_latex

    return linear_latex({v1: a, v2: b}, [v1, v2])


def _chart(model: LPModel, corners, opt, z) -> Chart:
    v1, v2 = model.variables
    xs = [float(p[0]) for p in corners] or [0.0]
    ys = [float(p[1]) for p in corners] or [0.0]
    for k in model.constraints:
        a, b = k.coeffs.get(v1, Fraction(0)), k.coeffs.get(v2, Fraction(0))
        if a:
            xs.append(float(k.rhs / a))
        if b:
            ys.append(float(k.rhs / b))
    xmax = max(max(xs) * 1.25, 1.0)
    ymax = max(max(ys) * 1.25, 1.0)
    xmin = min(min(xs) * 1.25, 0.0) if v1 in model.free else 0.0
    ymin = min(min(ys) * 1.25, 0.0) if v2 in model.free else 0.0
    traces: list[dict[str, Any]] = []
    # daerah layak ∩ kotak gambar
    box = [
        ((Fraction(1), Fraction(0), Fraction(xmax).limit_denominator(1000)), "<="),
        ((Fraction(0), Fraction(1), Fraction(ymax).limit_denominator(1000)), "<="),
    ]
    if v1 in model.free:
        box.append(((Fraction(1), Fraction(0), Fraction(xmin).limit_denominator(1000)), ">="))
    if v2 in model.free:
        box.append(((Fraction(0), Fraction(1), Fraction(ymin).limit_denominator(1000)), ">="))
    region = _corners(model, _lines(model) + [(ln, "kotak") for ln, _ in box], box)
    poly = _polygon([(float(a), float(b)) for a, b in region])
    if poly:
        traces.append(
            {
                "type": "scatter",
                "x": [p[0] for p in poly] + [poly[0][0]],
                "y": [p[1] for p in poly] + [poly[0][1]],
                "fill": "toself",
                "mode": "lines",
                "line": {"width": 0},
                "fillcolor": "rgba(99,102,241,0.18)",
                "name": "Daerah layak",
            }
        )
    for k in model.constraints:
        a, b, c = float(k.coeffs.get(v1, 0)), float(k.coeffs.get(v2, 0)), float(k.rhs)
        if b != 0:
            lx = [xmin, xmax]
            ly = [(c - a * xmin) / b, (c - a * xmax) / b]
        else:
            lx = [c / a, c / a]
            ly = [ymin, ymax]
        traces.append({"type": "scatter", "mode": "lines", "x": lx, "y": ly, "name": f"{k.name}: {_plain(k, v1, v2)}"})
    if corners:
        traces.append(
            {
                "type": "scatter",
                "mode": "markers+text",
                "x": [float(p[0]) for p in corners],
                "y": [float(p[1]) for p in corners],
                "text": [f"({fmt_frac(p[0])}, {fmt_frac(p[1])})" for p in corners],
                "textposition": "top right",
                "marker": {"size": 8, "color": "#64748b"},
                "name": "Titik sudut",
            }
        )
    if opt is not None:
        c1, c2 = float(model.objective.get(v1, 0)), float(model.objective.get(v2, 0))
        for frac_k, dash in ((1 / 3, "dot"), (2 / 3, "dot"), (1.0, "dash")):
            k_val = float(z) * frac_k
            if c2 != 0:
                lx = [xmin, xmax]
                ly = [(k_val - c1 * xmin) / c2, (k_val - c1 * xmax) / c2]
            elif c1 != 0:
                lx, ly = [k_val / c1] * 2, [ymin, ymax]
            else:
                continue
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": lx,
                    "y": ly,
                    "line": {"dash": dash, "color": "#f59e0b"},
                    "name": f"{model.objective_name} = {k_val:.4g}",
                    "showlegend": frac_k == 1.0,
                }
            )
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "x": [float(opt[0])],
                "y": [float(opt[1])],
                "marker": {"size": 14, "color": "#ef4444", "symbol": "star"},
                "name": "Optimal",
            }
        )
    return Chart(
        id="graphical",
        title="Metode grafik",
        spec=plotly_figure(
            traces,
            "Daerah layak & garis isoprofit",
            xaxis={"title": {"text": v1}, "range": [xmin, xmax]},
            yaxis={"title": {"text": v2}, "range": [ymin, ymax], "scaleanchor": None},
            height=480,
        ),
    )


def _plain(k, v1, v2) -> str:
    from app.solvers.lp.model import linear_text

    return f"{linear_text(k.coeffs, [v1, v2])} {k.op.replace('<=', '≤').replace('>=', '≥')} {fmt_frac(k.rhs)}"
