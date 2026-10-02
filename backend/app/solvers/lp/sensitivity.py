"""Dualitas & analisis sensitivitas (Bab 6): harga bayangan, rentang optimalitas & kelayakan, what-if."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from app.core.errors import SolverError
from app.schemas.common import NamedTable, SolverResponse, Step, Table
from app.solvers._base import summary_items
from app.solvers.lp import tableau
from app.solvers.lp.matrix import column, inverse, matvec, vecmat
from app.solvers.lp.model import Constraint, LPModel, linear_latex
from app.solvers.lp.numbers import fmt_frac, latex_frac

INF = None  # ditampilkan sebagai ∞


@dataclass
class Sensitivity:
    shadow: list[Fraction]
    rhs_ranges: list[tuple[Fraction | None, Fraction | None]]  # batas bawah/atas nilai bᵢ
    obj_ranges: dict[str, tuple[Fraction | None, Fraction | None]]  # batas cⱼ
    reduced: dict[str, Fraction]
    slack: list[Fraction]
    b_inv: list[list[Fraction]]
    basis_names: list[str]


def _fmt_bound(x: Fraction | None, neg: bool) -> str:
    if x is None:
        return "−∞" if neg else "∞"
    return fmt_frac(x)


def analyze(model: LPModel, outcome: tableau.SimplexOutcome) -> Sensitivity:
    if outcome.status != "optimal":
        raise SolverError("Analisis sensitivitas hanya untuk masalah dengan solusi optimal.")
    sf = tableau.standard_form(model)
    keep = [j for j, k in enumerate(sf.kinds) if k != "a"]
    names = [sf.names[j] for j in keep]
    a = [[row[j] for j in keep] for row in sf.rows]
    c = [sf.c[j] for j in keep]
    basis_names = [n for n in outcome.basis_names]
    if any(n not in names for n in basis_names) or len(basis_names) != len(a):
        raise SolverError(
            "Basis optimal memuat variabel artifisial (degenerate); analisis sensitivitas tidak tersedia."
        )
    bcols = [names.index(n) for n in basis_names]
    b_mat = [[a[i][j] for j in bcols] for i in range(len(a))]
    b_inv = inverse(b_mat)
    c_b = [c[j] for j in bcols]
    y = vecmat(c_b, b_inv)
    x_b = matvec(b_inv, sf.rhs)
    reduced_all = [sum((y[i] * a[i][j] for i in range(len(a))), Fraction(0)) - c[j] for j in range(len(names))]
    tab = [
        [sum((b_inv[r][i] * a[i][j] for i in range(len(a))), Fraction(0)) for j in range(len(names))]
        for r in range(len(a))
    ]

    shadow = [sf.sigma * y[i] * sf.flip[i] for i in range(len(a))]
    rhs_ranges = []
    for i in range(len(a)):
        col = column(b_inv, i)
        lo, hi = None, None  # perubahan Δ pada b internal
        for xb, d in zip(x_b, col, strict=True):
            if d > 0:
                lo = -xb / d if lo is None else max(lo, -xb / d)
            elif d < 0:
                hi = -xb / d if hi is None else min(hi, -xb / d)
        b0 = model.constraints[i].rhs
        if sf.flip[i] == -1:
            lo, hi = (None if hi is None else -hi), (None if lo is None else -lo)
        rhs_ranges.append((None if lo is None else b0 + lo, None if hi is None else b0 + hi))

    obj_ranges: dict[str, tuple[Fraction | None, Fraction | None]] = {}
    reduced: dict[str, Fraction] = {}
    nonbasic = [j for j in range(len(names)) if j not in bcols]
    for v, cols in sf.var_map.items():
        if len(cols) != 1 or cols[0][1] != 1:
            continue  # variabel bebas / nonpositif: rentang tidak ditampilkan
        j = cols[0][0]
        jj = keep.index(j)
        reduced[v] = sf.sigma * reduced_all[jj]
        if jj in bcols:
            k = bcols.index(jj)
            lo, hi = None, None
            for l_ in nonbasic:
                t = tab[k][l_]
                if t > 0:
                    lo = -reduced_all[l_] / t if lo is None else max(lo, -reduced_all[l_] / t)
                elif t < 0:
                    hi = -reduced_all[l_] / t if hi is None else min(hi, -reduced_all[l_] / t)
        else:
            lo, hi = None, reduced_all[jj]
        c0 = model.objective.get(v, Fraction(0))
        if sf.sigma == -1:
            lo, hi = (None if hi is None else -hi), (None if lo is None else -lo)
        obj_ranges[v] = (None if lo is None else c0 + lo, None if hi is None else c0 + hi)

    lhs = [
        sum((k.coeffs.get(v, Fraction(0)) * outcome.x[v] for v in model.variables), Fraction(0))
        for k in model.constraints
    ]
    slack = [k.rhs - lv if k.op != ">=" else lv - k.rhs for k, lv in zip(model.constraints, lhs, strict=True)]
    return Sensitivity(shadow, rhs_ranges, obj_ranges, reduced, slack, b_inv, basis_names)


def sensitivity_tables(model: LPModel, s: Sensitivity) -> list[NamedTable]:
    cons = NamedTable(
        title="Kendala: harga bayangan & rentang kelayakan",
        columns=["Kendala", "Slack/surplus", "Harga bayangan (yᵢ*)", "RHS", "Batas bawah bᵢ", "Batas atas bᵢ"],
        rows=[
            [k.name, fmt_frac(sl), fmt_frac(y), fmt_frac(k.rhs), _fmt_bound(lo, True), _fmt_bound(hi, False)]
            for k, sl, y, (lo, hi) in zip(model.constraints, s.slack, s.shadow, s.rhs_ranges, strict=True)
        ],
    )
    var = NamedTable(
        title="Variabel: biaya tereduksi & rentang optimalitas",
        columns=["Variabel", "Koefisien cⱼ", "Biaya tereduksi", "Batas bawah cⱼ", "Batas atas cⱼ"],
        rows=[
            [
                v,
                fmt_frac(model.objective.get(v, Fraction(0))),
                fmt_frac(s.reduced[v]),
                _fmt_bound(lo, True),
                _fmt_bound(hi, False),
            ]
            for v, (lo, hi) in s.obj_ranges.items()
        ],
    )
    return [cons, var]


# --------------------------------------------------------------------------- dual


def dual_model(model: LPModel) -> tuple[LPModel, list[str]]:
    """Konversi primal → dual dengan aturan SOB (sensible–odd–bizarre)."""
    is_max = model.sense == "max"
    ys = [f"y{i + 1}" for i in range(len(model.constraints))]
    notes = []
    free: set[str] = set()
    nonpos: set[str] = set()
    for y, k in zip(ys, model.constraints, strict=True):
        sensible = "<=" if is_max else ">="
        if k.op == sensible:
            notes.append(f"Kendala {k.name} ({k.op}) wajar → {y} ≥ 0.")
        elif k.op == "=":
            free.add(y)
            notes.append(f"Kendala {k.name} (=) → {y} bebas tanda.")
        else:
            nonpos.add(y)
            notes.append(f"Kendala {k.name} ({k.op}) tidak wajar → {y} ≤ 0.")
    cons = []
    for v in model.variables:
        coeffs = {y: k.coeffs.get(v, Fraction(0)) for y, k in zip(ys, model.constraints, strict=True)}
        coeffs = {y: c for y, c in coeffs.items() if c != 0}
        if v in model.free:
            op = "="
        elif v in model.nonpositive:
            op = "<=" if is_max else ">="
        else:
            op = ">=" if is_max else "<="
        if not coeffs:
            coeffs = {ys[0]: Fraction(0)}
        cons.append(Constraint(coeffs, op, model.objective.get(v, Fraction(0)), name=f"D{v}"))
        notes.append(
            f"Variabel {v} → kendala dual {op} (koefisien tujuan {fmt_frac(model.objective.get(v, Fraction(0)))})."
        )
    dual = LPModel(
        "min" if is_max else "max",
        {y: k.rhs for y, k in zip(ys, model.constraints, strict=True)},
        cons,
        ys,
        free,
        nonpos,
        objective_name="W",
    )
    return dual, notes


def duality_response(
    model: LPModel, what_if_rhs: list[float] | None, what_if_obj: list[float] | None
) -> SolverResponse:
    from app.solvers.lp.numbers import frac

    primal = tableau.solve(model, "bigm")
    dual, notes = dual_model(model)
    steps = [
        Step(title="Model primal", latex=model.latex()),
        Step(
            title="Konversi ke model dual",
            explanation="Setiap kendala primal menjadi satu variabel dual; setiap variabel primal menjadi satu kendala dual. "
            + " ".join(notes),
            latex=dual.latex(),
        ),
    ]
    if primal.status != "optimal":
        msg = {
            "unbounded": "Primal tak terbatas → dual tidak layak.",
            "infeasible": "Primal tidak layak → dual tak terbatas atau tidak layak.",
        }[primal.status]
        steps.append(Step(title="Status primal", explanation=msg))
        return SolverResponse(
            result={"status": primal.status},
            steps=steps,
            conclusion=msg,
            summary=summary_items([("Status primal", primal.status)]),
        )
    dual_out = tableau.solve(dual, "bigm")
    s = analyze(model, primal)
    tables = sensitivity_tables(model, s)
    steps += [
        Step(
            title="Solusi optimal primal",
            latex=", ".join(f"{v} = {latex_frac(x)}" for v, x in primal.x.items())
            + rf",\quad {model.objective_name}^* = {latex_frac(primal.z)}",
        ),
        Step(
            title="Solusi optimal dual (teorema dualitas kuat)",
            explanation="Nilai optimal dual sama dengan nilai optimal primal, dan solusi dual = harga bayangan kendala primal.",
            latex=", ".join(f"{v} = {latex_frac(x)}" for v, x in dual_out.x.items())
            + rf",\quad W^* = {latex_frac(dual_out.z) if dual_out.z is not None else '—'}",
        ),
        Step(
            title="Harga bayangan dari tabel optimal",
            explanation="y* = c_B B⁻¹: kenaikan Z bila ruas kanan kendala dinaikkan satu satuan (selama masih dalam rentang kelayakan).",
            latex=r"\mathbf{y}^* = \mathbf{c}_B \mathbf{B}^{-1} = (" + ", ".join(latex_frac(y) for y in s.shadow) + ")",
            matrix=[[float(x) for x in row] for row in s.b_inv],
        ),
        Step(
            title="Kesenjangan komplementer (complementary slackness)",
            explanation="Jika kendala primal tidak aktif (slack > 0) maka harga bayangannya 0, dan sebaliknya.",
            table=Table(
                columns=["Kendala", "Slack", "yᵢ*", "Slack × yᵢ*"],
                rows=[
                    [k.name, fmt_frac(sl), fmt_frac(y), fmt_frac(sl * y)]
                    for k, sl, y in zip(model.constraints, s.slack, s.shadow, strict=True)
                ],
            ),
        ),
        Step(
            title="Rentang kelayakan ruas kanan (bᵢ)",
            explanation="Basis tetap optimal (harga bayangan tetap berlaku) selama bᵢ di dalam rentang ini.",
            table=tables[0],
        ),
        Step(
            title="Rentang optimalitas koefisien tujuan (cⱼ)",
            explanation="Solusi optimal tetap sama selama cⱼ di dalam rentang ini (perubahan satu koefisien saja).",
            table=tables[1],
        ),
    ]
    result: dict = {
        "status": "optimal",
        "z": float(primal.z),
        "x": {v: float(x) for v, x in primal.x.items()},
        "dual": {v: float(x) for v, x in dual_out.x.items()},
        "shadow_prices": [float(y) for y in s.shadow],
    }
    conclusion = f"Z* = W* = {fmt_frac(primal.z)}."
    if what_if_rhs or what_if_obj:
        m2 = model.copy()
        if what_if_rhs:
            if len(what_if_rhs) != len(m2.constraints):
                raise SolverError(f"What-if RHS harus berisi {len(m2.constraints)} nilai.")
            for k, v in zip(m2.constraints, what_if_rhs, strict=True):
                k.rhs = frac(v)
        if what_if_obj:
            if len(what_if_obj) != len(m2.variables):
                raise SolverError(f"What-if koefisien tujuan harus berisi {len(m2.variables)} nilai.")
            m2.objective = {v: frac(c) for v, c in zip(m2.variables, what_if_obj, strict=True)}
        out2 = tableau.solve(m2, "bigm")
        inside = all(
            (lo is None or k.rhs >= lo) and (hi is None or k.rhs <= hi)
            for k, (lo, hi) in zip(m2.constraints, s.rhs_ranges, strict=True)
        )
        if out2.status == "optimal":
            txt = (
                f"Setelah perubahan: Z* = {fmt_frac(out2.z)} (sebelumnya {fmt_frac(primal.z)}), solusi "
                + ", ".join(f"{v} = {fmt_frac(x)}" for v, x in out2.x.items())
                + ". "
                + (
                    "Semua RHS baru masih dalam rentang kelayakan, sehingga basis optimal tidak berubah."
                    if what_if_rhs and inside
                    else ""
                )
            )
            result["what_if"] = {"z": float(out2.z), "x": {v: float(x) for v, x in out2.x.items()}}
        else:
            txt = (
                f"Setelah perubahan, masalah menjadi {'tak terbatas' if out2.status == 'unbounded' else 'tidak layak'}."
            )
            result["what_if"] = {"status": out2.status}
        steps.append(Step(title="Analisis what-if", explanation=txt))
        conclusion += " " + txt
    return SolverResponse(
        result=result,
        steps=steps,
        tables=tables,
        summary=summary_items(
            [("Z* primal", fmt_frac(primal.z)), ("W* dual", fmt_frac(dual_out.z) if dual_out.z is not None else "—")]
            + [(f"Harga bayangan {k.name}", fmt_frac(y)) for k, y in zip(model.constraints, s.shadow, strict=True)]
        ),
        conclusion=conclusion,
    )


__all__ = ["analyze", "dual_model", "duality_response", "linear_latex", "sensitivity_tables"]
