"""Algoritma LP lain (Bab 7): dual simpleks, LP parametrik, teknik batas atas, titik interior, goal programming."""

from __future__ import annotations

import re
from fractions import Fraction

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items
from app.solvers.lp import tableau
from app.solvers.lp.matrix import inverse, matvec, vecmat
from app.solvers.lp.model import Constraint, LPModel, parse_linear, parse_model
from app.solvers.lp.numbers import MNum, fmt_frac, frac, latex_frac

# =========================================================================== dual simpleks


def dual_simplex(model: LPModel) -> SolverResponse:
    if model.free or model.nonpositive:
        raise SolverError("Dual simpleks di sini membutuhkan semua variabel ≥ 0.")
    n = len(model.variables)
    rows: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    for k in model.constraints:
        a = [k.coeffs.get(v, Fraction(0)) for v in model.variables]
        if k.op in ("<=", "="):
            rows.append(list(a))
            rhs.append(k.rhs)
        if k.op in (">=", "="):
            rows.append([-x for x in a])
            rhs.append(-k.rhs)
    m = len(rows)
    sigma = 1 if model.sense == "max" else -1
    c = [sigma * x for x in model.c()]
    if any(x > 0 for x in c):
        raise SolverError(
            "Dual simpleks memerlukan tabel awal yang 'super optimal' (semua koefisien baris 0 ≥ 0), mis. minimasi dengan "
            "biaya nonnegatif. Untuk model ini gunakan simpleks biasa."
        )
    names = list(model.variables) + [f"s{i + 1}" for i in range(m)]
    sf = tableau.StandardForm(
        names,
        ["x"] * n + ["s"] * m,
        [r + [Fraction(int(i == j)) for j in range(m)] for i, r in enumerate(rows)],
        rhs,
        list(range(n, n + m)),
        c + [Fraction(0)] * m,
        [1] * m,
        {v: [(j, 1)] for j, v in enumerate(model.variables)},
        sigma,
    )
    t = tableau.Tableau.from_objective(sf, [MNum(x) for x in sf.c])
    steps = [
        Step(title="Model", latex=model.latex()),
        Step(
            title="Ubah kendala ≥ menjadi ≤ (kalikan −1) dan tambahkan slack",
            explanation="Solusi basis awal (slack) tidak layak (ada RHS negatif) tetapi baris 0 sudah memenuhi uji optimalitas. "
            "Dual simpleks menjaga optimalitas sambil memperbaiki kelayakan.",
            table=t.snapshot(),
        ),
    ]
    for it in range(1, 50):
        neg = [i for i in range(m) if sf.rhs[i] < 0]
        if not neg:
            x, z = tableau._extract(t)
            steps.append(
                Step(
                    title="Layak & optimal",
                    explanation="Semua ruas kanan ≥ 0: solusi sekarang layak, sehingga optimal.",
                    table=t.snapshot(),
                )
            )
            return SolverResponse(
                result={"status": "optimal", "z": float(z), "x": {v: float(val) for v, val in x.items()}},
                steps=steps,
                tables=[
                    NamedTable(
                        title="Solusi optimal",
                        columns=["Variabel", "Nilai"],
                        rows=[[v, fmt_frac(val)] for v, val in x.items()],
                    )
                ],
                summary=summary_items(
                    [(f"{model.objective_name}*", fmt_frac(z))] + [(v, fmt_frac(val)) for v, val in x.items()]
                ),
                conclusion=f"Solusi optimal {', '.join(f'{v} = {fmt_frac(val)}' for v, val in x.items())} dengan {model.objective_name} = {fmt_frac(z)}.",
            )
        r = min(neg, key=lambda i: (sf.rhs[i], i))
        cand = {j: abs(t.row0[j].a / sf.rows[r][j]) for j in t.nonbasic() if sf.rows[r][j] < 0}
        if not cand:
            steps.append(
                Step(
                    title="Tidak layak",
                    explanation=f"Baris {sf.names[sf.basis[r]]} tidak memiliki koefisien negatif: masalah tidak layak.",
                )
            )
            return SolverResponse(
                result={"status": "infeasible"},
                steps=steps,
                conclusion="Masalah tidak layak.",
                summary=summary_items([("Status", "Tidak layak")]),
            )
        col = min(cand, key=lambda j: (cand[j], j))
        steps.append(
            Step(
                title=f"Iterasi {it}",
                explanation=f"Variabel keluar: {sf.names[sf.basis[r]]} (RHS paling negatif, {fmt_frac(sf.rhs[r])}). "
                f"Variabel masuk: {sf.names[col]} — rasio |koefisien baris 0 / koefisien negatif di baris pivot| terkecil "
                f"({fmt_frac(cand[col])}).",
                table=t.snapshot(),
            )
        )
        t.pivot(r, col)
    raise SolverError("Dual simpleks tidak konvergen.")


# =========================================================================== LP parametrik


def parametric(model: LPModel, kind: str, direction: list[float], theta_max: float) -> SolverResponse:
    if theta_max <= 0:
        raise SolverError("θ maksimum harus lebih besar dari 0.")
    alpha = [frac(x) for x in direction]
    expected = len(model.variables) if kind == "objective" else len(model.constraints)
    if len(alpha) != expected:
        raise SolverError(f"Vektor arah perubahan harus berisi {expected} nilai.")
    tmax = frac(theta_max)
    eps = Fraction(1, 10**6)

    def at(theta: Fraction) -> LPModel:
        m = model.copy()
        if kind == "objective":
            m.objective = {
                v: model.objective.get(v, Fraction(0)) + theta * a for v, a in zip(model.variables, alpha, strict=True)
            }
        else:
            for k, a in zip(m.constraints, alpha, strict=True):
                k.rhs = k.rhs + theta * a
        return m

    segments = []
    theta = Fraction(0)
    steps = [
        Step(
            title="Model parametrik",
            explanation=("Koefisien tujuan" if kind == "objective" else "Ruas kanan") + " berubah linier terhadap θ.",
            latex=(
                r"c_j(\theta) = c_j + \alpha_j\theta" if kind == "objective" else r"b_i(\theta) = b_i + \alpha_i\theta"
            )
            + r",\quad \boldsymbol{\alpha} = ("
            + ", ".join(latex_frac(a) for a in alpha)
            + rf"),\quad 0 \le \theta \le {latex_frac(tmax)}",
        )
    ]
    while theta <= tmax and len(segments) < 30:
        m = at(theta if theta == 0 else theta + eps)
        out = tableau.solve(m, "bigm")
        if out.status != "optimal":
            segments.append((theta, tmax, out.status, None, None))
            break
        sf = tableau.standard_form(model)
        keep = [j for j, k in enumerate(sf.kinds) if k != "a"]
        names = [sf.names[j] for j in keep]
        bcols = [names.index(nm) for nm in out.basis_names]
        a_mat = [[row[j] for j in keep] for row in sf.rows]
        b_inv = inverse([[a_mat[i][j] for j in bcols] for i in range(len(a_mat))])
        upper = tmax
        if kind == "objective":
            sf_a = tableau.standard_form(at(Fraction(1)))
            c0 = [sf.c[j] for j in keep]
            c1 = [sf_a.c[j] - sf.c[j] for j in keep]
            y0, y1 = vecmat([c0[j] for j in bcols], b_inv), vecmat([c1[j] for j in bcols], b_inv)
            for j in range(len(names)):
                if j in bcols:
                    continue
                d0 = sum((y0[i] * a_mat[i][j] for i in range(len(a_mat))), Fraction(0)) - c0[j]
                d1 = sum((y1[i] * a_mat[i][j] for i in range(len(a_mat))), Fraction(0)) - c1[j]
                if d1 < 0:
                    upper = min(upper, -d0 / d1)
            x = out.x
            z0 = sum((model.objective.get(v, Fraction(0)) * x[v] for v in model.variables), Fraction(0))
            z1 = sum((a * x[v] for v, a in zip(model.variables, alpha, strict=True)), Fraction(0))
        else:
            b0 = sf.rhs
            b1 = [a * f for a, f in zip(alpha, sf.flip, strict=True)]
            xb0, xb1 = matvec(b_inv, b0), matvec(b_inv, b1)
            for p, q in zip(xb0, xb1, strict=True):
                if q < 0:
                    upper = min(upper, -p / q)
            c_int = [sf.c[j] for j in keep]
            z0 = sf.sigma * sum((c_int[j] * v for j, v in zip(bcols, xb0, strict=True)), Fraction(0))
            z1 = sf.sigma * sum((c_int[j] * v for j, v in zip(bcols, xb1, strict=True)), Fraction(0))
            x = out.x
        segments.append((theta, max(upper, theta), "optimal", out, (z0, z1)))
        if upper >= tmax:
            break
        theta = upper
    rows = []
    for lo, hi, status, out, z in segments:
        if status != "optimal":
            rows.append([f"{fmt_frac(lo)} < θ", "—", "tak terbatas" if status == "unbounded" else "tidak layak"])
            continue
        xs = (
            ", ".join(f"{v} = {fmt_frac(val)}" for v, val in out.x.items())
            if kind == "objective"
            else "basis: " + ", ".join(out.basis_names)
        )
        zt = f"{fmt_frac(z[0])} {'+' if z[1] >= 0 else '−'} {fmt_frac(abs(z[1]))}θ"
        rows.append([f"{fmt_frac(lo)} ≤ θ ≤ {fmt_frac(hi)}", xs, zt])
    table = NamedTable(title="Solusi optimal sebagai fungsi θ", columns=["Rentang θ", "Solusi", "Z*(θ)"], rows=rows)
    steps.append(
        Step(
            title="Tentukan rentang θ untuk setiap basis optimal",
            explanation="Untuk basis saat ini, koefisien baris 0 (untuk parametrik tujuan) atau x_B = B⁻¹b(θ) (untuk parametrik RHS) "
            "adalah fungsi linier θ. Batas atas θ adalah nilai saat salah satunya menjadi negatif; di titik itu basis berganti.",
            table=table,
        )
    )
    xs_plot, ys_plot = [], []
    for lo, hi, status, _, z in segments:
        if status == "optimal":
            xs_plot += [float(lo), float(hi)]
            ys_plot += [float(z[0] + z[1] * lo), float(z[0] + z[1] * hi)]
    chart = Chart(
        id="parametric",
        title="Z*(θ)",
        spec=plotly_figure(
            [{"type": "scatter", "mode": "lines+markers", "x": xs_plot, "y": ys_plot, "name": "Z*(θ)"}],
            "Nilai optimal sebagai fungsi θ",
            xaxis={"title": {"text": "θ"}},
            yaxis={"title": {"text": "Z*"}},
        ),
    )
    return SolverResponse(
        result={"segments": [[str(r[0]), str(r[1]), r[2]] for r in rows]},
        steps=steps,
        tables=[table],
        charts=[chart],
        summary=summary_items([("Jumlah segmen", len(rows))]),
        conclusion=f"Terdapat {len(rows)} rentang θ dengan basis optimal berbeda.",
    )


# =========================================================================== teknik batas atas


def upper_bound(model: LPModel) -> SolverResponse:
    if model.sense != "max" or model.free or model.nonpositive:
        raise SolverError("Teknik batas atas di sini untuk maksimasi dengan variabel ≥ 0.")
    bounds: dict[str, Fraction] = {}
    regular: list[Constraint] = []
    for k in model.constraints:
        if len(k.coeffs) == 1 and k.op == "<=":
            ((v, coef),) = k.coeffs.items()
            if coef > 0:
                bounds[v] = min(bounds.get(v, k.rhs / coef), k.rhs / coef)
                continue
        if k.op != "<=" or k.rhs < 0:
            raise SolverError("Kendala fungsional harus ≤ dengan ruas kanan ≥ 0 (bentuk standar).")
        regular.append(k)
    if not bounds:
        raise SolverError("Tidak ada kendala batas atas satu variabel (mis. x1 ≤ 4) yang dapat ditangani terpisah.")
    n = len(model.variables)
    m = len(regular)
    names = list(model.variables) + [f"s{i + 1}" for i in range(m)]
    upper = [bounds.get(v) for v in model.variables] + [None] * m
    subst = [False] * (n + m)
    rows = [
        [k.coeffs.get(v, Fraction(0)) for v in model.variables] + [Fraction(int(i == j)) for j in range(m)]
        for i, k in enumerate(regular)
    ]
    rhs = [k.rhs for k in regular]
    basis = list(range(n, n + m))
    row0 = [-x for x in model.c()] + [Fraction(0)] * m
    z = Fraction(0)

    def label(j: int) -> str:
        return f"{names[j]}′" if subst[j] else names[j]

    def snap() -> Table:
        cols = ["Basis", "Z", *[label(j) for j in range(n + m)], "RHS"]
        out = [["Z", "1", *[fmt_frac(x) for x in row0], fmt_frac(z)]]
        out += [[label(basis[i]), "0", *[fmt_frac(x) for x in rows[i]], fmt_frac(rhs[i])] for i in range(m)]
        return Table(columns=cols, rows=out)

    def substitute(j: int) -> None:
        nonlocal z
        u = upper[j]
        for i in range(m):
            a = rows[i][j]
            if a:
                rhs[i] -= a * u
                rows[i][j] = -a
        z -= row0[j] * u
        row0[j] = -row0[j]
        subst[j] = not subst[j]

    def pivot(r: int, col: int) -> None:
        nonlocal z
        p = rows[r][col]
        rows[r] = [x / p for x in rows[r]]
        rhs[r] /= p
        for i in range(m):
            if i != r and rows[i][col]:
                f = rows[i][col]
                rows[i] = [a - f * b for a, b in zip(rows[i], rows[r], strict=True)]
                rhs[i] -= f * rhs[r]
        f = row0[col]
        row0[:] = [a - f * b for a, b in zip(row0, rows[r], strict=True)]
        z -= f * rhs[r]
        basis[r] = col

    steps = [
        Step(
            title="Pisahkan kendala batas atas",
            explanation="Kendala satu variabel xⱼ ≤ uⱼ tidak dimasukkan ke tabel. Bila sebuah variabel mencapai batas atasnya, "
            "variabel itu disubstitusi xⱼ = uⱼ − xⱼ′ (ditandai ′).",
            table=Table(columns=["Variabel", "Batas atas"], rows=[[v, fmt_frac(u)] for v, u in bounds.items()]),
        ),
        Step(title="Tabel awal", table=snap()),
    ]
    for it in range(1, 60):
        cand = [j for j in range(n + m) if j not in basis and row0[j] < 0]
        if not cand:
            vals = {j: Fraction(0) for j in range(n + m)}
            for i, j in enumerate(basis):
                vals[j] = rhs[i]
            x = {v: (upper[j] - vals[j]) if subst[j] else vals[j] for j, v in enumerate(model.variables)}
            zval = sum((model.objective.get(v, Fraction(0)) * x[v] for v in model.variables), Fraction(0))
            steps.append(
                Step(
                    title="Optimal",
                    explanation="Semua koefisien baris 0 ≥ 0. Variabel bertanda ′ dikembalikan: xⱼ = uⱼ − xⱼ′.",
                    table=snap(),
                )
            )
            return SolverResponse(
                result={"status": "optimal", "z": float(zval), "x": {v: float(val) for v, val in x.items()}},
                steps=steps,
                tables=[
                    NamedTable(
                        title="Solusi optimal",
                        columns=["Variabel", "Nilai", "Batas atas"],
                        rows=[[v, fmt_frac(val), fmt_frac(bounds[v]) if v in bounds else "—"] for v, val in x.items()],
                    )
                ],
                summary=summary_items(
                    [(f"{model.objective_name}*", fmt_frac(zval))] + [(v, fmt_frac(val)) for v, val in x.items()]
                ),
                conclusion=f"Solusi optimal {', '.join(f'{v} = {fmt_frac(val)}' for v, val in x.items())} dengan {model.objective_name} = {fmt_frac(zval)}.",
            )
        e = min(cand, key=lambda j: (row0[j], j))
        options = []
        for i in range(m):
            a = rows[i][e]
            if a > 0:
                options.append((rhs[i] / a, 0, i))
            elif a < 0 and upper[basis[i]] is not None:
                options.append(((upper[basis[i]] - rhs[i]) / -a, 1, i))
        if upper[e] is not None:
            options.append((upper[e], 2, -1))
        if not options:
            steps.append(Step(title="Tak terbatas", explanation=f"{label(e)} dapat naik tanpa batas."))
            return SolverResponse(
                result={"status": "unbounded"},
                steps=steps,
                conclusion="Z tak terbatas.",
                summary=summary_items([("Status", "Tak terbatas")]),
            )
        theta, kind, r = min(options, key=lambda o: (o[0], o[1]))
        if kind == 2:
            substitute(e)
            msg = f"{names[e]} mencapai batas atasnya ({fmt_frac(upper[e])}) sebelum ada variabel basis yang habis → substitusi {names[e]} = {fmt_frac(upper[e])} − {names[e]}′ tanpa pivot."
        elif kind == 1:
            b = basis[r]
            substitute(b)
            rows[r] = [-x for x in rows[r]]
            rows[r][b] = Fraction(1)
            rhs[r] = -rhs[r]
            pivot(r, e)
            msg = f"Variabel basis {names[b]} mencapai batas atasnya → substitusi {names[b]}′, lalu {label(e)} masuk menggantikannya."
        else:
            msg = f"Uji rasio biasa: {label(basis[r])} keluar, {label(e)} masuk."
            pivot(r, e)
        steps.append(
            Step(
                title=f"Iterasi {it}",
                explanation=f"Variabel masuk {names[e]}, θ = {fmt_frac(theta)}. " + msg,
                table=snap(),
            )
        )
    raise SolverError("Teknik batas atas tidak konvergen.")


# =========================================================================== titik interior (affine scaling)


def interior_point(model: LPModel, start: list[float] | None, alpha: float = 0.5, tol: float = 1e-6) -> SolverResponse:
    if (
        model.sense != "max"
        or any(k.op != "<=" or k.rhs <= 0 for k in model.constraints)
        or model.free
        or model.nonpositive
    ):
        raise SolverError("Algoritma affine scaling di sini memerlukan maksimasi dengan kendala ≤ dan ruas kanan > 0.")
    if not 0 < alpha < 1:
        raise SolverError("Parameter α harus di antara 0 dan 1.")
    n = len(model.variables)
    a = np.array([[float(x) for x in row] for row in model.a()])
    b = np.array([float(x) for x in model.b()])
    c = np.array([float(x) for x in model.c()])
    m = a.shape[0]
    A = np.hstack([a, np.eye(m)])
    C = np.concatenate([c, np.zeros(m)])
    if start:
        if len(start) != n:
            raise SolverError(f"Titik awal harus berisi {n} nilai.")
        x0 = np.array(start, dtype=float)
    else:
        pos = np.maximum(a, 0).sum(axis=1)
        t = 0.5 * float(np.min(b / np.where(pos > 0, pos, 1)))
        x0 = np.full(n, t)
    s0 = b - a @ x0
    if np.any(x0 <= 0) or np.any(s0 <= 0):
        raise SolverError("Titik awal harus berada di interior: semua variabel dan slack > 0.")
    x = np.concatenate([x0, s0])
    rows = [[0, *[round(v, 6) for v in x[:n]], round(float(C @ x), 6)]]
    for it in range(1, 501):
        D = np.diag(x)
        At = A @ D
        ct = D @ C
        P = np.eye(n + m) - At.T @ np.linalg.solve(At @ At.T, At)
        cp = P @ ct
        neg = cp[cp < 0]
        if neg.size == 0:
            if np.allclose(cp, 0, atol=1e-12):
                break
            raise SolverError("Gradien terproyeksi tidak memiliki komponen negatif: Z tak terbatas.")
        nu = float(-neg.min())
        x_new = D @ (np.ones(n + m) + alpha / nu * cp)
        rows.append([it, *[round(v, 6) for v in x_new[:n]], round(float(C @ x_new), 6)])
        if np.linalg.norm(x_new - x) < tol * max(1, np.linalg.norm(x)):
            x = x_new
            break
        x = x_new
    simplex = tableau.solve(model)
    table = NamedTable(
        title="Iterasi affine scaling",
        columns=["Iterasi", *model.variables, "Z"],
        rows=rows if len(rows) <= 40 else rows[:20] + rows[-10:],
    )
    steps = [
        Step(
            title="Bentuk augmented & titik awal interior",
            explanation="Algoritma bergerak di dalam daerah layak, bukan di titik sudut.",
            latex=r"\mathbf{x}^{(0)} = (" + ", ".join(f"{v:.4g}" for v in np.concatenate([x0, s0])) + ")",
        ),
        Step(
            title="Satu iterasi affine scaling",
            explanation=f"Skala ulang agar titik saat ini menjadi (1, …, 1), proyeksikan gradien ke ruang nol Ã, lalu melangkah sejauh α = {alpha} dari batas.",
            latex=r"\mathbf{D} = \mathrm{diag}(\mathbf{x}),\ \tilde{\mathbf{A}} = \mathbf{AD},\ \tilde{\mathbf{c}} = \mathbf{Dc},\ "
            r"\mathbf{P} = \mathbf{I} - \tilde{\mathbf{A}}^\top(\tilde{\mathbf{A}}\tilde{\mathbf{A}}^\top)^{-1}\tilde{\mathbf{A}},\ "
            r"\mathbf{c}_p = \mathbf{P}\tilde{\mathbf{c}},\ \tilde{\mathbf{x}} = \mathbf{1} + \frac{\alpha}{\nu}\mathbf{c}_p,\ \mathbf{x} = \mathbf{D}\tilde{\mathbf{x}}",
        ),
        Step(title="Iterasi", table=table),
        Step(
            title="Bandingkan dengan simpleks",
            explanation="Titik interior mendekati solusi optimal secara asimtotik; solusi simpleks berada tepat di titik sudut.",
            latex=", ".join(f"{v} \\approx {x[j]:.4f}" for j, v in enumerate(model.variables))
            + r"\quad\text{vs}\quad "
            + ", ".join(f"{v} = {latex_frac(val)}" for v, val in simplex.x.items()),
        ),
    ]
    charts = []
    if n == 2:
        path = np.array([[r[1], r[2]] for r in rows])
        charts.append(
            Chart(
                id="interior-path",
                title="Lintasan titik interior",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "lines+markers",
                            "x": path[:, 0].tolist(),
                            "y": path[:, 1].tolist(),
                            "name": "Lintasan",
                        }
                    ],
                    "Lintasan algoritma titik interior",
                    xaxis={"title": {"text": model.variables[0]}},
                    yaxis={"title": {"text": model.variables[1]}},
                ),
            )
        )
    z = float(c @ x[:n])
    return SolverResponse(
        result={"x": {v: float(x[j]) for j, v in enumerate(model.variables)}, "z": z, "iterations": len(rows) - 1},
        steps=steps,
        tables=[table],
        charts=charts,
        summary=summary_items(
            [
                ("Z (titik interior)", z),
                ("Z* (simpleks)", fmt_frac(simplex.z) if simplex.z is not None else "—"),
                ("Iterasi", len(rows) - 1),
            ]
        ),
        conclusion=f"Setelah {len(rows) - 1} iterasi, Z ≈ {z:.6g} (optimum simpleks {fmt_frac(simplex.z) if simplex.z is not None else '—'}).",
    )


# =========================================================================== goal programming

_GOAL_RE = re.compile(r"^\s*(?:P\s*(\d+))?\s*(.*?)\s*:\s*(.+)$", re.IGNORECASE)


def _parse_goals(text: str):
    goals = []
    for idx, line in enumerate(
        [ln.strip() for ln in text.split("\n") if ln.strip() and not ln.strip().startswith("#")]
    ):
        m = _GOAL_RE.match(line)
        if not m:
            raise SolverError(f"Tujuan “{line}”: gunakan format “P1, w=5: 12x1 + 9x2 >= 125”.")
        prio = int(m.group(1) or 1)
        opts = m.group(2)
        body = m.group(3)
        w = re.search(r"(?<![-+])w\s*=\s*([\d.]+)", opts)
        wm = re.search(r"w-\s*=\s*([\d.]+)", opts)
        wp = re.search(r"w\+\s*=\s*([\d.]+)", opts)
        parts = re.split(r"(<=|>=|=)", body)
        if len(parts) != 3:
            raise SolverError(f"Tujuan “{line}” harus memuat ≤, ≥, atau = dengan target di ruas kanan.")
        lhs, op, rhs = parts
        base = frac(float(w.group(1))) if w else Fraction(1)
        under = frac(float(wm.group(1))) if wm else (base if op in (">=", "=") else Fraction(0))
        over = frac(float(wp.group(1))) if wp else (base if op in ("<=", "=") else Fraction(0))
        goals.append(
            {
                "name": f"G{idx + 1}",
                "priority": prio,
                "coeffs": parse_linear(lhs, f"Tujuan {idx + 1}"),
                "target": frac(float(rhs.strip().replace(",", "."))),
                "under": under,
                "over": over,
                "op": op,
            }
        )
    if not goals:
        raise SolverError("Tuliskan minimal satu tujuan (goal).")
    return goals


def goal_programming(goals_text: str, constraints_text: str, mode: str) -> SolverResponse:
    goals = _parse_goals(goals_text)
    hard = parse_model("min Z = 0x0\n" + constraints_text).constraints if constraints_text.strip() else []
    variables = sorted({v for g in goals for v in g["coeffs"]} | {v for k in hard for v in k.coeffs} - {"x0"})
    cons = [k for k in hard]
    for g in goals:
        coeffs = dict(g["coeffs"])
        coeffs[f"{g['name']}m"] = Fraction(1)  # d⁻ (kekurangan)
        coeffs[f"{g['name']}p"] = Fraction(-1)  # d⁺ (kelebihan)
        cons.append(Constraint(coeffs, "=", g["target"], name=g["name"]))
    dev = [f"{g['name']}{s}" for g in goals for s in ("m", "p")]
    all_vars = variables + dev
    steps = [
        Step(
            title="Ubah setiap tujuan menjadi kendala dengan variabel deviasi",
            explanation="Untuk tujuan i: ekspresi + dᵢ⁻ − dᵢ⁺ = target. dᵢ⁻ = kekurangan (under), dᵢ⁺ = kelebihan (over). "
            "Hanya deviasi yang tidak diinginkan yang diberi penalti.",
            table=Table(
                columns=["Tujuan", "Prioritas", "Ekspresi", "Target", "Penalti d⁻", "Penalti d⁺"],
                rows=[
                    [
                        g["name"],
                        f"P{g['priority']}",
                        " + ".join(f"{fmt_frac(c)}{v}" for v, c in g["coeffs"].items()),
                        fmt_frac(g["target"]),
                        fmt_frac(g["under"]),
                        fmt_frac(g["over"]),
                    ]
                    for g in goals
                ],
            ),
        )
    ]

    def solve_with(obj: dict[str, Fraction], extra: list[Constraint]):
        model = LPModel("min", obj, cons + extra, all_vars)
        return tableau.solve(model, "twophase")

    def penalty(g):
        return {f"{g['name']}m": g["under"], f"{g['name']}p": g["over"]}

    level_rows = []
    if mode == "weighted":
        obj: dict[str, Fraction] = {}
        for g in goals:
            for k, v in penalty(g).items():
                if v:
                    obj[k] = obj.get(k, Fraction(0)) + v
        out = solve_with(obj, [])
        if out.status != "optimal":
            raise SolverError("Model goal programming tidak layak terhadap kendala keras.")
        steps.append(
            Step(
                title="Minimumkan total penalti berbobot",
                latex=r"\min\ \sum_i (w_i^- d_i^- + w_i^+ d_i^+) = " + latex_frac(out.z),
            )
        )
        final = out
        level_rows.append(["Semua (berbobot)", fmt_frac(out.z)])
    else:
        extra: list[Constraint] = []
        final = None
        for p in sorted({g["priority"] for g in goals}):
            obj = {}
            for g in goals:
                if g["priority"] == p:
                    for k, v in penalty(g).items():
                        if v:
                            obj[k] = obj.get(k, Fraction(0)) + v
            if not obj:
                continue
            out = solve_with(obj, extra)
            if out.status != "optimal":
                raise SolverError("Model goal programming tidak layak terhadap kendala keras.")
            steps.append(
                Step(
                    title=f"Prioritas P{p}",
                    explanation=f"Minimumkan deviasi tidak diinginkan pada prioritas P{p}, dengan hasil prioritas lebih tinggi dipertahankan sebagai kendala. "
                    f"Nilai minimum = {fmt_frac(out.z)}.",
                )
            )
            level_rows.append([f"P{p}", fmt_frac(out.z)])
            extra.append(Constraint(dict(obj), "<=", out.z, name=f"P{p} tetap"))
            final = out
    x = final.x
    goal_rows = []
    for g in goals:
        val = sum((c * x[v] for v, c in g["coeffs"].items()), Fraction(0))
        dm, dp = x[f"{g['name']}m"], x[f"{g['name']}p"]
        ok = (g["under"] == 0 or dm == 0) and (g["over"] == 0 or dp == 0)
        goal_rows.append(
            [
                g["name"],
                fmt_frac(val),
                fmt_frac(g["target"]),
                fmt_frac(dm),
                fmt_frac(dp),
                "Tercapai" if ok else "Tidak tercapai",
            ]
        )
    tables = [
        NamedTable(
            title="Nilai variabel keputusan",
            columns=["Variabel", "Nilai"],
            rows=[[v, fmt_frac(x[v])] for v in variables],
        ),
        NamedTable(
            title="Pencapaian tujuan", columns=["Tujuan", "Nilai", "Target", "d⁻", "d⁺", "Status"], rows=goal_rows
        ),
        NamedTable(title="Penalti per tingkat", columns=["Tingkat", "Penalti minimum"], rows=level_rows),
    ]
    achieved = sum(1 for r in goal_rows if r[-1] == "Tercapai")
    return SolverResponse(
        result={"x": {v: float(x[v]) for v in variables}, "achieved": achieved, "levels": level_rows},
        steps=steps,
        tables=tables,
        summary=summary_items(
            [(v, fmt_frac(x[v])) for v in variables] + [("Tujuan tercapai", f"{achieved} dari {len(goals)}")]
        ),
        conclusion=f"{achieved} dari {len(goals)} tujuan tercapai penuh. Solusi: "
        + ", ".join(f"{v} = {fmt_frac(x[v])}" for v in variables)
        + ".",
    )
