"""Korelasi (Pearson, Spearman), regresi linier sederhana & berganda, dan uji asumsi klasik."""

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import HypothesisTest, as_finite_array, fmt, hypotheses, plotly_figure, summary_items


def _check_alpha(alpha: float) -> None:
    if not 0 < alpha < 1:
        raise SolverError("Taraf signifikansi α harus di antara 0 dan 1.")


def _variables(variables: dict[str, list[float]], min_n: int) -> dict[str, np.ndarray]:
    out = {name: as_finite_array(v, f"Variabel {name}") for name, v in variables.items()}
    sizes = {v.size for v in out.values()}
    if len(sizes) != 1:
        raise SolverError("Semua variabel harus memiliki jumlah data yang sama.")
    if sizes.pop() < min_n:
        raise SolverError(f"Dibutuhkan minimal {min_n} pengamatan.")
    return out


def _rank(x: np.ndarray) -> np.ndarray:
    """Peringkat dengan rata-rata untuk nilai kembar (ties)."""
    return stats.rankdata(x)


# --------------------------------------------------------------------------- korelasi


def correlation(variables: dict[str, list[float]], method: str, alpha: float) -> SolverResponse:
    _check_alpha(alpha)
    if method not in ("pearson", "spearman"):
        raise SolverError("Metode korelasi harus 'pearson' atau 'spearman'.")
    if len(variables) < 2:
        raise SolverError("Masukkan minimal 2 variabel.")
    vs = _variables(variables, 3)
    names = list(vs)
    n = vs[names[0]].size
    label = "Pearson" if method == "pearson" else "Spearman"
    data = {k: (_rank(v) if method == "spearman" else v) for k, v in vs.items()}
    for k, v in data.items():
        if np.all(v == v[0]):
            raise SolverError(f"Variabel {k} konstan sehingga korelasi tidak terdefinisi.")
    mat = np.corrcoef(np.vstack([data[k] for k in names]))
    df = n - 2

    if len(names) == 2:
        x, y = data[names[0]], data[names[1]]
        dx, dy = x - x.mean(), y - y.mean()
        sxy, sxx, syy = float((dx * dy).sum()), float((dx**2).sum()), float((dy**2).sum())
        r = float(mat[0, 1])
        steps: list[Step] = []
        if method == "spearman":
            d = x - y
            steps.append(
                Step(
                    title="Ubah data menjadi peringkat",
                    explanation="Korelasi Spearman = korelasi Pearson terhadap peringkat (nilai kembar diberi peringkat rata-rata).",
                    table=Table(
                        columns=[names[0], names[1], f"R({names[0]})", f"R({names[1]})", "d²"],
                        rows=[
                            [float(a), float(b), float(p), float(q), float(e * e)]
                            for a, b, p, q, e in zip(vs[names[0]], vs[names[1]], x, y, d, strict=True)
                        ],
                    ),
                    latex=(
                        rf"\text{{Tanpa ties: }} r_s = 1 - \frac{{6\sum d^2}}{{n(n^2-1)}} = "
                        rf"1 - \frac{{6\cdot {fmt(float((d**2).sum()))}}}{{{n}({n}^2-1)}} = {fmt(1 - 6 * float((d**2).sum()) / (n * (n * n - 1)))}"
                    ),
                )
            )
        steps.append(
            Step(
                title=f"Koefisien korelasi {label}",
                latex=(
                    rf"r = \frac{{\sum (x-\bar{{x}})(y-\bar{{y}})}}{{\sqrt{{\sum (x-\bar{{x}})^2 \sum (y-\bar{{y}})^2}}}} = "
                    rf"\frac{{{fmt(sxy)}}}{{\sqrt{{{fmt(sxx)} \cdot {fmt(syy)}}}}} = {fmt(r)}"
                ),
            )
        )
        if abs(r) >= 1 - 1e-12:
            return SolverResponse(
                result={"r": r, "n": n},
                steps=steps,
                summary=summary_items([(f"r ({label})", r), ("n", n)]),
                conclusion="Korelasi sempurna: semua titik tepat berada pada satu garis (monoton).",
            )
        t = r * np.sqrt(df / (1 - r * r))
        steps.append(
            Step(
                title="Statistik uji signifikansi korelasi",
                latex=rf"t = r\sqrt{{\frac{{n-2}}{{1-r^2}}}} = {fmt(r)}\sqrt{{\frac{{{df}}}{{1-{fmt(r)}^2}}}} = {fmt(t)}",
            )
        )
        h0, h1 = hypotheses(r"\rho", "0", "two-sided")
        test = HypothesisTest(
            h0,
            h1,
            alpha,
            "t",
            float(t),
            stats.t(df),
            f"t dengan df = n − 2 = {df}",
            "two-sided",
            reject_text=f"Terdapat korelasi yang signifikan antara {names[0]} dan {names[1]} ({_strength(r)}).",
            accept_text=f"Tidak terdapat korelasi yang signifikan antara {names[0]} dan {names[1]}.",
        )
        scatter = Chart(
            id="scatter",
            title="Diagram pencar",
            spec=plotly_figure(
                [
                    {
                        "type": "scatter",
                        "mode": "markers",
                        "x": vs[names[0]].tolist(),
                        "y": vs[names[1]].tolist(),
                        "name": "Data",
                    }
                ],
                f"{names[1]} vs {names[0]}",
                xaxis={"title": {"text": names[0]}},
                yaxis={"title": {"text": names[1]}},
            ),
        )
        return SolverResponse(
            result={**test.result(), "r": r, "r_squared": r * r, "n": n, "df": df},
            steps=test.head_steps() + steps + test.tail_steps(),
            charts=[scatter, test.chart()],
            summary=summary_items([(f"r ({label})", r), ("r²", r * r), ("Kekuatan", _strength(r))]) + test.summary(),
            conclusion=test.conclusion,
        )

    # matriks korelasi untuk > 2 variabel
    p_mat = np.ones_like(mat)
    for i in range(len(names)):
        for j in range(len(names)):
            if i != j and abs(mat[i, j]) < 1:
                t = mat[i, j] * np.sqrt(df / (1 - mat[i, j] ** 2))
                p_mat[i, j] = 2 * stats.t.sf(abs(t), df)
            elif i != j:
                p_mat[i, j] = 0.0
    table = NamedTable(
        title=f"Matriks korelasi {label}",
        columns=["", *names],
        rows=[[a, *[float(v) for v in mat[i]]] for i, a in enumerate(names)],
    )
    p_table = NamedTable(
        title="Matriks p-value",
        columns=["", *names],
        rows=[[a, *[float(v) for v in p_mat[i]]] for i, a in enumerate(names)],
    )
    heat = Chart(
        id="correlation-heatmap",
        title="Heatmap korelasi",
        spec=plotly_figure(
            [
                {
                    "type": "heatmap",
                    "z": mat.round(4).tolist(),
                    "x": names,
                    "y": names,
                    "zmin": -1,
                    "zmax": 1,
                    "colorscale": "RdBu",
                    "texttemplate": "%{z:.2f}",
                }
            ],
            f"Matriks korelasi {label}",
            yaxis={"autorange": "reversed"},
        ),
    )
    return SolverResponse(
        result={"matrix": mat.tolist(), "p_values": p_mat.tolist(), "names": names, "n": n},
        steps=[
            Step(title=f"Hitung korelasi {label} setiap pasangan variabel", table=table),
            Step(
                title="Uji signifikansi setiap pasangan",
                latex=rf"t = r\sqrt{{\frac{{n-2}}{{1-r^2}}}},\quad df = {df}",
                table=p_table,
            ),
        ],
        charts=[heat],
        tables=[table, p_table],
        summary=summary_items([("Jumlah variabel", len(names)), ("n", n)]),
    )


def _strength(r: float) -> str:
    a = abs(r)
    level = (
        "sangat lemah"
        if a < 0.2
        else "lemah"
        if a < 0.4
        else "sedang"
        if a < 0.6
        else "kuat"
        if a < 0.8
        else "sangat kuat"
    )
    return f"{level}, {'positif' if r > 0 else 'negatif'}"


# --------------------------------------------------------------------------- regresi (OLS)


def _ols(y: np.ndarray, x_cols: list[np.ndarray]) -> dict:
    n = y.size
    X = np.column_stack([np.ones(n), *x_cols])
    xtx = X.T @ X
    if np.linalg.matrix_rank(xtx) < xtx.shape[0]:
        raise SolverError(
            "Matriks XᵀX singular: ada variabel bebas yang konstan atau merupakan kombinasi linier variabel lain "
            "(multikolinearitas sempurna)."
        )
    xtx_inv = np.linalg.inv(xtx)
    beta = xtx_inv @ X.T @ y
    fitted = X @ beta
    resid = y - fitted
    p = X.shape[1] - 1
    df_e = n - p - 1
    sse = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    ssr = sst - sse
    mse = sse / df_e if df_e > 0 else float("nan")
    return {
        "X": X,
        "xtx": xtx,
        "xtx_inv": xtx_inv,
        "beta": beta,
        "fitted": fitted,
        "resid": resid,
        "p": p,
        "n": n,
        "df_e": df_e,
        "sse": sse,
        "sst": sst,
        "ssr": ssr,
        "mse": mse,
        "r2": ssr / sst if sst > 0 else float("nan"),
    }


def _regression_response(
    y_name: str,
    x_names: list[str],
    y: np.ndarray,
    xs: list[np.ndarray],
    alpha: float,
    predict: list[list[float]] | None,
    simple: bool,
) -> SolverResponse:
    _check_alpha(alpha)
    fit = _ols(y, xs)
    n, p, df_e = fit["n"], fit["p"], fit["df_e"]
    if df_e < 1:
        raise SolverError(f"Jumlah pengamatan ({n}) harus lebih besar dari jumlah parameter ({p + 1}).")
    beta, mse = fit["beta"], fit["mse"]
    se_beta = np.sqrt(np.diag(fit["xtx_inv"]) * mse)
    t_vals = beta / se_beta
    p_vals = 2 * stats.t.sf(np.abs(t_vals), df_e)
    t_crit = float(stats.t.ppf(1 - alpha / 2, df_e))
    r2 = fit["r2"]
    adj_r2 = 1 - (1 - r2) * (n - 1) / df_e
    msr = fit["ssr"] / p
    f = msr / mse if mse > 0 else float("inf")
    f_p = float(stats.f.sf(f, p, df_e)) if np.isfinite(f) else 0.0
    terms = ["Konstanta (b₀)", *[f"{name} (b{i + 1})" for i, name in enumerate(x_names)]]
    coef_table = NamedTable(
        title="Koefisien regresi",
        columns=["Variabel", "Koefisien", "Galat baku", "t", "p-value", "Batas bawah", "Batas atas"],
        rows=[
            [
                terms[i],
                float(beta[i]),
                float(se_beta[i]),
                float(t_vals[i]),
                float(p_vals[i]),
                float(beta[i] - t_crit * se_beta[i]),
                float(beta[i] + t_crit * se_beta[i]),
            ]
            for i in range(p + 1)
        ],
    )
    anova_table = NamedTable(
        title="Tabel ANOVA regresi",
        columns=["Sumber", "SS", "df", "MS", "F", "p-value"],
        rows=[
            ["Regresi", fit["ssr"], p, msr, f, f_p],
            ["Residual", fit["sse"], df_e, mse, None, None],
            ["Total", fit["sst"], n - 1, None, None, None],
        ],
    )
    equation = rf"\hat{{y}} = {fmt(beta[0])}" + "".join(
        rf" {'+' if b >= 0 else '-'} {fmt(abs(b))}\,\text{{{name}}}" for b, name in zip(beta[1:], x_names, strict=True)
    )
    steps: list[Step] = []
    if simple:
        x = xs[0]
        dx, dy = x - x.mean(), y - y.mean()
        sxx, sxy = float((dx**2).sum()), float((dx * dy).sum())
        steps += [
            Step(
                title="Hitung rata-rata dan jumlah kuadrat",
                latex=(
                    rf"\bar{{x}} = {fmt(x.mean())},\ \bar{{y}} = {fmt(y.mean())},\quad "
                    rf"S_{{xx}} = \sum(x-\bar{{x}})^2 = {fmt(sxx)},\quad S_{{xy}} = \sum(x-\bar{{x}})(y-\bar{{y}}) = {fmt(sxy)}"
                ),
            ),
            Step(
                title="Koefisien metode kuadrat terkecil (least squares)",
                latex=(
                    rf"b_1 = \frac{{S_{{xy}}}}{{S_{{xx}}}} = \frac{{{fmt(sxy)}}}{{{fmt(sxx)}}} = {fmt(beta[1])},\quad "
                    rf"b_0 = \bar{{y}} - b_1\bar{{x}} = {fmt(y.mean())} - {fmt(beta[1])}\cdot{fmt(x.mean())} = {fmt(beta[0])}"
                ),
            ),
        ]
    else:
        steps += [
            Step(
                title="Susun matriks desain X dan hitung XᵀX",
                explanation="Kolom pertama X berisi 1 untuk konstanta. Koefisien diperoleh dari persamaan normal.",
                latex=r"\mathbf{b} = (\mathbf{X}^\top\mathbf{X})^{-1}\mathbf{X}^\top\mathbf{y}",
                matrix=fit["xtx"].round(6).tolist(),
            ),
            Step(title="Invers (XᵀX)⁻¹", matrix=fit["xtx_inv"].round(8).tolist()),
            Step(title="Vektor koefisien b", matrix=[[float(b)] for b in beta]),
        ]
    steps += [
        Step(title="Persamaan regresi", latex=equation),
        Step(
            title="Koefisien determinasi",
            explanation="R² = proporsi variasi y yang dijelaskan model.",
            latex=(
                rf"R^2 = \frac{{SSR}}{{SST}} = \frac{{{fmt(fit['ssr'])}}}{{{fmt(fit['sst'])}}} = {fmt(r2)},\quad "
                rf"R^2_{{adj}} = 1 - (1-R^2)\frac{{n-1}}{{n-p-1}} = {fmt(adj_r2)}"
            ),
        ),
        Step(
            title="Uji F (signifikansi model secara simultan)",
            latex=rf"F = \frac{{MSR}}{{MSE}} = \frac{{{fmt(msr)}}}{{{fmt(mse)}}} = {fmt(f)},\quad p = {fmt(f_p, 6)}",
            table=anova_table,
        ),
        Step(
            title="Uji t (signifikansi tiap koefisien)",
            latex=rf"t_j = \frac{{b_j}}{{SE(b_j)}},\quad df = n - p - 1 = {df_e},\quad t_{{\alpha/2}} = {fmt(t_crit)}",
            table=coef_table,
        ),
    ]
    tables = [coef_table, anova_table]
    result: dict = {
        "coefficients": beta.tolist(),
        "standard_errors": se_beta.tolist(),
        "t_values": t_vals.tolist(),
        "p_values": p_vals.tolist(),
        "r_squared": r2,
        "adj_r_squared": adj_r2,
        "f": f,
        "f_p_value": f_p,
        "mse": mse,
        "df_residual": df_e,
        "residuals": fit["resid"].tolist(),
        "fitted": fit["fitted"].tolist(),
    }
    if predict:
        pred_rows = []
        for row in predict:
            if len(row) != p:
                raise SolverError(f"Setiap baris prediksi harus berisi {p} nilai ({', '.join(x_names)}).")
            x0 = np.array([1.0, *row])
            y0 = float(x0 @ beta)
            h = float(x0 @ fit["xtx_inv"] @ x0)
            ci = t_crit * np.sqrt(mse * h)
            pi = t_crit * np.sqrt(mse * (1 + h))
            pred_rows.append([*row, y0, y0 - ci, y0 + ci, y0 - pi, y0 + pi])
        pred_table = NamedTable(
            title="Prediksi",
            columns=[*x_names, "ŷ", "CI rata-rata bawah", "CI rata-rata atas", "PI individu bawah", "PI individu atas"],
            rows=pred_rows,
        )
        steps.append(
            Step(
                title="Prediksi dengan interval",
                explanation="Interval kepercayaan (CI) untuk rata-rata y; interval prediksi (PI) untuk satu pengamatan baru.",
                latex=r"\hat{y}_0 \pm t_{\alpha/2}\sqrt{MSE\,\mathbf{x}_0^\top(\mathbf{X}^\top\mathbf{X})^{-1}\mathbf{x}_0}\ \ (\text{CI}),\qquad "
                r"\hat{y}_0 \pm t_{\alpha/2}\sqrt{MSE\,(1+\mathbf{x}_0^\top(\mathbf{X}^\top\mathbf{X})^{-1}\mathbf{x}_0)}\ \ (\text{PI})",
                table=pred_table,
            )
        )
        tables.append(pred_table)
        result["predictions"] = pred_rows

    charts = []
    if simple:
        x = xs[0]
        grid = np.linspace(float(x.min()), float(x.max()), 50)
        charts.append(
            Chart(
                id="fit",
                title="Garis regresi",
                spec=plotly_figure(
                    [
                        {"type": "scatter", "mode": "markers", "x": x.tolist(), "y": y.tolist(), "name": "Data"},
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "x": grid.tolist(),
                            "y": (beta[0] + beta[1] * grid).tolist(),
                            "name": "ŷ",
                        },
                    ],
                    "Diagram pencar & garis regresi",
                    xaxis={"title": {"text": x_names[0]}},
                    yaxis={"title": {"text": y_name}},
                ),
            )
        )
    charts.append(
        Chart(
            id="residuals",
            title="Plot residual",
            spec=plotly_figure(
                [
                    {
                        "type": "scatter",
                        "mode": "markers",
                        "x": fit["fitted"].tolist(),
                        "y": fit["resid"].tolist(),
                        "name": "Residual",
                    }
                ],
                "Residual vs nilai prediksi (pola acak = baik)",
                xaxis={"title": {"text": "ŷ"}},
                yaxis={"title": {"text": "Residual"}, "zeroline": True},
            ),
        )
    )
    sig_terms = [terms[i] for i in range(1, p + 1) if p_vals[i] < alpha]
    conclusion = (
        f"Model {'signifikan' if f_p < alpha else 'tidak signifikan'} secara simultan (F = {fmt(f)}, p = {fmt(f_p, 6)}) "
        f"dan menjelaskan {fmt(r2 * 100, 2)}% variasi {y_name}. "
        + (
            f"Variabel yang signifikan: {', '.join(sig_terms)}."
            if sig_terms
            else "Tidak ada variabel bebas yang signifikan secara parsial."
        )
    )
    return SolverResponse(
        result=result,
        steps=steps,
        charts=charts,
        tables=tables,
        summary=summary_items(
            [("Persamaan", equation), ("R²", r2), ("R² disesuaikan", adj_r2), ("F", f), ("p-value (F)", f_p), ("n", n)]
        ),
        conclusion=conclusion,
    )


def simple(
    x: list[float],
    y: list[float],
    alpha: float,
    x_name: str = "x",
    y_name: str = "y",
    predict: list[float] | None = None,
) -> SolverResponse:
    vs = _variables({"x": x, "y": y}, 3)
    return _regression_response(
        y_name, [x_name], vs["y"], [vs["x"]], alpha, [[v] for v in predict] if predict else None, simple=True
    )


def multiple(
    y: list[float],
    predictors: dict[str, list[float]],
    alpha: float,
    y_name: str = "y",
    predict: list[list[float]] | None = None,
) -> SolverResponse:
    if not predictors:
        raise SolverError("Masukkan minimal satu variabel bebas.")
    if y_name in predictors:
        raise SolverError("Nama variabel terikat tidak boleh sama dengan variabel bebas.")
    vs = _variables({y_name: y, **predictors}, len(predictors) + 2)
    names = list(predictors)
    return _regression_response(
        y_name, names, vs[y_name], [vs[k] for k in names], alpha, predict, simple=len(names) == 1
    )


def assumptions(y: list[float], predictors: dict[str, list[float]], alpha: float, y_name: str = "y") -> SolverResponse:
    _check_alpha(alpha)
    if not predictors:
        raise SolverError("Masukkan minimal satu variabel bebas.")
    vs = _variables({y_name: y, **predictors}, len(predictors) + 3)
    names = list(predictors)
    yv, xs = vs[y_name], [vs[k] for k in names]
    fit = _ols(yv, xs)
    e, n = fit["resid"], fit["n"]
    rows: list[list] = []
    steps: list[Step] = []
    warnings: list[str] = []

    # 1. Normalitas residual (Shapiro-Wilk)
    if n >= 3:
        w, p_sw = stats.shapiro(e)
        ok = p_sw >= alpha
        rows.append(
            ["Normalitas residual", "Shapiro-Wilk", float(w), float(p_sw), "Terpenuhi" if ok else "Tidak terpenuhi"]
        )
        steps.append(
            Step(
                title="Normalitas residual (Shapiro-Wilk)",
                explanation="H₀: residual berdistribusi normal. p-value ≥ α berarti asumsi normalitas terpenuhi.",
                latex=rf"W = {fmt(float(w))},\quad p = {fmt(float(p_sw), 6)}",
            )
        )

    # 2. Homoskedastisitas (Breusch–Pagan, versi Koenker: LM = n·R² dari regresi e² terhadap X)
    e2 = e**2
    aux = _ols(e2, xs)
    lm = n * aux["r2"] if np.isfinite(aux["r2"]) else 0.0
    p_bp = float(stats.chi2.sf(lm, len(names)))
    ok = p_bp >= alpha
    rows.append(["Homoskedastisitas", "Breusch–Pagan", float(lm), p_bp, "Terpenuhi" if ok else "Tidak terpenuhi"])
    steps.append(
        Step(
            title="Homoskedastisitas (Breusch–Pagan)",
            explanation="Regresikan kuadrat residual e² terhadap variabel bebas. H₀: varians residual konstan.",
            latex=rf"LM = n R^2_{{aux}} = {n}\cdot{fmt(aux['r2'])} = {fmt(lm)} \sim \chi^2_{{{len(names)}}},\quad p = {fmt(p_bp, 6)}",
        )
    )

    # 3. Autokorelasi (Durbin–Watson)
    dw = float((np.diff(e) ** 2).sum() / (e @ e)) if e @ e > 0 else float("nan")
    dw_ok = 1.5 <= dw <= 2.5
    rows.append(["Tidak ada autokorelasi", "Durbin–Watson", dw, None, "Terpenuhi (≈2)" if dw_ok else "Perlu diperiksa"])
    steps.append(
        Step(
            title="Autokorelasi (Durbin–Watson)",
            explanation="Nilai mendekati 2 berarti tidak ada autokorelasi; < 1,5 indikasi autokorelasi positif, > 2,5 negatif "
            "(aturan praktis; untuk keputusan formal bandingkan dengan tabel dL/dU).",
            latex=rf"DW = \frac{{\sum_{{t=2}}^n (e_t - e_{{t-1}})^2}}{{\sum e_t^2}} = {fmt(dw)}",
        )
    )

    # 4. Multikolinearitas (VIF)
    vif_rows = []
    if len(names) >= 2:
        for i, name in enumerate(names):
            others = [xs[j] for j in range(len(names)) if j != i]
            r2_i = _ols(xs[i], others)["r2"]
            vif = 1 / (1 - r2_i) if r2_i < 1 else float("inf")
            vif_rows.append([name, float(r2_i), vif, "Aman" if vif < 10 else "Multikolinearitas"])
            rows.append(
                [f"Multikolinearitas: {name}", "VIF", vif, None, "Terpenuhi" if vif < 10 else "Tidak terpenuhi"]
            )
        steps.append(
            Step(
                title="Multikolinearitas (VIF)",
                explanation="Regresikan setiap variabel bebas terhadap variabel bebas lainnya. VIF ≥ 10 menandakan multikolinearitas serius.",
                latex=r"VIF_j = \frac{1}{1 - R_j^2}",
                table=Table(columns=["Variabel", "R²ⱼ", "VIF", "Keterangan"], rows=vif_rows),
            )
        )
    else:
        warnings.append("VIF hanya relevan untuk regresi dengan ≥ 2 variabel bebas.")

    table = NamedTable(
        title="Ringkasan uji asumsi klasik", columns=["Asumsi", "Uji", "Statistik", "p-value", "Hasil"], rows=rows
    )
    failed = [r[0] for r in rows if r[4].startswith("Tidak")]
    (osm, osr), (slope, intercept, _) = stats.probplot(e, dist="norm")
    return SolverResponse(
        result={"tests": rows, "durbin_watson": dw, "breusch_pagan": {"lm": lm, "p_value": p_bp}, "vif": vif_rows},
        steps=steps,
        tables=[table],
        charts=[
            Chart(
                id="residual-qq",
                title="Q-Q plot residual",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "markers",
                            "x": osm.tolist(),
                            "y": osr.tolist(),
                            "name": "Residual",
                        },
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "x": [float(osm[0]), float(osm[-1])],
                            "y": [float(intercept + slope * osm[0]), float(intercept + slope * osm[-1])],
                            "name": "Garis normal",
                        },
                    ],
                    "Q-Q plot residual",
                ),
            ),
            Chart(
                id="residuals",
                title="Plot residual",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "markers",
                            "x": fit["fitted"].tolist(),
                            "y": e.tolist(),
                            "name": "Residual",
                        }
                    ],
                    "Residual vs ŷ",
                ),
            ),
        ],
        warnings=warnings,
        conclusion="Semua asumsi klasik terpenuhi."
        if not failed
        else "Asumsi yang tidak terpenuhi: " + ", ".join(failed) + ".",
    )
