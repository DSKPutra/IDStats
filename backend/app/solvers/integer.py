"""Pemrograman bilangan bulat (Bab 12): branch-and-bound untuk BIP/MIP dengan relaksasi LP (simpleks sendiri),
pohon visual, dan pembantu formulasi biner (fixed-charge, either-or, k dari n kendala)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from fractions import Fraction
from math import floor

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items
from app.solvers.lp import tableau
from app.solvers.lp.model import Constraint, LPModel, linear_text, parse_linear, parse_model
from app.solvers.lp.numbers import fmt_frac, frac

MAX_NODES = 400
TIME_LIMIT = 20


@dataclass
class BBNode:
    id: int
    parent: int | None
    branch: str
    extra: list[Constraint]
    status: str = ""
    z: Fraction | None = None
    x: dict[str, Fraction] = field(default_factory=dict)
    depth: int = 0


def branch_and_bound(model: LPModel) -> SolverResponse:
    ints = [v for v in model.variables if v in model.integer]
    if not ints:
        raise SolverError("Tandai variabel bilangan bulat dengan baris “int x1, x2” atau biner dengan “bin y1, y2”.")
    is_max = model.sense == "max"
    better = (lambda a, b: a > b) if is_max else (lambda a, b: a < b)
    all_int_obj = all(c.denominator == 1 for v, c in model.objective.items()) and all(
        v in model.integer for v in model.objective
    )
    incumbent: tuple[Fraction, dict[str, Fraction]] | None = None
    nodes: list[BBNode] = []
    stack = [BBNode(0, None, "Masalah awal (relaksasi LP)", [])]
    counter = 1
    started = time.monotonic()
    while stack:
        node = stack.pop()
        nodes.append(node)
        if time.monotonic() - started > TIME_LIMIT:
            raise SolverError(
                f"Branch-and-bound melebihi {TIME_LIMIT} detik ({len(nodes)} simpul); perkecil masalah atau perketat batas variabel."
            )
        if len(nodes) > MAX_NODES:
            raise SolverError(f"Pohon branch-and-bound melebihi {MAX_NODES} simpul; perkecil masalah.")
        sub = model.copy()
        sub.constraints = sub.constraints + node.extra
        out = tableau.solve(sub, "bigm", record=False)
        if out.status == "infeasible":
            node.status = "Difathom: tidak layak"
            continue
        if out.status == "unbounded":
            raise SolverError("Relaksasi LP tak terbatas; tambahkan kendala pembatas.")
        node.z, node.x = out.z, out.x
        bound = node.z
        if all_int_obj:  # Z harus bulat → bound dapat dibulatkan
            bound = Fraction(floor(bound)) if is_max else -Fraction(floor(-bound))
        if incumbent is not None and not better(bound, incumbent[0]):
            node.status = f"Difathom: batas {fmt_frac(bound)} tidak lebih baik dari incumbent {fmt_frac(incumbent[0])}"
            continue
        frac_vars = [v for v in ints if out.x[v].denominator != 1]
        if not frac_vars:
            node.status = "Difathom: solusi bulat → incumbent baru"
            incumbent = (out.z, out.x)
            continue
        # variabel biner dicabangkan lebih dulu; selain itu pilih yang paling jauh dari bilangan bulat
        binaries = [v for v in frac_vars if v in model.binary]
        v = (
            binaries[0]
            if binaries
            else max(
                frac_vars,
                key=lambda w: (min(out.x[w] - floor(out.x[w]), 1 - (out.x[w] - floor(out.x[w]))), -ints.index(w)),
            )
        )
        val = out.x[v]
        lo = Fraction(floor(val))
        node.status = f"Dicabangkan pada {v} = {fmt_frac(val)}"
        children = [
            BBNode(
                counter,
                node.id,
                f"{v} ≥ {fmt_frac(lo + 1)}",
                node.extra + [Constraint({v: Fraction(1)}, ">=", lo + 1, name=f"{v} ≥ {fmt_frac(lo + 1)}")],
                depth=node.depth + 1,
            ),
            BBNode(
                counter + 1,
                node.id,
                f"{v} ≤ {fmt_frac(lo)}",
                node.extra + [Constraint({v: Fraction(1)}, "<=", lo, name=f"{v} ≤ {fmt_frac(lo)}")],
                depth=node.depth + 1,
            ),
        ]
        counter += 2
        stack.extend(children)  # LIFO: anak terakhir (≤) diproses lebih dulu, seperti Hillier
    nodes.sort(key=lambda n: n.id)
    rows = [
        [
            n.id,
            "—" if n.parent is None else n.parent,
            n.branch,
            fmt_frac(n.z) if n.z is not None else "—",
            ", ".join(f"{k}={fmt_frac(v)}" for k, v in n.x.items()) if n.x else "—",
            n.status,
        ]
        for n in nodes
    ]
    table = NamedTable(
        title="Simpul branch-and-bound",
        columns=["Simpul", "Induk", "Kendala cabang", "Z relaksasi", "Solusi relaksasi", "Status"],
        rows=rows,
    )
    steps = [
        Step(title="Model", latex=model.latex()),
        Step(
            title="Strategi",
            explanation="Setiap simpul menyelesaikan relaksasi LP (kendala bulat diabaikan) dengan simpleks. Pencabangan pada variabel bulat "
            "yang bernilai pecahan (variabel biner lebih dulu, lalu yang paling pecahan): xⱼ ≤ ⌊xⱼ*⌋ atau xⱼ ≥ ⌊xⱼ*⌋ + 1. Simpul difathom bila (1) tidak layak, (2) batasnya tidak lebih baik "
            "dari incumbent, atau (3) solusinya sudah bulat. Simpul terbaru diproses lebih dulu (depth-first)."
            + (" Karena semua koefisien tujuan bulat, batas Z dibulatkan." if all_int_obj else ""),
        ),
        Step(title="Iterasi pohon", table=table),
    ]
    chart = _tree_chart(nodes, incumbent)
    if incumbent is None:
        steps.append(
            Step(title="Tidak ada solusi bulat", explanation="Semua simpul difathom tanpa solusi bulat layak.")
        )
        return SolverResponse(
            result={"status": "infeasible", "nodes": len(nodes)},
            steps=steps,
            tables=[table],
            charts=[chart],
            conclusion="Masalah bilangan bulat tidak memiliki solusi layak.",
            summary=summary_items([("Status", "Tidak layak"), ("Simpul diperiksa", len(nodes))]),
        )
    z, x = incumbent
    steps.append(
        Step(
            title="Solusi optimal",
            explanation="Tidak ada simpul tersisa; incumbent terakhir adalah solusi optimal.",
            latex=", ".join(f"{k} = {fmt_frac(v)}" for k, v in x.items())
            + rf",\quad {model.objective_name}^* = {fmt_frac(z)}",
        )
    )
    return SolverResponse(
        result={"status": "optimal", "z": float(z), "x": {k: float(v) for k, v in x.items()}, "nodes": len(nodes)},
        steps=steps,
        tables=[
            NamedTable(
                title="Solusi optimal", columns=["Variabel", "Nilai"], rows=[[k, fmt_frac(v)] for k, v in x.items()]
            ),
            table,
        ],
        charts=[chart],
        summary=summary_items(
            [(f"{model.objective_name}*", fmt_frac(z))]
            + [(k, fmt_frac(v)) for k, v in x.items()]
            + [("Simpul diperiksa", len(nodes))]
        ),
        conclusion=f"Solusi bulat optimal: {', '.join(f'{k} = {fmt_frac(v)}' for k, v in x.items())} dengan {model.objective_name} = {fmt_frac(z)} ({len(nodes)} simpul).",
    )


def _tree_chart(nodes: list[BBNode], incumbent) -> Chart:
    children: dict[int | None, list[BBNode]] = {}
    for n in nodes:
        children.setdefault(n.parent, []).append(n)
    pos: dict[int, tuple[float, float]] = {}
    counter = [0.0]

    def place(n: BBNode) -> float:
        kids = sorted(children.get(n.id, []), key=lambda c: c.id)
        if not kids:
            x = counter[0]
            counter[0] += 1
        else:
            xs = [place(k) for k in kids]
            x = sum(xs) / len(xs)
        pos[n.id] = (x, -n.depth)
        return x

    for root in children.get(None, []):
        place(root)
    ann = []
    for n in nodes:
        if n.parent is not None:
            (x0, y0), (x1, y1) = pos[n.parent], pos[n.id]
            ann.append(
                {
                    "x": x1,
                    "y": y1,
                    "ax": x0,
                    "ay": y0,
                    "xref": "x",
                    "yref": "y",
                    "axref": "x",
                    "ayref": "y",
                    "showarrow": True,
                    "arrowhead": 0,
                    "arrowcolor": "#94a3b8",
                    "standoff": 18,
                    "startstandoff": 18,
                }
            )
            ann.append(
                {
                    "x": (x0 + x1) / 2,
                    "y": (y0 + y1) / 2,
                    "text": n.branch,
                    "showarrow": False,
                    "font": {"size": 10},
                    "bgcolor": "rgba(255,255,255,0.75)",
                }
            )
    best_x = incumbent[1] if incumbent else None

    def color(n: BBNode) -> str:
        if best_x is not None and n.x == best_x and "bulat" in n.status:
            return "#10b981"
        if "tidak layak" in n.status:
            return "#94a3b8"
        if "Dicabangkan" in n.status:
            return "#12a227"
        return "#f59e0b"

    return Chart(
        id="bb-tree",
        title="Pohon branch-and-bound",
        spec=plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "markers+text",
                    "x": [pos[n.id][0] for n in nodes],
                    "y": [pos[n.id][1] for n in nodes],
                    "text": [f"{n.id}<br>{'Z=' + fmt_frac(n.z) if n.z is not None else 'TL'}" for n in nodes],
                    "textposition": "middle center",
                    "marker": {"size": 46, "color": [color(n) for n in nodes]},
                    "textfont": {"color": "#ffffff", "size": 10},
                    "hovertext": [n.status for n in nodes],
                    "showlegend": False,
                }
            ],
            "Pohon branch-and-bound (hijau = optimal, oranye = difathom, abu = tidak layak)",
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=ann,
            height=max(380, 110 * (max(n.depth for n in nodes) + 1)),
        ),
    )


# --------------------------------------------------------------------------- formulasi biner

_EITHER = re.compile(r"^(?:either|salah\s*satu)\s*(?:M\s*=\s*([\d.]+))?\s*:\s*(.+)$", re.IGNORECASE)
_KOFN = re.compile(r"^(?:k|kofn)\s*=?\s*(\d+)\s*(?:M\s*=\s*([\d.]+))?\s*:\s*(.+)$", re.IGNORECASE)
_FIXED = re.compile(
    r"^(?:fixed|tetap)\s+([A-Za-z_]\w*)\s*:\s*(?:biaya|cost)\s*=\s*([\d.]+)\s*,\s*(?:maks|max|u)\s*=\s*([\d.]+)$",
    re.IGNORECASE,
)


def _parse_con(text: str) -> Constraint:
    m = parse_model("min Z = 0q\n" + text)
    return m.constraints[0]


def binary_formulation(model_text: str, rules_text: str) -> SolverResponse:
    model = parse_model(model_text, allow_integer=True, require_constraints=False)
    notes: list[list[str]] = []
    y_count = 0
    for raw in rules_text.replace("\r", "").split("\n"):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        if m := _EITHER.match(line):
            big = frac(float(m.group(1) or 1000))
            parts = [p.strip() for p in m.group(2).split("|")]
            if len(parts) != 2:
                raise SolverError("Aturan either-or memerlukan tepat dua kendala dipisah “|”.")
            y_count += 1
            y = f"y{y_count}"
            for k, part, coef in ((0, parts[0], 1), (1, parts[1], -1)):
                con = _parse_con(part)
                if con.op == "=":
                    raise SolverError("Either-or hanya untuk kendala ≤ atau ≥.")
                sign = 1 if con.op == "<=" else -1
                coeffs = dict(con.coeffs)
                # ≤: f(x) ≤ b + M·y  (k=0)  /  f(x) ≤ b + M(1 − y)  (k=1)
                coeffs[y] = coeffs.get(y, Fraction(0)) - sign * big * coef
                rhs = con.rhs + (sign * big if k == 1 else 0)
                model.constraints.append(Constraint(coeffs, con.op, rhs, name=f"either-{y}-{k + 1}"))
            model.variables.append(y)
            model.binary.add(y)
            model.integer.add(y)
            model.constraints.append(Constraint({y: Fraction(1)}, "<=", Fraction(1), name=f"{y} ≤ 1 (biner)"))
            notes.append(
                ["Either-or", line, f"{y} = 0 → kendala 1 berlaku; {y} = 1 → kendala 2 berlaku (M = {fmt_frac(big)})"]
            )
        elif m := _KOFN.match(line):
            k = int(m.group(1))
            big = frac(float(m.group(2) or 1000))
            parts = [p.strip() for p in m.group(3).split("|")]
            if not 1 <= k <= len(parts):
                raise SolverError("Nilai K harus di antara 1 dan banyaknya kendala.")
            ys = []
            for part in parts:
                y_count += 1
                y = f"y{y_count}"
                ys.append(y)
                con = _parse_con(part)
                sign = 1 if con.op == "<=" else -1
                coeffs = dict(con.coeffs)
                coeffs[y] = -sign * big  # f(x) ≤ b + M·y ; y = 1 berarti kendala dilonggarkan
                model.constraints.append(Constraint(coeffs, con.op, con.rhs, name=f"kofn-{y}"))
                model.variables.append(y)
                model.binary.add(y)
                model.integer.add(y)
                model.constraints.append(Constraint({y: Fraction(1)}, "<=", Fraction(1), name=f"{y} ≤ 1 (biner)"))
            model.constraints.append(
                Constraint(
                    {y: Fraction(1) for y in ys}, "=", Fraction(len(parts) - k), name=f"{k} dari {len(parts)} berlaku"
                )
            )
            notes.append(
                ["K dari N kendala", line, f"Σ y = N − K = {len(parts) - k}; yᵢ = 1 berarti kendala i boleh dilanggar"]
            )
        elif m := _FIXED.match(line):
            v, cost, upper = m.group(1), frac(float(m.group(2))), frac(float(m.group(3)))
            if v not in model.variables:
                raise SolverError(f"Variabel {v} pada aturan biaya tetap tidak ada di model.")
            y_count += 1
            y = f"y{y_count}"
            model.objective[y] = cost if model.sense == "min" else -cost
            model.constraints.append(
                Constraint({v: Fraction(1), y: -upper}, "<=", Fraction(0), name=f"{v} ≤ {fmt_frac(upper)}·{y}")
            )
            model.constraints.append(Constraint({y: Fraction(1)}, "<=", Fraction(1), name=f"{y} ≤ 1 (biner)"))
            model.variables.append(y)
            model.binary.add(y)
            model.integer.add(y)
            notes.append(
                [
                    "Biaya tetap",
                    line,
                    f"Biaya tetap {fmt_frac(cost)} dikenakan bila {v} > 0 melalui {v} ≤ {fmt_frac(upper)}·{y}",
                ]
            )
        else:
            raise SolverError(
                f"Aturan “{line}” tidak dikenali. Gunakan “either M=100: kendala1 | kendala2”, “k=2 M=100: k1 | k2 | k3”, atau “fixed x1: biaya=50, maks=10”."
            )
    res = branch_and_bound(model)
    res.steps = [
        Step(
            title="Reformulasi dengan variabel biner",
            explanation="Setiap aturan diubah menjadi kendala linier dengan variabel biner tambahan.",
            table=Table(columns=["Jenis", "Aturan", "Reformulasi"], rows=notes),
        ),
        Step(title="Model hasil reformulasi", latex=model.latex()),
    ] + res.steps[1:]
    res.tables.append(
        NamedTable(
            title="Kendala hasil reformulasi",
            columns=["Nama", "Kendala"],
            rows=[
                [k.name, f"{linear_text(k.coeffs, model.variables)} {k.op} {fmt_frac(k.rhs)}"]
                for k in model.constraints
            ],
        )
    )
    return res


__all__ = ["binary_formulation", "branch_and_bound", "parse_linear"]
