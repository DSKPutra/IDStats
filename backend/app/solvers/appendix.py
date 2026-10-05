"""Appendix: uji konveksitas (Hessian), optimasi klasik (titik stasioner & pengali Lagrange),
dan kalkulator matriks (determinan & invers dengan langkah, eigen, perkalian, transpose)."""

from __future__ import annotations

from fractions import Fraction

import numpy as np
from scipy.optimize import fsolve

from app.core.errors import SolverError
from app.schemas.common import NamedTable, SolverResponse, Step, Table
from app.solvers._base import summary_items
from app.solvers.expr import Expr, latexify
from app.solvers.lp.numbers import fmt_frac, frac


def _r(x: float) -> float:
    return float(round(x, 6))


def _vec(x) -> str:
    return "(" + ", ".join(f"{v:.6g}" for v in x) + ")"


def convexity(func: str, lower: list[float], upper: list[float], samples: int = 200, seed: int = 0) -> SolverResponse:
    f = Expr(func)
    n = len(f.variables)
    if len(lower) != n or len(upper) != n:
        raise SolverError(f"Batas bawah/atas harus berisi {n} nilai ({', '.join(f.variables)}).")
    lo, hi = np.array(lower, float), np.array(upper, float)
    if np.any(hi <= lo):
        raise SolverError("Setiap batas atas harus lebih besar dari batas bawah.")
    rng = np.random.default_rng(seed)
    pts = lo + (hi - lo) * rng.random((samples, n))
    eig_min, eig_max = np.inf, -np.inf
    rows = []
    for k, p in enumerate(pts):
        h = f.hessian(p)
        ev = np.linalg.eigvalsh(h)
        eig_min, eig_max = min(eig_min, ev.min()), max(eig_max, ev.max())
        if k < 8:
            rows.append([_vec(p), _vec(ev)])
    tol = 1e-6
    if eig_min >= -tol:
        verdict = "konveks"
    elif eig_max <= tol:
        verdict = "konkaf"
    else:
        verdict = "tidak konveks maupun konkaf"
    h0 = f.hessian((lo + hi) / 2)
    minors = [float(np.linalg.det(h0[: k + 1, : k + 1])) for k in range(n)]
    return SolverResponse(
        result={"verdict": verdict, "min_eigenvalue": float(eig_min), "max_eigenvalue": float(eig_max)},
        steps=[
            Step(title="Fungsi", latex=f"f = {latexify(func)}"),
            Step(
                title="Matriks Hessian di titik tengah daerah",
                explanation="Hessian dihitung secara numerik (beda pusat).",
                matrix=h0.round(6).tolist(),
                latex=r"\text{Minor utama: } " + ", ".join(f"\\Delta_{k + 1} = {m:.4g}" for k, m in enumerate(minors)),
            ),
            Step(
                title="Uji definit",
                explanation="f konveks pada daerah bila Hessian semidefinit positif di semua titik (semua nilai eigen ≥ 0); konkaf bila semidefinit negatif (semua ≤ 0). "
                f"Diuji pada {samples} titik acak di dalam kotak batas.",
                table=Table(columns=["Titik", "Nilai eigen Hessian"], rows=rows),
            ),
        ],
        summary=summary_items(
            [("Kesimpulan", verdict), ("Nilai eigen minimum", _r(eig_min)), ("Nilai eigen maksimum", _r(eig_max))]
        ),
        warnings=["Pengujian numerik pada sampel titik; untuk bukti formal periksa Hessian secara analitis."],
        conclusion=f"Fungsi {verdict} pada daerah yang diuji (nilai eigen Hessian dari {eig_min:.4g} sampai {eig_max:.4g}).",
    )


def _solve_many(eqs, n: int, lo: float, hi: float, seed: int = 0) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    sols: list[np.ndarray] = []
    for _ in range(60):
        x0 = lo + (hi - lo) * rng.random(n)
        x, info, ier, _ = fsolve(eqs, x0, full_output=True)
        if ier == 1 and np.max(np.abs(eqs(x))) < 1e-7 and not any(np.allclose(x, s, atol=1e-5) for s in sols):
            sols.append(x)
    return sorted(sols, key=lambda s: tuple(np.round(s, 6)))


def classical(func: str, constraints: str, search_lo: float, search_hi: float) -> SolverResponse:
    f0 = Expr(func)
    cons_text = [ln.strip() for ln in constraints.replace("\r", "").split("\n") if ln.strip()]
    gs = []
    for line in cons_text:
        if "=" not in line or any(op in line for op in ("<=", ">=")):
            raise SolverError(f"Kendala “{line}” harus berupa persamaan g(x) = b.")
        lhs, rhs = line.split("=", 1)
        gs.append(Expr(f"({lhs}) - ({rhs})"))
    variables = sorted(
        set(f0.variables) | {v for g in gs for v in g.variables},
        key=lambda s: (s.rstrip("0123456789"), int(s[len(s.rstrip("0123456789")) :] or 0)),
    )
    f = Expr(func, variables)
    gs = [Expr(g.text, variables) for g in gs]
    n, m = len(variables), len(gs)
    if m >= n and m:
        raise SolverError("Jumlah kendala persamaan harus lebih kecil dari jumlah variabel.")

    def eqs(z):
        x, lam = z[:n], z[n:]
        grad = f.grad(x) - sum((lam[i] * gs[i].grad(x) for i in range(m)), np.zeros(n))
        return np.r_[grad, [g(x) for g in gs]]

    sols = _solve_many(eqs, n + m, search_lo, search_hi)
    if not sols:
        raise SolverError("Tidak ditemukan titik stasioner pada rentang pencarian; ubah rentang.")
    rows = []
    for z in sols:
        x, lam = z[:n], z[n:]
        if m == 0:
            ev = np.linalg.eigvalsh(f.hessian(x))
            kind = (
                "minimum lokal"
                if ev.min() > 1e-6
                else "maksimum lokal"
                if ev.max() < -1e-6
                else "titik pelana"
                if ev.min() < -1e-6 and ev.max() > 1e-6
                else "tidak dapat ditentukan"
            )
        else:
            # Hessian terbatas (bordered) — klasifikasi lewat Hessian Lagrangian pada ruang tangen
            jac = np.array([g.grad(x) for g in gs])
            hl = f.hessian(x) - sum(lam[i] * gs[i].hessian(x) for i in range(m))
            _, _, vt = np.linalg.svd(jac)
            z_basis = vt[m:].T
            ev = np.linalg.eigvalsh(z_basis.T @ hl @ z_basis) if z_basis.size else np.array([0.0])
            kind = (
                "minimum lokal"
                if ev.min() > 1e-6
                else "maksimum lokal"
                if ev.max() < -1e-6
                else "titik pelana / tak tentu"
            )
        rows.append([_vec(x), _vec(lam) if m else "—", _r(f(x)), kind])
    table = NamedTable(title="Titik stasioner", columns=["x", "Pengali λ", "f(x)", "Jenis"], rows=rows)
    lagr = r"\mathcal{L}(\mathbf{x}, \boldsymbol{\lambda}) = f(\mathbf{x}) - \sum_i \lambda_i (g_i(\mathbf{x}) - b_i)"
    return SolverResponse(
        result={
            "points": [list(map(float, z[:n])) for z in sols],
            "multipliers": [list(map(float, z[n:])) for z in sols],
            "kinds": [r[3] for r in rows],
        },
        steps=[
            Step(
                title="Fungsi" + (" dan kendala" if m else ""),
                latex=f"f = {latexify(func)}" + (r",\quad " + r",\ ".join(latexify(c) for c in cons_text) if m else ""),
            ),
            Step(
                title="Syarat perlu",
                latex=(lagr + r",\quad \nabla_{\mathbf{x}}\mathcal{L} = \mathbf{0},\ g_i(\mathbf{x}) = b_i")
                if m
                else r"\nabla f(\mathbf{x}) = \mathbf{0}",
                explanation="Sistem persamaan diselesaikan secara numerik dari banyak titik awal untuk menemukan semua titik stasioner pada rentang pencarian.",
            ),
            Step(
                title="Klasifikasi (syarat cukup orde dua)",
                explanation="Tanpa kendala: Hessian definit positif → minimum, definit negatif → maksimum, tak tentu → titik pelana. Dengan kendala: Hessian Lagrangian dibatasi pada ruang singgung kendala.",
                table=table,
            ),
        ],
        tables=[table],
        summary=summary_items([(f"Titik {i + 1}", f"{r[0]} — {r[3]}") for i, r in enumerate(rows)]),
        conclusion=f"Ditemukan {len(rows)} titik stasioner: "
        + "; ".join(f"{r[0]} ({r[3]}, f = {r[2]:.6g})" for r in rows)
        + ".",
    )


# --------------------------------------------------------------------------- matriks


def _fm(m: list[list[Fraction]]) -> list[list[str]]:
    return [[fmt_frac(x) for x in row] for row in m]


def _mt(m: list[list[Fraction]], title: str = "") -> Table:
    return Table(
        columns=["", *[f"k{j + 1}" for j in range(len(m[0]))]],
        rows=[[f"b{i + 1}", *row] for i, row in enumerate(_fm(m))],
    )


def matrix_ops(a: list[list[float]], b: list[list[float]] | None, operation: str) -> SolverResponse:
    if not a or not a[0] or any(len(r) != len(a[0]) for r in a):
        raise SolverError("Matriks A harus persegi panjang dan tidak kosong.")
    A = [[frac(x) for x in r] for r in a]
    n, m = len(A), len(A[0])
    steps: list[Step] = [Step(title="Matriks A", table=_mt(A))]
    result: dict = {}
    summary: list = []
    tables: list[NamedTable] = []
    if operation in ("determinant", "inverse"):
        if n != m:
            raise SolverError("Determinan dan invers hanya untuk matriks persegi.")
        aug = [
            row[:] + ([Fraction(int(i == j)) for j in range(n)] if operation == "inverse" else [])
            for i, row in enumerate(A)
        ]
        det = Fraction(1)
        for col in range(n):
            piv = next((r for r in range(col, n) if aug[r][col] != 0), None)
            if piv is None:
                det = Fraction(0)
                steps.append(
                    Step(
                        title=f"Kolom {col + 1}: tidak ada pivot",
                        explanation="Seluruh kolom di bawah diagonal bernilai nol → matriks singular (determinan 0).",
                    )
                )
                break
            if piv != col:
                aug[col], aug[piv] = aug[piv], aug[col]
                det = -det
                steps.append(
                    Step(
                        title=f"Tukar baris {col + 1} ↔ {piv + 1}",
                        explanation="Pertukaran baris mengubah tanda determinan.",
                        table=_mt(aug),
                    )
                )
            p = aug[col][col]
            det *= p
            if operation == "inverse":
                aug[col] = [x / p for x in aug[col]]
                for r in range(n):
                    if r != col and aug[r][col] != 0:
                        fct = aug[r][col]
                        aug[r] = [x - fct * y for x, y in zip(aug[r], aug[col], strict=True)]
                steps.append(
                    Step(
                        title=f"Eliminasi Gauss-Jordan kolom {col + 1}",
                        explanation=f"Bagi baris {col + 1} dengan pivot {fmt_frac(p)}, lalu nolkan elemen lain di kolom ini.",
                        table=_mt(aug),
                    )
                )
            else:
                for r in range(col + 1, n):
                    if aug[r][col] != 0:
                        fct = aug[r][col] / p
                        aug[r] = [x - fct * y for x, y in zip(aug[r], aug[col], strict=True)]
                steps.append(
                    Step(
                        title=f"Eliminasi Gauss kolom {col + 1}",
                        explanation=f"Pivot {fmt_frac(p)}; nolkan elemen di bawahnya.",
                        table=_mt(aug),
                    )
                )
        result["determinant"] = float(det)
        summary.append(("Determinan", fmt_frac(det)))
        steps.append(
            Step(
                title="Determinan",
                explanation="Hasil kali elemen diagonal matriks segitiga atas (dengan tanda dari pertukaran baris).",
                latex=rf"\det(A) = {fmt_frac(det)}",
            )
        )
        if operation == "inverse":
            if det == 0:
                raise SolverError("Matriks singular (determinan 0) sehingga tidak memiliki invers.")
            inv = [row[n:] for row in aug]
            result["inverse"] = [[float(x) for x in row] for row in inv]
            tables.append(NamedTable(title="Invers A⁻¹", columns=[f"k{j + 1}" for j in range(n)], rows=_fm(inv)))
            steps.append(
                Step(
                    title="Invers",
                    explanation="Bagian kanan matriks augmented [I | A⁻¹].",
                    matrix=[[float(x) for x in row] for row in inv],
                )
            )
    elif operation == "eigen":
        if n != m:
            raise SolverError("Nilai eigen hanya untuk matriks persegi.")
        arr = np.array(a, float)
        vals, vecs = np.linalg.eig(arr)
        rows = []
        for k in range(n):
            v = vals[k]
            vec = vecs[:, k]
            txt = f"{v.real:.6g}" + (
                f" {'+' if v.imag >= 0 else '−'} {abs(v.imag):.6g}i" if abs(v.imag) > 1e-12 else ""
            )
            rows.append([k + 1, txt, _vec(vec.real) if np.allclose(vec.imag, 0) else "kompleks"])
        tables.append(
            NamedTable(title="Nilai & vektor eigen", columns=["#", "λ", "Vektor eigen (ternormalisasi)"], rows=rows)
        )
        steps.append(
            Step(
                title="Persamaan karakteristik",
                latex=r"\det(A - \lambda I) = 0",
                explanation="Akar polinomial karakteristik adalah nilai eigen; untuk setiap λ, vektor eigen memenuhi (A − λI)v = 0. Dihitung secara numerik.",
                table=Table(columns=["#", "λ", "v"], rows=rows),
            )
        )
        result["eigenvalues"] = [[float(v.real), float(v.imag)] for v in vals]
        summary += [(f"λ{k + 1}", r[1]) for k, r in enumerate(rows)]
    elif operation == "multiply":
        if not b:
            raise SolverError("Isi matriks B untuk perkalian.")
        B = [[frac(x) for x in r] for r in b]
        if len(B) != m:
            raise SolverError(f"Perkalian AB memerlukan jumlah baris B = jumlah kolom A ({m}).")
        prod = [[sum((A[i][k] * B[k][j] for k in range(m)), Fraction(0)) for j in range(len(B[0]))] for i in range(n)]
        steps += [
            Step(title="Matriks B", table=_mt(B)),
            Step(title="Hasil AB", latex=r"(AB)_{ij} = \sum_k a_{ik} b_{kj}", table=_mt(prod)),
        ]
        tables.append(NamedTable(title="AB", columns=[f"k{j + 1}" for j in range(len(prod[0]))], rows=_fm(prod)))
        result["product"] = [[float(x) for x in row] for row in prod]
    elif operation == "transpose":
        t = [list(col) for col in zip(*A, strict=True)]
        steps.append(Step(title="Transpose", table=_mt(t)))
        tables.append(NamedTable(title="Aᵀ", columns=[f"k{j + 1}" for j in range(len(t[0]))], rows=_fm(t)))
        result["transpose"] = [[float(x) for x in row] for row in t]
    else:
        raise SolverError("Operasi harus determinant, inverse, eigen, multiply, atau transpose.")
    if n == m and operation != "determinant":
        arr = np.array(a, float)
        summary.append(("Rank", int(np.linalg.matrix_rank(arr))))
    return SolverResponse(
        result=result, steps=steps, tables=tables, summary=summary_items(summary), conclusion="Operasi matriks selesai."
    )
