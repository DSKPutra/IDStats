"""Pemrograman nonlinear (Bab 13).

Satu variabel: biseksi & Newton. Multivariabel: gradient search. Kondisi KKT, quadratic programming (simpleks
termodifikasi / Wolfe), separable programming (aproksimasi linier sepotong), convex programming (Frank-Wolfe & SUMT),
dan nonkonveks (multistart). Turunan dihitung secara numerik (beda pusat).
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items
from app.solvers.expr import Expr, latexify
from app.solvers.lp import tableau
from app.solvers.lp.model import Constraint, LPModel, parse_model
from app.solvers.lp.numbers import MNum, fmt_frac

GOLDEN = (math.sqrt(5) - 1) / 2


def _r(x: float, d: int = 6) -> float:
    return float(round(x, d))


def _vec(x) -> str:
    return "(" + ", ".join(f"{v:.6g}" for v in x) + ")"


def line_search(phi, t_max: float = 1.0, tol: float = 1e-9) -> float:
    """Maksimumkan φ(t) pada [0, t_max] dengan golden section (φ diasumsikan unimodal)."""
    a, b = 0.0, t_max
    c, d = b - GOLDEN * (b - a), a + GOLDEN * (b - a)
    fc, fd = phi(c), phi(d)
    for _ in range(200):
        if b - a < tol:
            break
        if fc >= fd:
            b, d, fd = d, c, fc
            c = b - GOLDEN * (b - a)
            fc = phi(c)
        else:
            a, c, fc = c, d, fd
            d = a + GOLDEN * (b - a)
            fd = phi(d)
    best = max(
        (0.0, phi(0.0)),
        ((a + b) / 2, phi((a + b) / 2)),
        (t_max, phi(t_max)),
        key=lambda p: p[1] if math.isfinite(p[1]) else -math.inf,
    )
    return best[0]


def _bracket(phi) -> float:
    """Cari t_max sehingga φ sudah turun (untuk line search tanpa batas atas)."""
    t = 1e-3
    prev = phi(0.0)
    for _ in range(60):
        val = phi(t)
        if not math.isfinite(val) or val < prev:
            return t
        prev = val
        t *= 2
    return t


def ascent(
    f, x0, sign: float = 1.0, tol: float = 1e-7, max_iter: int = 500, record: list | None = None, feasible=None
) -> np.ndarray:
    """Gradient search (Bab 13.5) untuk memaksimumkan sign·f."""
    x = np.asarray(x0, dtype=float)
    for k in range(max_iter):
        g = sign * f.grad(x)
        if record is not None:
            record.append((k, x.copy(), sign * f.safe(x), g.copy()))
        if np.linalg.norm(g, ord=np.inf) < tol:
            break

        def phi(t: float, x=x, g=g) -> float:
            y = x + t * g
            if feasible is not None and not feasible(y):
                return -math.inf
            v = sign * f.safe(y)
            return v if math.isfinite(v) else -math.inf

        t = line_search(phi, _bracket(phi))
        x_new = x + t * g
        if np.linalg.norm(x_new - x) < tol * max(1.0, np.linalg.norm(x)):
            x = x_new
            break
        x = x_new
    return x


# --------------------------------------------------------------------------- satu variabel


def one_variable(
    func: str, method: str, maximize: bool, lower: float | None, upper: float | None, x0: float | None, tol: float
) -> SolverResponse:
    f = Expr(func)
    if len(f.variables) != 1:
        raise SolverError("Fungsi satu variabel harus memuat tepat satu variabel (mis. x).")
    v = f.variables[0]
    sign = 1 if maximize else -1
    rows = []
    if method == "bisection":
        if lower is None or upper is None or lower >= upper:
            raise SolverError("Biseksi memerlukan batas bawah < batas atas.")
        lo, hi = lower, upper
        d_lo, d_hi = sign * f.grad([lo])[0], sign * f.grad([hi])[0]
        if d_lo < 0 or d_hi > 0:
            raise SolverError(
                "Biseksi memerlukan f′ berubah tanda di dalam interval (f′(bawah) ≥ 0 ≥ f′(atas) untuk maksimasi)."
            )
        k = 0
        while hi - lo > 2 * tol and k < 200:
            mid = (lo + hi) / 2
            d = sign * f.grad([mid])[0]
            rows.append([k, _r(lo), _r(hi), _r(mid), _r(sign * d), _r(f([mid]))])
            if d >= 0:
                lo = mid
            else:
                hi = mid
            k += 1
        x_star = (lo + hi) / 2
        cols = ["Iterasi", "x̲ (bawah)", "x̄ (atas)", "x′ = (x̲ + x̄)/2", "f′(x′)", "f(x′)"]
        explanation = (
            "Bila f′(x′) ≥ 0 (maksimasi) titik optimum di kanan → x̲ = x′; bila < 0 → x̄ = x′. Berhenti saat x̄ − x̲ ≤ 2ε."
        )
        formula = r"x' = \frac{\underline{x} + \bar{x}}{2}"
    elif method == "newton":
        if x0 is None:
            raise SolverError("Metode Newton memerlukan titik awal x₀.")
        x = float(x0)
        for k in range(100):
            d1 = f.grad([x])[0]
            d2 = f.hessian([x])[0, 0]
            if d2 == 0:
                raise SolverError("f″(x) = 0: metode Newton tidak dapat dilanjutkan.")
            x_new = x - d1 / d2
            rows.append([k, _r(x), _r(f([x])), _r(d1), _r(d2), _r(x_new)])
            if abs(x_new - x) <= tol:
                x = x_new
                break
            x = x_new
        x_star = x
        cols = ["Iterasi", "xᵢ", "f(xᵢ)", "f′(xᵢ)", "f″(xᵢ)", "xᵢ₊₁"]
        explanation = "Aproksimasi kuadratik (deret Taylor) di sekitar xᵢ lalu loncat ke titik stasionernya. Berhenti saat |xᵢ₊₁ − xᵢ| ≤ ε."
        formula = r"x_{i+1} = x_i - \frac{f'(x_i)}{f''(x_i)}"
    else:
        raise SolverError("Metode harus bisection atau newton.")
    fx = f([x_star])
    second = f.hessian([x_star])[0, 0]
    kind = "maksimum lokal" if second < 0 else "minimum lokal" if second > 0 else "titik stasioner"
    table = NamedTable(title="Iterasi", columns=cols, rows=rows)
    grid = np.linspace((lower if lower is not None else x_star - 2), (upper if upper is not None else x_star + 2), 300)
    chart = Chart(
        id="one-var",
        title="Grafik fungsi",
        spec=plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": grid.tolist(),
                    "y": [f.safe([g]) for g in grid],
                    "name": "f(x)",
                },
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": [x_star],
                    "y": [fx],
                    "name": "Optimum",
                    "marker": {"size": 12, "color": "#ef4444"},
                },
            ],
            f"f({v}) = {func}",
            xaxis={"title": {"text": v}},
        ),
    )
    return SolverResponse(
        result={"x": x_star, "f": fx, "iterations": len(rows)},
        steps=[
            Step(title="Fungsi", latex=f"f({v}) = {latexify(func)}"),
            Step(
                title="Metode " + ("biseksi" if method == "bisection" else "Newton"),
                explanation=explanation,
                latex=formula,
                table=table,
            ),
            Step(
                title="Hasil",
                explanation=f"f″(x*) = {second:.4g} → {kind}.",
                latex=rf"x^* \approx {x_star:.6f},\quad f(x^*) \approx {fx:.6f}",
            ),
        ],
        tables=[table],
        charts=[chart],
        summary=summary_items([(f"{v}*", x_star), ("f(x*)", fx), ("Iterasi", len(rows)), ("Jenis titik", kind)]),
        conclusion=f"{'Maksimum' if maximize else 'Minimum'} di {v}* ≈ {x_star:.6f} dengan f ≈ {fx:.6f} ({len(rows)} iterasi).",
    )


# --------------------------------------------------------------------------- gradient search


def _contour(f: Expr, path: np.ndarray, title: str, extra: list | None = None) -> Chart:
    lo = path.min(axis=0)
    hi = path.max(axis=0)
    span = np.maximum(hi - lo, 1.0)
    xs = np.linspace(lo[0] - 0.4 * span[0], hi[0] + 0.4 * span[0], 70)
    ys = np.linspace(lo[1] - 0.4 * span[1], hi[1] + 0.4 * span[1], 70)
    z = [[f.safe([x, y]) for x in xs] for y in ys]
    traces = [
        {
            "type": "contour",
            "x": xs.tolist(),
            "y": ys.tolist(),
            "z": z,
            "colorscale": "Viridis",
            "contours": {"coloring": "heatmap"},
            "showscale": False,
            "name": "f",
        },
        {
            "type": "scatter",
            "mode": "lines+markers",
            "x": path[:, 0].tolist(),
            "y": path[:, 1].tolist(),
            "line": {"color": "#ef4444"},
            "marker": {"size": 6},
            "name": "Lintasan",
        },
    ] + (extra or [])
    return Chart(
        id="contour",
        title="Kontur & lintasan",
        spec=plotly_figure(
            traces,
            title,
            xaxis={"title": {"text": f.variables[0]}},
            yaxis={"title": {"text": f.variables[1]}},
            height=460,
        ),
    )


def gradient_search(func: str, x0: list[float], maximize: bool, tol: float) -> SolverResponse:
    f = Expr(func)
    if len(x0) != len(f.variables):
        raise SolverError(f"Titik awal harus berisi {len(f.variables)} nilai ({', '.join(f.variables)}).")
    sign = 1 if maximize else -1
    rec: list = []
    x = ascent(f, x0, sign, tol=tol, record=rec)
    rows = []
    for k, xk, _, g in rec[:60]:
        rows.append([k, _vec(xk), _r(f(xk)), _vec(sign * g)])
    table = NamedTable(title="Iterasi gradient search", columns=["Iterasi", "x", "f(x)", "∇f(x)"], rows=rows)
    charts = [_contour(f, np.array([r[1] for r in rec]), "Lintasan gradient search")] if len(f.variables) == 2 else []
    return SolverResponse(
        result={"x": x.tolist(), "f": f(x), "iterations": len(rec) - 1},
        steps=[
            Step(title="Fungsi", latex=f"f = {latexify(func)}"),
            Step(
                title="Prosedur gradient search",
                explanation="Pada setiap iterasi, bergerak searah gradien (naik tercuram) sejauh t* yang memaksimumkan f(x + t∇f) "
                "(line search golden section), lalu ulangi sampai |∂f/∂xⱼ| ≤ ε untuk semua j.",
                latex=r"\mathbf{x}' = \mathbf{x} + t^*\nabla f(\mathbf{x}),\quad t^* = \arg\max_{t \ge 0} f(\mathbf{x} + t\nabla f(\mathbf{x}))",
                table=table,
            ),
        ],
        tables=[table],
        charts=charts,
        summary=summary_items([("x*", _vec(x)), ("f(x*)", f(x)), ("Iterasi", len(rec) - 1)]),
        conclusion=f"{'Maksimum' if maximize else 'Minimum'} lokal di x* ≈ {_vec(x)} dengan f ≈ {f(x):.6f}.",
    )


# --------------------------------------------------------------------------- kendala nonlinear


def _parse_constraints(text: str, variables: list[str] | None):
    cons = []
    for raw in text.replace("\r", "").split("\n"):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        for op in ("<=", ">="):
            if op in line:
                lhs, rhs = line.split(op, 1)
                g = Expr(f"({lhs}) - ({rhs})" if op == "<=" else f"({rhs}) - ({lhs})", variables)
                cons.append((g, line))
                break
        else:
            raise SolverError(f"Kendala “{line}” harus memakai ≤ (<=) atau ≥ (>=).")
    return cons


def kkt(func: str, constraints: str, maximize: bool, nonneg: bool) -> SolverResponse:
    from scipy.optimize import minimize  # hanya untuk mencari kandidat; kondisi KKT diperiksa manual

    f = Expr(func)
    variables = f.variables
    cons = _parse_constraints(constraints, None)
    variables = sorted(
        set(variables) | {v for g, _ in cons for v in g.variables},
        key=lambda s: (s.rstrip("0123456789"), int(s[len(s.rstrip("0123456789")) :] or 0)),
    )
    f = Expr(func, variables)
    cons = _parse_constraints(constraints, variables)
    n = len(variables)
    sign = 1 if maximize else -1
    best = None
    for start in [np.full(n, 0.5), np.ones(n), np.full(n, 2.0), np.zeros(n) + 0.1]:
        res = minimize(
            lambda x: -sign * f.safe(x),
            start,
            method="SLSQP",
            bounds=[(0, None)] * n if nonneg else None,
            constraints=[{"type": "ineq", "fun": (lambda x, g=g: -g(x))} for g, _ in cons],
        )
        if res.success and (best is None or -res.fun > -best.fun):
            best = res
    if best is None:
        raise SolverError("Tidak menemukan kandidat solusi yang layak.")
    x = np.where(np.abs(best.x) < 1e-7, 0.0, best.x)
    grad_f = sign * f.grad(x)
    active = [i for i, (g, _) in enumerate(cons) if abs(g(x)) < 1e-5]
    cols = [cons[i][0].grad(x) for i in active]
    zero_vars = [j for j in range(n) if nonneg and abs(x[j]) < 1e-7]
    # ∇f − Σ uᵢ∇gᵢ + Σ vⱼ eⱼ = 0  dengan uᵢ ≥ 0, vⱼ ≥ 0  → kuadrat terkecil nonnegatif
    from scipy.optimize import nnls

    mat = np.column_stack(cols + [-np.eye(n)[j] for j in zero_vars]) if cols or zero_vars else np.zeros((n, 0))
    if mat.shape[1]:
        mult, resid = nnls(mat, grad_f)
    else:
        mult, resid = np.zeros(0), float(np.linalg.norm(grad_f))
    u = np.zeros(len(cons))
    for k, i in enumerate(active):
        u[i] = mult[k]
    rows = []
    for j, v in enumerate(variables):
        partial = grad_f[j] - sum(u[i] * cons[i][0].grad(x)[j] for i in range(len(cons)))
        rows.append(
            [
                f"∂/∂{v}",
                _r(partial),
                "≤ 0" if nonneg else "= 0",
                f"{v} = {_r(x[j])}",
                "✓"
                if (partial <= 1e-5 if nonneg else abs(partial) <= 1e-5) and (not nonneg or abs(x[j] * partial) < 1e-4)
                else "✗",
            ]
        )
    for i, (g, line) in enumerate(cons):
        rows.append(
            [
                f"Kendala {i + 1}: {line}",
                _r(g(x)),
                "≤ 0",
                f"u{i + 1} = {_r(u[i])}",
                "✓" if g(x) <= 1e-5 and abs(u[i] * g(x)) < 1e-4 else "✗",
            ]
        )
    table = NamedTable(
        title="Pemeriksaan kondisi KKT",
        columns=["Kondisi", "Nilai", "Syarat", "Pengali / variabel", "Terpenuhi"],
        rows=rows,
    )
    ok = resid < 1e-4
    return SolverResponse(
        result={"x": x.tolist(), "f": f(x), "multipliers": u.tolist(), "kkt_satisfied": bool(ok)},
        steps=[
            Step(
                title="Masalah",
                latex=rf"\{'max' if maximize else 'min'}\ f = {latexify(func)}\quad \text{{s.t.}}\ "
                + r",\ ".join(latexify(line).replace("<=", r"\le").replace(">=", r"\ge") for _, line in cons)
                + (r",\ \mathbf{x} \ge 0" if nonneg else ""),
            ),
            Step(
                title="Kondisi Karush-Kuhn-Tucker",
                explanation="Untuk maksimasi dengan gᵢ(x) ≤ bᵢ dan x ≥ 0: (1) ∂f/∂xⱼ − Σuᵢ∂gᵢ/∂xⱼ ≤ 0, (2) xⱼ·(…) = 0, (3) gᵢ(x) − bᵢ ≤ 0, "
                "(4) uᵢ(gᵢ(x) − bᵢ) = 0, (5) xⱼ ≥ 0, (6) uᵢ ≥ 0. Untuk masalah konveks, KKT juga cukup untuk optimal global.",
            ),
            Step(
                title="Kandidat solusi",
                explanation="Kandidat dicari secara numerik (SLSQP), lalu pengali uᵢ dihitung dari kendala aktif dan semua kondisi diperiksa.",
                latex=r"\mathbf{x}^* \approx " + _vec(x),
            ),
            Step(
                title="Pemeriksaan kondisi",
                table=table,
                explanation="Semua kondisi KKT terpenuhi."
                if ok
                else "Ada kondisi yang tidak terpenuhi; titik mungkin bukan optimal reguler.",
            ),
        ],
        tables=[table],
        summary=summary_items(
            [("x*", _vec(x)), ("f(x*)", f(x)), ("Pengali u", _vec(u)), ("KKT terpenuhi", "Ya" if ok else "Tidak")]
        ),
        conclusion=f"x* ≈ {_vec(x)}, f* ≈ {f(x):.6g}, pengali u = {_vec(u)}. Kondisi KKT {'terpenuhi' if ok else 'tidak terpenuhi'}.",
    )


# --------------------------------------------------------------------------- quadratic programming (Wolfe)


def quadratic(objective: str, constraints: str) -> SolverResponse:
    """Maks f(x) = cx − ½xᵀQx dengan Ax ≤ b, x ≥ 0 lewat simpleks termodifikasi pada sistem KKT (Bab 13.7)."""
    lin = parse_model("max Z = 0x1\n" + constraints)
    f0 = Expr(objective)
    variables = sorted(
        set(f0.variables) | {v for k in lin.constraints for v in k.coeffs},
        key=lambda s: (s.rstrip("0123456789"), int(s[len(s.rstrip("0123456789")) :] or 0)),
    )
    f = Expr(objective, variables)
    n = len(variables)
    if any(k.op != "<=" or k.rhs < 0 for k in lin.constraints):
        raise SolverError("QP di sini memerlukan kendala ≤ dengan ruas kanan ≥ 0.")
    zero = np.zeros(n)
    c = f.grad(zero)
    q = -f.hessian(zero)
    if np.min(np.linalg.eigvalsh(q)) < -1e-8:
        raise SolverError(
            "Fungsi tujuan tidak konkaf (Q tidak semidefinit positif); metode simpleks termodifikasi memerlukan QP konveks."
        )
    m = len(lin.constraints)
    a = np.array([[float(k.coeffs.get(v, 0)) for v in variables] for k in lin.constraints])
    b = np.array([float(k.rhs) for k in lin.constraints])

    def fr(v: float) -> Fraction:
        return Fraction(v).limit_denominator(10**6)

    # Variabel: x (n), u (m), y (n), v (m slack), z (n artifisial)
    names = (
        variables
        + [f"u{i + 1}" for i in range(m)]
        + [f"y{j + 1}" for j in range(n)]
        + [f"v{i + 1}" for i in range(m)]
        + [f"z{j + 1}" for j in range(n)]
    )
    rows: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    basis: list[int] = []
    for j in range(n):  # Qx + Aᵀu − y + z = c
        row = (
            [fr(q[j, k]) for k in range(n)]
            + [fr(a[i, j]) for i in range(m)]
            + [Fraction(-1) if k == j else Fraction(0) for k in range(n)]
            + [Fraction(0)] * m
            + [Fraction(1) if k == j else Fraction(0) for k in range(n)]
        )
        cj = fr(c[j])
        if cj < 0:
            row = [-x for x in row]
            row[n + m + n + m + j] = Fraction(1)
            cj = -cj
        rows.append(row)
        rhs.append(cj)
        basis.append(n + m + n + m + j)
    for i in range(m):  # Ax + v = b
        rows.append(
            [fr(a[i, k]) for k in range(n)]
            + [Fraction(0)] * (m + n)
            + [Fraction(1) if k == i else Fraction(0) for k in range(m)]
            + [Fraction(0)] * n
        )
        rhs.append(fr(b[i]))
        basis.append(n + m + n + i)
    kinds = ["x"] * (n + m + n + m) + ["a"] * n
    sf = tableau.StandardForm(names, kinds, rows, rhs, basis, [Fraction(0)] * len(names), [1] * len(rows), {}, 1)
    t = tableau.Tableau.from_objective(sf, [MNum(Fraction(-1)) if k == "a" else MNum() for k in kinds])
    complement = (
        {j: n + m + j for j in range(n)}
        | {n + m + j: j for j in range(n)}
        | {n + i: n + m + n + i for i in range(m)}
        | {n + m + n + i: n + i for i in range(m)}
    )
    steps = [
        Step(
            title="Bentuk QP",
            latex=rf"\max f(\mathbf{{x}}) = {latexify(objective)} = \mathbf{{c}}\mathbf{{x}} - \tfrac{{1}}{{2}}\mathbf{{x}}^\top\mathbf{{Q}}\mathbf{{x}}",
            matrix=q.round(6).tolist(),
            explanation="Matriks Q (konkaf ⇔ Q semidefinit positif).",
        ),
        Step(
            title="Sistem KKT linier + kendala komplementer",
            explanation="Qx + Aᵀu − y = cᵀ, Ax + v = b, x, u, y, v ≥ 0, dengan xⱼyⱼ = 0 dan uᵢvᵢ = 0. Fase 1 simpleks meminimumkan Σ zⱼ "
            "(artifisial) dengan aturan masuk terbatas: sebuah variabel tidak boleh masuk basis bila komplemennya sudah di basis.",
            table=t.snapshot(),
        ),
    ]
    for it in range(1, 100):
        in_basis = set(sf.basis)
        cand = [j for j in t.nonbasic() if t.row0[j] < 0 and complement.get(j) not in in_basis]
        if not cand:
            break
        col = min(cand, key=lambda j: (t.row0[j].key(), j))
        ratios = {i: sf.rhs[i] / sf.rows[i][col] for i in range(len(rows)) if sf.rows[i][col] > 0}
        if not ratios:
            raise SolverError("Sistem KKT tak terbatas.")
        r = min(ratios, key=lambda i: (ratios[i], sf.basis[i]))
        steps.append(
            Step(
                title=f"Iterasi {it}",
                explanation=f"Masuk {names[col]} (komplemen {names[complement[col]] if col in complement else '—'} tidak di basis), keluar {names[sf.basis[r]]}.",
                table=t.snapshot(ratios),
            )
        )
        t.pivot(r, col)
    if t.z.a != 0:
        raise SolverError("Fase 1 tidak mencapai Σz = 0; tidak ditemukan solusi KKT.")
    vals = {j: Fraction(0) for j in range(len(names))}
    for i, j in enumerate(sf.basis):
        vals[j] = sf.rhs[i]
    x = np.array([float(vals[j]) for j in range(n)])
    steps.append(
        Step(
            title="Solusi optimal",
            explanation="Σz = 0 sehingga solusi memenuhi semua kondisi KKT; karena QP konveks, solusi ini optimal global.",
            table=t.snapshot(),
            latex=", ".join(f"{v} = {fmt_frac(vals[j])}" for j, v in enumerate(variables))
            + rf",\quad f^* = {f(x):.6g}",
        )
    )
    return SolverResponse(
        result={"x": x.tolist(), "f": f(x)},
        steps=steps,
        tables=[
            NamedTable(
                title="Solusi optimal",
                columns=["Variabel", "Nilai"],
                rows=[[v, fmt_frac(vals[j])] for j, v in enumerate(variables)],
            )
        ],
        summary=summary_items([(v, fmt_frac(vals[j])) for j, v in enumerate(variables)] + [("f*", f(x))]),
        conclusion=f"Solusi optimal QP: {', '.join(f'{v} = {fmt_frac(vals[j])}' for j, v in enumerate(variables))} dengan f* = {f(x):.6g}.",
    )


# --------------------------------------------------------------------------- separable programming


def separable(terms: str, constraints: str, segments: int) -> SolverResponse:
    """terms: satu baris per variabel ``x1: 3x1 - x1^2 ; 0..4`` (fungsi konkaf satu variabel dan rentangnya)."""
    if not 1 <= segments <= 20:
        raise SolverError("Jumlah segmen harus 1–20.")
    funcs = []
    for raw in terms.replace("\r", "").split("\n"):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        try:
            head, rest = line.split(":", 1)
            expr, rng = rest.rsplit(";", 1)
            lo, hi = (float(p) for p in rng.replace("..", " ").split())
        except ValueError as exc:
            raise SolverError(f"Baris “{line}”: gunakan format “x1: 3x1 - x1^2 ; 0..4”.") from exc
        v = head.strip()
        f = Expr(expr, [v])
        if hi <= lo:
            raise SolverError(f"Rentang {v} tidak valid.")
        funcs.append((v, f, lo, hi, expr.strip()))
    if not funcs:
        raise SolverError("Isi minimal satu fungsi terpisah.")
    lin = parse_model("max Z = 0x1\n" + constraints) if constraints.strip() else None
    obj: dict[str, Fraction] = {}
    cons: list[Constraint] = []
    var_names: list[str] = []
    seg_rows = []
    concave_ok = True
    for v, f, lo, hi, _expr in funcs:
        pts = np.linspace(lo, hi, segments + 1)
        slopes = [(f([pts[k + 1]]) - f([pts[k]])) / (pts[k + 1] - pts[k]) for k in range(segments)]
        if any(slopes[k + 1] > slopes[k] + 1e-9 for k in range(segments - 1)):
            concave_ok = False
        seg_vars = []
        for k in range(segments):
            name = f"{v}_{k + 1}"
            seg_vars.append(name)
            var_names.append(name)
            obj[name] = Fraction(slopes[k]).limit_denominator(10**6)
            cons.append(
                Constraint(
                    {name: Fraction(1)},
                    "<=",
                    Fraction(pts[k + 1] - pts[k]).limit_denominator(10**6),
                    name=f"{name} ≤ {pts[k + 1] - pts[k]:.4g}",
                )
            )
            seg_rows.append([v, k + 1, f"[{pts[k]:.4g}, {pts[k + 1]:.4g}]", _r(slopes[k])])
        if lin:
            for kcon in lin.constraints:
                if v in kcon.coeffs:
                    coef = kcon.coeffs.pop(v)
                    for sv in seg_vars:
                        kcon.coeffs[sv] = coef
                    kcon.rhs -= coef * Fraction(lo).limit_denominator(10**6)
    if lin:
        leftover = {v for k in lin.constraints for v in k.coeffs if v not in var_names}
        if leftover:
            raise SolverError(f"Variabel {', '.join(sorted(leftover))} di kendala tidak memiliki fungsi terpisah.")
        cons += lin.constraints
    model = LPModel("max", obj, cons, var_names)
    out = tableau.solve(model, "bigm", record=False)
    if out.status != "optimal":
        raise SolverError("Aproksimasi LP tidak memiliki solusi optimal.")
    xs = {v: lo + sum(float(out.x[f"{v}_{k + 1}"]) for k in range(segments)) for v, _, lo, _, _ in funcs}
    true_val = sum(f([xs[v]]) for v, f, *_ in funcs)
    seg_table = NamedTable(
        title="Segmen linier", columns=["Variabel", "Segmen", "Rentang", "Kemiringan (laba marjinal)"], rows=seg_rows
    )
    warnings = (
        []
        if concave_ok
        else [
            "Ada fungsi yang tidak konkaf (kemiringan naik): segmen bisa terisi tidak berurutan dan aproksimasi menjadi tidak valid."
        ]
    )
    return SolverResponse(
        result={
            "x": xs,
            "approx_value": float(out.z) + sum(f([lo]) for _, f, lo, _, _ in funcs),
            "true_value": true_val,
        },
        steps=[
            Step(
                title="Fungsi terpisah",
                latex=r"f(\mathbf{x}) = " + " + ".join(f"\\left({latexify(e)}\\right)" for *_, e in funcs),
            ),
            Step(
                title="Aproksimasi linier sepotong-sepotong",
                explanation="Setiap fungsi konkaf dibagi menjadi segmen dengan kemiringan menurun. xⱼ = Σ xⱼₖ dengan 0 ≤ xⱼₖ ≤ lebar segmen. "
                "Karena kemiringan menurun, LP otomatis mengisi segmen secara berurutan.",
                table=seg_table,
            ),
            Step(
                title="Solusi LP aproksimasi",
                latex=", ".join(f"{v} \\approx {val:.4g}" for v, val in xs.items())
                + rf",\quad f \approx {true_val:.6g}",
            ),
        ],
        tables=[
            NamedTable(title="Solusi", columns=["Variabel", "Nilai"], rows=[[v, _r(val)] for v, val in xs.items()]),
            seg_table,
        ],
        summary=summary_items([(v, val) for v, val in xs.items()] + [("f(x) sebenarnya", true_val)]),
        warnings=warnings,
        conclusion=f"Solusi aproksimasi {', '.join(f'{v} ≈ {val:.4g}' for v, val in xs.items())} dengan nilai fungsi sebenarnya ≈ {true_val:.6g}.",
    )


# --------------------------------------------------------------------------- Frank-Wolfe


def frank_wolfe(
    func: str, constraints: str, x0: list[float], maximize: bool, max_iter: int = 500, tol: float = 1e-4
) -> SolverResponse:
    lin = parse_model("max Z = 0x1\n" + constraints)
    f0 = Expr(func)
    variables = sorted(
        set(f0.variables) | {v for k in lin.constraints for v in k.coeffs},
        key=lambda s: (s.rstrip("0123456789"), int(s[len(s.rstrip("0123456789")) :] or 0)),
    )
    f = Expr(func, variables)
    sign = 1 if maximize else -1
    x = np.array(x0, dtype=float)
    if x.size != len(variables):
        raise SolverError(f"Titik awal harus berisi {len(variables)} nilai.")
    rows = []
    path = [x.copy()]
    for k in range(1, max_iter + 1):
        g = sign * f.grad(x)
        lp = LPModel(
            "max",
            {v: Fraction(float(g[j])).limit_denominator(10**6) for j, v in enumerate(variables)},
            [Constraint(dict(c.coeffs), c.op, c.rhs, c.name) for c in lin.constraints],
            list(variables),
        )
        out = tableau.solve(lp, "bigm", record=False)
        if out.status != "optimal":
            raise SolverError("Subproblem LP tidak memiliki solusi optimal (daerah layak tidak terbatas?).")
        x_lp = np.array([float(out.x[v]) for v in variables])
        d = x_lp - x
        gap = float(g @ d)
        t = line_search(lambda t, x=x, d=d: sign * f.safe(x + t * d), 1.0)
        x_new = x + t * d
        rows.append([k, _vec(x), _vec(g), _vec(x_lp), _r(t), _vec(x_new), _r(f(x_new))])
        path.append(x_new.copy())
        x = x_new
        if gap < tol:
            break
    shown = rows if len(rows) <= 40 else rows[:30] + [["…", "", "", "", "", "", ""]] + rows[-5:]
    table = NamedTable(
        title="Iterasi Frank-Wolfe", columns=["k", "x⁽ᵏ⁻¹⁾", "∇f", "Solusi LP xₗₚ", "t*", "x⁽ᵏ⁾", "f(x⁽ᵏ⁾)"], rows=shown
    )
    charts = [_contour(f, np.array(path), "Lintasan Frank-Wolfe")] if len(variables) == 2 else []
    return SolverResponse(
        result={"x": x.tolist(), "f": f(x), "iterations": len(rows)},
        steps=[
            Step(title="Masalah", latex=rf"\{'max' if maximize else 'min'}\ f = {latexify(func)}"),
            Step(
                title="Algoritma Frank-Wolfe (aproksimasi linier berurutan)",
                explanation="Linearkan f di titik saat ini: selesaikan LP maks ∇f(x)·x atas kendala linier (simpleks), lalu cari t* ∈ [0, 1] "
                "yang memaksimumkan f pada ruas garis dari x ke solusi LP. Berhenti bila ∇f·(xₗₚ − x) ≈ 0. Solusi LP sering "
                "bergantian antar titik sudut (zig-zag), sehingga konvergensinya lambat — seperti dicatat di Bab 13.9.",
                table=table,
            ),
        ],
        tables=[table],
        charts=charts,
        summary=summary_items([("x*", _vec(x)), ("f(x*)", f(x)), ("Iterasi", len(rows))]),
        conclusion=f"Frank-Wolfe mendekati x* ≈ {_vec(x)} dengan f ≈ {f(x):.6g}.",
    )


# --------------------------------------------------------------------------- SUMT


def sumt(
    func: str, constraints: str, x0: list[float], maximize: bool, r0: float = 1.0, theta: float = 0.01, rounds: int = 6
) -> SolverResponse:
    f0 = Expr(func)
    cons0 = _parse_constraints(constraints, None)
    variables = sorted(
        set(f0.variables) | {v for g, _ in cons0 for v in g.variables},
        key=lambda s: (s.rstrip("0123456789"), int(s[len(s.rstrip("0123456789")) :] or 0)),
    )
    f = Expr(func, variables)
    cons = _parse_constraints(constraints, variables)
    sign = 1 if maximize else -1
    x = np.array(x0, dtype=float)
    if x.size != len(variables):
        raise SolverError(f"Titik awal harus berisi {len(variables)} nilai.")

    def interior(y) -> bool:
        return bool(np.all(y > 0) and all(g(y) < 0 for g, _ in cons))

    if not interior(x):
        raise SolverError(
            "Titik awal SUMT harus berada di interior: semua variabel > 0 dan semua kendala terpenuhi ketat."
        )
    r = r0
    rows = []
    path = [x.copy()]
    for k in range(rounds):

        class Barrier:
            variables = f.variables

            def __init__(self, rr: float):
                self.rr = rr

            def safe(self, y):
                if not interior(y):
                    return -math.inf
                return sign * f(y) - self.rr * (sum(1 / -g(y) for g, _ in cons) + sum(1 / v for v in y))

            __call__ = safe

            def grad(self, y, h=1e-7):
                y = np.asarray(y, dtype=float)
                out = np.zeros_like(y)
                for i in range(y.size):
                    e = np.zeros_like(y)
                    e[i] = h * max(1, abs(y[i]))
                    out[i] = (self.safe(y + e) - self.safe(y - e)) / (2 * e[i])
                return out

        p = Barrier(r)
        x = ascent(p, x, 1.0, tol=1e-8, max_iter=2000, feasible=interior)
        rows.append([k + 1, f"{r:g}", _vec(x), _r(f(x))])
        path.append(x.copy())
        r *= theta
    table = NamedTable(title="Iterasi SUMT", columns=["k", "r", "x(r)", "f(x(r))"], rows=rows)
    charts = [_contour(f, np.array(path), "Lintasan SUMT (barrier)")] if len(variables) == 2 else []
    return SolverResponse(
        result={"x": x.tolist(), "f": f(x)},
        steps=[
            Step(
                title="Fungsi barrier",
                latex=r"P(\mathbf{x}; r) = f(\mathbf{x}) - r\left(\sum_i \frac{1}{b_i - g_i(\mathbf{x})} + \sum_j \frac{1}{x_j}\right)",
                explanation="Penalti barrier mencegah iterasi keluar daerah layak. Untuk r yang mengecil (r ← θr), maksimum P(x; r) mendekati solusi optimal.",
            ),
            Step(
                title="Barisan maksimisasi tanpa kendala",
                explanation=f"Setiap P(x; r) dimaksimumkan dengan gradient search dari solusi sebelumnya; r dikalikan θ = {theta:g}.",
                table=table,
            ),
        ],
        tables=[table],
        charts=charts,
        summary=summary_items([("x*", _vec(x)), ("f(x*)", f(x)), ("r terakhir", r / theta)]),
        conclusion=f"SUMT mendekati x* ≈ {_vec(x)} dengan f ≈ {f(x):.6g}.",
    )


# --------------------------------------------------------------------------- multistart (nonkonveks)


def multistart(
    func: str, lower: list[float], upper: list[float], starts: int, maximize: bool, seed: int = 0
) -> SolverResponse:
    f = Expr(func)
    n = len(f.variables)
    if len(lower) != n or len(upper) != n:
        raise SolverError(f"Batas bawah/atas harus berisi {n} nilai.")
    lo, hi = np.array(lower, float), np.array(upper, float)
    if np.any(hi <= lo):
        raise SolverError("Setiap batas atas harus lebih besar dari batas bawah.")
    if not 1 <= starts <= 100:
        raise SolverError("Jumlah titik awal harus 1–100.")
    sign = 1 if maximize else -1
    rng = np.random.default_rng(seed)
    pts = lo + (hi - lo) * rng.random((starts, n))
    if n == 1:
        pts = np.linspace(lo, hi, starts).reshape(-1, 1)

    def inside(y) -> bool:
        return bool(np.all(y >= lo - 1e-12) and np.all(y <= hi + 1e-12))

    found: list[tuple[np.ndarray, float]] = []
    rows = []
    for k, p in enumerate(pts):
        x = ascent(f, p, sign, tol=1e-7, feasible=inside)
        x = np.clip(x, lo, hi)
        val = f(x)
        rows.append([k + 1, _vec(p), _vec(x), _r(val)])
        if not any(np.linalg.norm(x - q) < 1e-3 * max(1, np.linalg.norm(q)) for q, _ in found):
            found.append((x, val))
    found.sort(key=lambda t: -sign * t[1])
    best_x, best_v = found[0]
    local = NamedTable(
        title="Optimum lokal berbeda yang ditemukan",
        columns=["#", "x", "f(x)"],
        rows=[[i + 1, _vec(x), _r(v)] for i, (x, v) in enumerate(found)],
    )
    charts = []
    if n == 1:
        grid = np.linspace(lo[0], hi[0], 400)
        charts.append(
            Chart(
                id="multistart",
                title="Fungsi & optimum lokal",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "x": grid.tolist(),
                            "y": [f.safe([g]) for g in grid],
                            "name": "f(x)",
                        },
                        {
                            "type": "scatter",
                            "mode": "markers",
                            "x": [float(x[0]) for x, _ in found],
                            "y": [v for _, v in found],
                            "marker": {"size": 10},
                            "name": "Optimum lokal",
                        },
                        {
                            "type": "scatter",
                            "mode": "markers",
                            "x": [float(best_x[0])],
                            "y": [best_v],
                            "marker": {"size": 16, "symbol": "star", "color": "#ef4444"},
                            "name": "Terbaik",
                        },
                    ],
                    "Fungsi nonkonveks dengan beberapa optimum lokal",
                ),
            )
        )
    elif n == 2:
        charts.append(_contour(f, np.array([x for x, _ in found] + [lo, hi]), "Optimum lokal (titik merah)"))
    return SolverResponse(
        result={"x": best_x.tolist(), "f": best_v, "local_optima": len(found)},
        steps=[
            Step(title="Fungsi", latex=f"f = {latexify(func)}"),
            Step(
                title="Multistart",
                explanation="Masalah nonkonveks bisa memiliki banyak optimum lokal. Jalankan gradient search dari banyak titik awal di dalam kotak batas, "
                "kumpulkan optimum lokal yang berbeda, lalu ambil yang terbaik (tidak menjamin optimum global, tetapi meningkatkan peluangnya).",
                table=Table(columns=["Start", "Titik awal", "Konvergen ke", "f"], rows=rows),
            ),
            Step(title="Optimum lokal", table=local),
        ],
        tables=[local],
        charts=charts,
        summary=summary_items(
            [("x terbaik", _vec(best_x)), ("f terbaik", best_v), ("Optimum lokal berbeda", len(found))]
        ),
        conclusion=f"Ditemukan {len(found)} optimum lokal; yang terbaik x ≈ {_vec(best_x)} dengan f ≈ {best_v:.6g}.",
    )
