"""Metode simpleks direvisi (Bab 5): bentuk matriks B⁻¹, x_B = B⁻¹b, c_B B⁻¹ dan wawasan fundamental."""

from __future__ import annotations

from fractions import Fraction

from app.core.errors import SolverError
from app.schemas.common import NamedTable, SolverResponse, Step, Table
from app.solvers._base import summary_items
from app.solvers.lp.matrix import column, inverse, matmul, matvec, vecmat
from app.solvers.lp.model import LPModel
from app.solvers.lp.numbers import fmt_frac, latex_frac

MAX_ITER = 40


def _vec_latex(v: list[Fraction]) -> str:
    return r"\begin{bmatrix}" + r"\\".join(latex_frac(x) for x in v) + r"\end{bmatrix}"


def _row_latex(v: list[Fraction]) -> str:
    return "[" + ",\\ ".join(latex_frac(x) for x in v) + "]"


def solve_revised(model: LPModel) -> SolverResponse:
    if (
        model.sense != "max"
        or any(k.op != "<=" or k.rhs < 0 for k in model.constraints)
        or model.free
        or model.nonpositive
    ):
        raise SolverError(
            "Simpleks direvisi di halaman ini memakai bentuk standar Bab 5: maksimasi, semua kendala ≤ dengan ruas kanan ≥ 0, "
            "dan variabel ≥ 0. Untuk bentuk lain gunakan Metode Simpleks (Big-M / Dua Fase)."
        )
    n, m = len(model.variables), len(model.constraints)
    names = list(model.variables) + [f"s{i + 1}" for i in range(m)]
    a = [row + [Fraction(int(i == j)) for j in range(m)] for i, row in enumerate(model.a())]
    c = model.c() + [Fraction(0)] * m
    b = model.b()
    basis = list(range(n, n + m))
    steps = [
        Step(
            title="Model dalam bentuk matriks",
            explanation="Maks Z = c x dengan A x + I x_s = b, x ≥ 0, x_s ≥ 0.",
            latex=model.latex(),
        ),
        Step(
            title="Basis awal",
            explanation="Variabel slack menjadi basis awal sehingga B = I dan B⁻¹ = I.",
            latex=r"\mathbf{B} = \mathbf{I},\quad \mathbf{x}_B = \mathbf{b} = " + _vec_latex(b),
        ),
    ]
    for it in range(1, MAX_ITER + 1):
        bmat = [[a[i][j] for j in basis] for i in range(m)]
        binv = inverse(bmat)
        xb = matvec(binv, b)
        cb = [c[j] for j in basis]
        y = vecmat(cb, binv)
        z = sum((p * q for p, q in zip(cb, xb, strict=True)), Fraction(0))
        reduced = {
            j: sum((y[i] * a[i][j] for i in range(m)), Fraction(0)) - c[j] for j in range(n + m) if j not in basis
        }
        steps.append(
            Step(
                title=f"Iterasi {it}: hitung B⁻¹, x_B, dan c_B B⁻¹",
                explanation="Basis: "
                + ", ".join(names[j] for j in basis)
                + ". Koefisien baris 0 untuk variabel nonbasis = c_B B⁻¹ Aⱼ − cⱼ.",
                latex=(
                    r"\mathbf{x}_B = \mathbf{B}^{-1}\mathbf{b} = "
                    + _vec_latex(xb)
                    + r",\quad \mathbf{c}_B\mathbf{B}^{-1} = "
                    + _row_latex(y)
                    + rf",\quad Z = \mathbf{{c}}_B\mathbf{{x}}_B = {latex_frac(z)}"
                ),
                matrix=[[float(x) for x in row] for row in binv],
                table=Table(
                    columns=["Variabel nonbasis", "c_B B⁻¹ Aⱼ − cⱼ"],
                    rows=[[names[j], fmt_frac(d)] for j, d in reduced.items()],
                ),
            )
        )
        neg = [j for j, d in reduced.items() if d < 0]
        if not neg:
            x = {v: Fraction(0) for v in model.variables}
            for i, j in enumerate(basis):
                if j < n:
                    x[names[j]] = xb[i]
            s_star = matmul(binv, [row[:n] for row in a])
            steps.append(
                Step(
                    title="Optimal & wawasan fundamental (fundamental insight)",
                    explanation="Semua koefisien ≥ 0 sehingga basis optimal. Tabel akhir dapat dihitung langsung dari tabel awal: "
                    "baris 0 akhir = baris 0 awal + y*·(kendala awal), baris kendala akhir = B⁻¹·(kendala awal). "
                    "Matriks di bawah adalah S* = B⁻¹A (koefisien variabel keputusan pada tabel akhir).",
                    latex=r"\mathbf{y}^* = "
                    + _row_latex(y)
                    + r",\quad \mathbf{z}^* - \mathbf{c} = \mathbf{y}^*\mathbf{A} - \mathbf{c},\quad \mathbf{S}^* = \mathbf{B}^{-1}",
                    matrix=[[float(v) for v in row] for row in s_star],
                )
            )
            table = NamedTable(
                title="Solusi optimal", columns=["Variabel", "Nilai"], rows=[[v, fmt_frac(val)] for v, val in x.items()]
            )
            return SolverResponse(
                result={
                    "status": "optimal",
                    "z": float(z),
                    "x": {v: float(val) for v, val in x.items()},
                    "shadow_prices": [float(v) for v in y],
                    "iterations": it - 1,
                },
                steps=steps,
                tables=[table],
                summary=summary_items(
                    [(f"{model.objective_name}*", fmt_frac(z))]
                    + [(v, fmt_frac(val)) for v, val in x.items()]
                    + [("Iterasi", it - 1)]
                ),
                conclusion=f"Solusi optimal {', '.join(f'{v} = {fmt_frac(val)}' for v, val in x.items())} dengan {model.objective_name} = {fmt_frac(z)}.",
            )
        enter = min(neg, key=lambda j: (reduced[j], j))
        d = matvec(binv, column(a, enter))
        ratios = {i: xb[i] / d[i] for i in range(m) if d[i] > 0}
        if not ratios:
            steps.append(
                Step(
                    title="Tak terbatas",
                    explanation=f"Kolom B⁻¹A untuk {names[enter]} tidak memiliki elemen positif: Z tak terbatas.",
                )
            )
            return SolverResponse(
                result={"status": "unbounded"},
                steps=steps,
                conclusion=f"{model.objective_name} tak terbatas.",
                summary=summary_items([("Status", "Tak terbatas")]),
            )
        leave = min(ratios, key=lambda i: (ratios[i], basis[i]))
        steps.append(
            Step(
                title=f"Iterasi {it}: pilih variabel masuk & keluar",
                explanation=f"Masuk: {names[enter]} (koefisien {fmt_frac(reduced[enter])}). Kolom B⁻¹Aⱼ dan uji rasio → keluar: {names[basis[leave]]}.",
                latex=r"\mathbf{B}^{-1}\mathbf{A}_j = " + _vec_latex(d),
                table=Table(
                    columns=["Basis", "x_B", "B⁻¹Aⱼ", "Rasio"],
                    rows=[
                        [names[basis[i]], fmt_frac(xb[i]), fmt_frac(d[i]), fmt_frac(ratios[i]) if i in ratios else "—"]
                        for i in range(m)
                    ],
                ),
            )
        )
        basis[leave] = enter
    raise SolverError("Simpleks direvisi tidak konvergen.")
