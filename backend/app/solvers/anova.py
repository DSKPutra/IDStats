"""ANOVA satu arah, dua arah (desain seimbang), dan uji lanjut Tukey HSD / Tukey–Kramer."""

from itertools import combinations

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import HypothesisTest, as_finite_array, fmt, plotly_figure, summary_items


def _groups(groups: list[tuple[str, list[float]]], min_groups: int = 2) -> list[tuple[str, np.ndarray]]:
    if len(groups) < min_groups:
        raise SolverError(f"Dibutuhkan minimal {min_groups} kelompok.")
    out = []
    for name, values in groups:
        arr = as_finite_array(values, f"Kelompok {name}")
        out.append((name, arr))
    return out


def _check_alpha(alpha: float) -> None:
    if not 0 < alpha < 1:
        raise SolverError("Taraf signifikansi α harus di antara 0 dan 1.")


def _box_chart(groups: list[tuple[str, np.ndarray]]) -> Chart:
    return Chart(
        id="groups-boxplot",
        title="Boxplot per kelompok",
        spec=plotly_figure(
            [{"type": "box", "y": g.tolist(), "name": name, "boxmean": True} for name, g in groups],
            "Sebaran data per kelompok",
            showlegend=False,
        ),
    )


def _anova_table(rows: list[list]) -> NamedTable:
    return NamedTable(
        title="Tabel ANOVA",
        columns=["Sumber variasi", "SS", "df", "MS", "F", "p-value"],
        rows=rows,
    )


def one_way(groups: list[tuple[str, list[float]]], alpha: float) -> SolverResponse:
    _check_alpha(alpha)
    gs = _groups(groups)
    k = len(gs)
    all_x = np.concatenate([g for _, g in gs])
    n = all_x.size
    if n - k < 1:
        raise SolverError("Jumlah total data harus lebih besar dari jumlah kelompok.")
    grand = float(all_x.mean())
    ns = [g.size for _, g in gs]
    means = [float(g.mean()) for _, g in gs]
    ssb = float(sum(ni * (mi - grand) ** 2 for ni, mi in zip(ns, means, strict=True)))
    ssw = float(sum(((g - g.mean()) ** 2).sum() for _, g in gs))
    sst = float(((all_x - grand) ** 2).sum())
    df_b, df_w = k - 1, n - k
    msb, msw = ssb / df_b, ssw / df_w
    if msw == 0:
        raise SolverError("Tidak ada variasi di dalam kelompok (MSW = 0); statistik F tidak terdefinisi.")
    f = msb / msw
    test = HypothesisTest(
        r"H_0: \mu_1 = \mu_2 = \dots = \mu_k",
        r"H_1: \text{minimal ada satu } \mu_i \text{ yang berbeda}",
        alpha,
        "F",
        f,
        stats.f(df_b, df_w),
        f"F dengan df = ({df_b}, {df_w})",
        "greater",
        reject_text="Terdapat perbedaan rata-rata yang signifikan antarkelompok. Lanjutkan dengan uji Tukey HSD "
        "untuk mengetahui pasangan mana yang berbeda.",
        accept_text="Tidak terdapat perbedaan rata-rata yang signifikan antarkelompok.",
    )
    table = _anova_table(
        [
            ["Antarkelompok (Between)", ssb, df_b, msb, f, test.p_value],
            ["Dalam kelompok (Within/Error)", ssw, df_w, msw, None, None],
            ["Total", sst, n - 1, None, None, None],
        ]
    )
    steps = [
        Step(
            title="Statistik tiap kelompok",
            table=Table(
                columns=["Kelompok", "n", "Rata-rata", "Varians"],
                rows=[[name, g.size, float(g.mean()), float(g.var(ddof=1)) if g.size > 1 else None] for name, g in gs],
            ),
            latex=rf"\bar{{x}} = \frac{{\sum_{{\text{{semua}}}} x}}{{N}} = {fmt(grand)},\quad N = {n},\ k = {k}",
        ),
        Step(
            title="Jumlah kuadrat (sum of squares)",
            latex=(
                rf"SSB = \sum n_i(\bar{{x}}_i - \bar{{x}})^2 = {fmt(ssb)},\quad "
                rf"SSW = \sum\sum (x_{{ij}} - \bar{{x}}_i)^2 = {fmt(ssw)},\quad SST = SSB + SSW = {fmt(sst)}"
            ),
        ),
        Step(
            title="Kuadrat tengah & statistik F",
            latex=(
                rf"MSB = \frac{{SSB}}{{k-1}} = {fmt(msb)},\quad MSW = \frac{{SSW}}{{N-k}} = {fmt(msw)},\quad "
                rf"F = \frac{{MSB}}{{MSW}} = {fmt(f)}"
            ),
            table=table,
        ),
    ]
    eta2 = ssb / sst if sst > 0 else None
    return SolverResponse(
        result={
            **test.result(),
            "ssb": ssb,
            "ssw": ssw,
            "sst": sst,
            "df_between": df_b,
            "df_within": df_w,
            "eta_squared": eta2,
        },
        steps=test.head_steps() + steps + test.tail_steps(),
        charts=[_box_chart(gs), test.chart()],
        summary=test.summary() + summary_items([("η² (ukuran efek)", eta2)]),
        tables=[table],
        conclusion=test.conclusion,
    )


def two_way(
    cells: list[tuple[str, str, list[float]]], alpha: float, factor_a: str = "Faktor A", factor_b: str = "Faktor B"
) -> SolverResponse:
    """ANOVA dua arah desain seimbang. Setiap sel (level A, level B) memiliki r ulangan yang sama.

    r = 1 → tanpa interaksi (galat = interaksi); r > 1 → dengan interaksi.
    """
    _check_alpha(alpha)
    if not cells:
        raise SolverError("Isi data per sel (level A, level B, nilai).")
    a_levels = list(dict.fromkeys(a for a, _, _ in cells))
    b_levels = list(dict.fromkeys(b for _, b, _ in cells))
    a_n, b_n = len(a_levels), len(b_levels)
    if a_n < 2 or b_n < 2:
        raise SolverError("Setiap faktor membutuhkan minimal 2 level.")
    grid: dict[tuple[str, str], np.ndarray] = {}
    for a, b, values in cells:
        if (a, b) in grid:
            raise SolverError(f"Sel ({a}, {b}) muncul lebih dari sekali.")
        grid[(a, b)] = as_finite_array(values, f"Sel ({a}, {b})")
    missing = [(a, b) for a in a_levels for b in b_levels if (a, b) not in grid]
    if missing:
        raise SolverError(f"Sel ({missing[0][0]}, {missing[0][1]}) belum diisi; desain harus lengkap.")
    reps = {v.size for v in grid.values()}
    if len(reps) != 1:
        raise SolverError("Jumlah ulangan setiap sel harus sama (desain seimbang).")
    r = reps.pop()
    y = np.array([[grid[(a, b)] for b in b_levels] for a in a_levels])  # (a, b, r)
    n = y.size
    grand = float(y.mean())
    mean_a = y.mean(axis=(1, 2))
    mean_b = y.mean(axis=(0, 2))
    mean_ab = y.mean(axis=2)
    ss_a = float(b_n * r * ((mean_a - grand) ** 2).sum())
    ss_b = float(a_n * r * ((mean_b - grand) ** 2).sum())
    sst = float(((y - grand) ** 2).sum())
    with_interaction = r > 1
    rows = []
    results: dict[str, dict] = {}
    if with_interaction:
        ss_ab = float(r * ((mean_ab - mean_a[:, None] - mean_b[None, :] + grand) ** 2).sum())
        sse = float(((y - mean_ab[:, :, None]) ** 2).sum())
        df_e = a_n * b_n * (r - 1)
        sources = [
            (factor_a, ss_a, a_n - 1),
            (factor_b, ss_b, b_n - 1),
            (f"Interaksi {factor_a} × {factor_b}", ss_ab, (a_n - 1) * (b_n - 1)),
        ]
    else:
        sse = sst - ss_a - ss_b
        df_e = (a_n - 1) * (b_n - 1)
        sources = [(factor_a, ss_a, a_n - 1), (factor_b, ss_b, b_n - 1)]
    mse = sse / df_e
    if mse <= 1e-15:
        raise SolverError("Tidak ada variasi galat (MSE = 0); statistik F tidak terdefinisi.")
    for name, ss, df in sources:
        ms = ss / df
        f = ms / mse
        p = float(stats.f.sf(f, df, df_e))
        rows.append([name, ss, df, ms, f, p])
        results[name] = {"ss": ss, "df": df, "ms": ms, "f": f, "p_value": p, "reject_h0": p < alpha}
    rows += [["Galat (Error)", sse, df_e, mse, None, None], ["Total", sst, n - 1, None, None, None]]
    table = _anova_table(rows)
    decisions = [
        f"{name}: {'signifikan' if res['reject_h0'] else 'tidak signifikan'} (p = {fmt(res['p_value'], 6)})"
        for name, res in results.items()
    ]
    steps = [
        Step(
            title="Rumuskan hipotesis",
            explanation=(
                f"Diuji {len(sources)} hipotesis: efek utama {factor_a}, efek utama {factor_b}"
                + (
                    ", dan efek interaksi."
                    if with_interaction
                    else ". Tanpa ulangan (r = 1), interaksi tidak dapat diuji."
                )
            ),
            latex=r"H_0: \alpha_i = 0,\quad H_0: \beta_j = 0"
            + (r",\quad H_0: (\alpha\beta)_{ij} = 0" if with_interaction else ""),
        ),
        Step(
            title="Rata-rata sel dan rata-rata marginal",
            table=Table(
                columns=[f"{factor_a} \\ {factor_b}", *b_levels, "Rata-rata A"],
                rows=[[a, *[float(v) for v in mean_ab[i]], float(mean_a[i])] for i, a in enumerate(a_levels)]
                + [["Rata-rata B", *[float(v) for v in mean_b], grand]],
            ),
            latex=rf"a = {a_n},\ b = {b_n},\ r = {r},\ N = {n},\ \bar{{x}} = {fmt(grand)}",
        ),
        Step(
            title="Jumlah kuadrat",
            latex=(
                rf"SS_A = br\sum(\bar{{x}}_{{i\cdot}} - \bar{{x}})^2 = {fmt(ss_a)},\quad "
                rf"SS_B = ar\sum(\bar{{x}}_{{\cdot j}} - \bar{{x}})^2 = {fmt(ss_b)}"
                + (rf",\quad SS_{{AB}} = {fmt(sources[2][1])}" if with_interaction else "")
                + rf",\quad SSE = {fmt(sse)},\quad SST = {fmt(sst)}"
            ),
        ),
        Step(title="Tabel ANOVA", explanation=f"F = MS / MSE, dengan MSE = {fmt(mse)} (df = {df_e}).", table=table),
        Step(title="Keputusan (α = " + fmt(alpha) + ")", explanation="; ".join(decisions) + "."),
    ]
    interaction_chart = Chart(
        id="interaction-plot",
        title="Plot interaksi",
        spec=plotly_figure(
            [
                {"type": "scatter", "mode": "lines+markers", "x": a_levels, "y": mean_ab[:, j].tolist(), "name": str(b)}
                for j, b in enumerate(b_levels)
            ],
            "Plot interaksi (garis sejajar = tidak ada interaksi)",
            xaxis={"title": {"text": factor_a}},
            yaxis={"title": {"text": "Rata-rata"}},
        ),
    )
    return SolverResponse(
        result={"effects": results, "sse": sse, "df_error": df_e, "mse": mse, "replicates": r},
        steps=steps,
        charts=[interaction_chart],
        tables=[table],
        summary=summary_items([(f"p-value {name}", res["p_value"]) for name, res in results.items()]),
        conclusion="; ".join(decisions) + ".",
    )


def tukey_hsd(groups: list[tuple[str, list[float]]], alpha: float) -> SolverResponse:
    _check_alpha(alpha)
    gs = _groups(groups)
    k = len(gs)
    n = sum(g.size for _, g in gs)
    df_w = n - k
    if df_w < 1:
        raise SolverError("Jumlah total data harus lebih besar dari jumlah kelompok.")
    mse = float(sum(((g - g.mean()) ** 2).sum() for _, g in gs)) / df_w
    if mse == 0:
        raise SolverError("Tidak ada variasi di dalam kelompok (MSE = 0).")
    q_crit = float(stats.studentized_range.ppf(1 - alpha, k, df_w))
    balanced = len({g.size for _, g in gs}) == 1
    rows = []
    pairs = []
    for (n1, g1), (n2, g2) in combinations(gs, 2):
        diff = float(g1.mean() - g2.mean())
        se = float(np.sqrt(mse / 2 * (1 / g1.size + 1 / g2.size)))
        q = abs(diff) / se
        hsd = q_crit * se
        p = float(stats.studentized_range.sf(q, k, df_w))
        sig = p < alpha
        rows.append([f"{n1} − {n2}", diff, hsd, diff - hsd, diff + hsd, p, "Ya" if sig else "Tidak"])
        pairs.append(
            {
                "pair": [n1, n2],
                "diff": diff,
                "hsd": hsd,
                "lower": diff - hsd,
                "upper": diff + hsd,
                "p_value": p,
                "significant": sig,
            }
        )
    table = NamedTable(
        title="Perbandingan berganda Tukey",
        columns=["Pasangan", "Selisih rata-rata", "HSD", "Batas bawah", "Batas atas", "p-value", "Berbeda nyata?"],
        rows=rows,
    )
    method = "Tukey HSD" if balanced else "Tukey–Kramer (ukuran kelompok tidak sama)"
    steps = [
        Step(
            title="Kuadrat tengah galat (MSE) dari ANOVA",
            latex=rf"MSE = \frac{{SSW}}{{N-k}} = {fmt(mse)},\quad df = {df_w},\quad k = {k}",
        ),
        Step(
            title="Nilai kritis studentized range",
            latex=rf"q_{{\alpha;\,k,\,N-k}} = q_{{{fmt(alpha)};\,{k},\,{df_w}}} = {fmt(q_crit)}",
        ),
        Step(
            title=f"Beda nyata jujur ({method})",
            explanation="Dua rata-rata berbeda nyata bila |selisih| > HSD (setara: interval tidak memuat 0).",
            latex=r"HSD_{ij} = q_{\alpha}\sqrt{\frac{MSE}{2}\left(\frac{1}{n_i}+\frac{1}{n_j}\right)}",
            table=table,
        ),
    ]
    significant = [p["pair"] for p in pairs if p["significant"]]
    conclusion = (
        "Pasangan yang berbeda nyata: " + ", ".join(f"{a} dan {b}" for a, b in significant) + "."
        if significant
        else "Tidak ada pasangan kelompok yang berbeda nyata."
    )
    ci_chart = Chart(
        id="tukey-ci",
        title="Interval kepercayaan selisih",
        spec=plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": [p["diff"] for p in pairs],
                    "y": [f"{p['pair'][0]} − {p['pair'][1]}" for p in pairs],
                    "error_x": {
                        "type": "data",
                        "array": [p["hsd"] for p in pairs],
                    },
                    "marker": {"size": 10},
                    "name": "Selisih",
                }
            ],
            f"Interval kepercayaan simultan {fmt((1 - alpha) * 100)}%",
            shapes=[{"type": "line", "x0": 0, "x1": 0, "yref": "paper", "y0": 0, "y1": 1, "line": {"dash": "dot"}}],
        ),
    )
    return SolverResponse(
        result={"q_critical": q_crit, "mse": mse, "df": df_w, "pairs": pairs},
        steps=steps,
        charts=[ci_chart, _box_chart(gs)],
        tables=[table],
        summary=summary_items(
            [("Metode", method), ("q kritis", q_crit), ("MSE", mse), ("Pasangan berbeda nyata", len(significant))]
        ),
        conclusion=conclusion,
    )
