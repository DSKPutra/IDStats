"""Penyusun respons API untuk metode simpleks (Bab 4)."""

from __future__ import annotations

from app.schemas.common import NamedTable, SolverResponse, Step
from app.solvers._base import summary_items
from app.solvers.lp import sensitivity, tableau
from app.solvers.lp.graphical import _chart
from app.solvers.lp.model import LPModel
from app.solvers.lp.numbers import fmt_frac, latex_frac

METHOD_LABEL = {"simplex": "Simpleks", "bigm": "Big-M", "twophase": "Dua Fase"}


def simplex_response(model: LPModel, method: str) -> SolverResponse:
    sf = tableau.standard_form(model)
    out = tableau.solve(model, method)
    head = [
        Step(title="Model", latex=model.latex()),
        Step(
            title="Bentuk augmented (standar)",
            explanation="Tambahkan slack (sᵢ) untuk kendala ≤, surplus (eᵢ) dan artifisial (aᵢ) untuk ≥, artifisial untuk =. "
            + " ".join(sf.notes),
            latex=tableau.augmented_latex(sf),
        ),
    ]
    steps = head + out.steps
    label = METHOD_LABEL[out.method]
    if out.status != "optimal":
        text = {
            "unbounded": f"{model.objective_name} tak terbatas (unbounded).",
            "infeasible": "Masalah tidak memiliki solusi layak (infeasible).",
        }[out.status]
        return SolverResponse(
            result={"status": out.status, "method": out.method},
            steps=steps,
            conclusion=text,
            summary=summary_items([("Metode", label), ("Status", text)]),
        )
    sol = NamedTable(
        title="Solusi optimal", columns=["Variabel", "Nilai"], rows=[[v, fmt_frac(x)] for v, x in out.x.items()]
    )
    tables = [sol]
    try:
        s = sensitivity.analyze(model, out)
        tables += sensitivity.sensitivity_tables(model, s)
        steps.append(
            Step(
                title="Analisis pasca-optimal",
                explanation="Harga bayangan (shadow price) dibaca dari baris 0 tabel optimal pada kolom slack: kenaikan Z untuk "
                "setiap tambahan satu satuan ruas kanan. Rentang lengkap ada di halaman Dualitas & Sensitivitas.",
                latex=r"\mathbf{y}^* = (" + ", ".join(latex_frac(y) for y in s.shadow) + ")",
            )
        )
    except Exception:  # noqa: BLE001 - sensitivitas opsional (mis. basis degenerate dengan artifisial)
        pass
    charts = (
        [_chart(model, [], (out.x[model.variables[0]], out.x[model.variables[1]]), out.z)]
        if len(model.variables) == 2
        else []
    )
    conclusion = (
        f"Solusi optimal ({label}): "
        + ", ".join(f"{v} = {fmt_frac(x)}" for v, x in out.x.items())
        + f", dengan {model.objective_name} = {fmt_frac(out.z)}."
    )
    if out.alternative:
        conclusion += (
            " Terdapat solusi optimum ganda, mis. "
            + ", ".join(f"{v} = {fmt_frac(x)}" for v, x in out.alternative.items())
            + "."
        )
    iters = sum(1 for st in out.steps if "iterasi" in st.title.lower())
    return SolverResponse(
        result={
            "status": "optimal",
            "method": out.method,
            "z": float(out.z),
            "x": {v: float(x) for v, x in out.x.items()},
            "multiple": bool(out.alternative),
        },
        steps=steps,
        tables=tables,
        charts=charts,
        summary=summary_items(
            [("Metode", label), (f"{model.objective_name}*", fmt_frac(out.z))]
            + [(v, fmt_frac(x)) for v, x in out.x.items()]
            + [("Jumlah iterasi", iters)]
        ),
        conclusion=conclusion,
    )
