"""Uji non-parametrik: Mann-Whitney U, Wilcoxon signed-rank, Kruskal-Wallis.

Statistik uji dan pendekatan normal dihitung manual (dengan koreksi ties).
p-value eksak dari scipy dipakai bila sampel kecil dan tanpa ties.
"""

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, SolverResponse, Step, Table
from app.solvers._base import (
    Alternative,
    HypothesisTest,
    as_finite_array,
    fmt,
    plotly_figure,
    summary_items,
)


def _check_alpha(alpha: float) -> None:
    if not 0 < alpha < 1:
        raise SolverError("Taraf signifikansi α harus di antara 0 dan 1.")


def _tie_term(ranks_source: np.ndarray) -> float:
    _, counts = np.unique(ranks_source, return_counts=True)
    return float(((counts**3) - counts).sum())


_ALT = {"two-sided": "berbeda dari", "less": "cenderung lebih kecil dari", "greater": "cenderung lebih besar dari"}


def mann_whitney(x: list[float], y: list[float], alternative: Alternative, alpha: float) -> SolverResponse:
    _check_alpha(alpha)
    a, b = as_finite_array(x, "Sampel 1"), as_finite_array(y, "Sampel 2")
    n1, n2 = a.size, b.size
    pooled = np.concatenate([a, b])
    ranks = stats.rankdata(pooled)
    r1 = float(ranks[:n1].sum())
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    n = n1 + n2
    mu = n1 * n2 / 2
    tie = _tie_term(pooled)
    sigma = np.sqrt(n1 * n2 / 12 * ((n + 1) - tie / (n * (n - 1))))
    if sigma == 0:
        raise SolverError("Semua nilai sama sehingga uji tidak dapat dihitung.")
    z = (u1 - mu) / sigma
    exact = n1 < 20 and n2 < 20 and tie == 0
    scipy_res = stats.mannwhitneyu(a, b, alternative=alternative, method="exact" if exact else "asymptotic")
    order = np.argsort(pooled, kind="stable")
    steps = [
        Step(
            title="Gabungkan & beri peringkat semua data",
            explanation="Nilai kembar (ties) diberi peringkat rata-rata.",
            table=Table(
                columns=["Nilai", "Sampel", "Peringkat"],
                rows=[[float(pooled[i]), 1 if i < n1 else 2, float(ranks[i])] for i in order],
            ),
        ),
        Step(
            title="Hitung statistik U",
            latex=(
                rf"R_1 = {fmt(r1)},\quad U_1 = R_1 - \frac{{n_1(n_1+1)}}{{2}} = {fmt(u1)},\quad "
                rf"U_2 = n_1 n_2 - U_1 = {fmt(u2)}"
            ),
        ),
        Step(
            title="Pendekatan normal (dengan koreksi ties)",
            latex=(
                rf"\mu_U = \frac{{n_1 n_2}}{{2}} = {fmt(mu)},\quad "
                rf"\sigma_U = \sqrt{{\frac{{n_1 n_2}}{{12}}\left[(n+1) - \frac{{\sum(t^3-t)}}{{n(n-1)}}\right]}} = {fmt(sigma)},\quad "
                rf"z = \frac{{U_1 - \mu_U}}{{\sigma_U}} = {fmt(z)}"
            ),
        ),
    ]
    test = HypothesisTest(
        r"H_0: \text{distribusi kedua populasi sama}",
        rf"H_1: \text{{populasi 1 {_ALT[alternative]} populasi 2}}",
        alpha,
        "z",
        float(z),
        stats.norm(),
        "normal baku (pendekatan)",
        alternative,
        reject_text=f"Terdapat cukup bukti bahwa nilai pada populasi 1 {_ALT[alternative]} populasi 2.",
        accept_text=f"Tidak terdapat cukup bukti bahwa nilai pada populasi 1 {_ALT[alternative]} populasi 2.",
    )
    warnings = []
    if exact:
        warnings.append(
            f"Sampel kecil tanpa ties: p-value eksak = {fmt(float(scipy_res.pvalue), 6)} (lebih akurat dari pendekatan normal)."
        )
    return SolverResponse(
        result={
            **test.result(),
            "u1": u1,
            "u2": u2,
            "rank_sum_1": r1,
            "z": z,
            "p_value_exact": float(scipy_res.pvalue) if exact else None,
        },
        steps=test.head_steps() + steps + test.tail_steps(),
        charts=[_box([("Sampel 1", a), ("Sampel 2", b)]), test.chart()],
        summary=summary_items([("U₁", u1), ("U₂", u2)]) + test.summary(),
        warnings=warnings,
        conclusion=test.conclusion,
    )


def wilcoxon(
    x: list[float], alternative: Alternative, alpha: float, y: list[float] | None = None, mu0: float = 0.0
) -> SolverResponse:
    _check_alpha(alpha)
    a = as_finite_array(x, "Sampel 1")
    if y is not None:
        b = as_finite_array(y, "Sampel 2")
        if a.size != b.size:
            raise SolverError(
                f"Uji Wilcoxon berpasangan membutuhkan jumlah data sama (sekarang {a.size} dan {b.size})."
            )
        d_all = a - b
        subject = "selisih (sampel 1 − sampel 2)"
    else:
        d_all = a - mu0
        subject = f"median populasi dikurangi {fmt(mu0)}"
    zero = int((d_all == 0).sum())
    d = d_all[d_all != 0]
    n = d.size
    if n < 1:
        raise SolverError("Semua selisih bernilai nol; uji Wilcoxon tidak dapat dihitung.")
    abs_rank = stats.rankdata(np.abs(d))
    w_plus = float(abs_rank[d > 0].sum())
    w_minus = float(abs_rank[d < 0].sum())
    mu = n * (n + 1) / 4
    tie = _tie_term(np.abs(d))
    sigma = np.sqrt(n * (n + 1) * (2 * n + 1) / 24 - tie / 48)
    z = (w_plus - mu) / sigma
    steps = [
        Step(
            title="Hitung selisih dan peringkat nilai mutlaknya",
            explanation=f"Selisih nol ({zero} data) dibuang. Peringkat diberi pada |d|, lalu tanda d dikembalikan.",
            table=Table(
                columns=["d", "|d|", "Peringkat |d|", "Tanda"],
                rows=[
                    [float(v), float(abs(v)), float(r), "+" if v > 0 else "−"] for v, r in zip(d, abs_rank, strict=True)
                ],
            ),
        ),
        Step(title="Jumlah peringkat bertanda", latex=rf"W^+ = {fmt(w_plus)},\quad W^- = {fmt(w_minus)},\quad n = {n}"),
        Step(
            title="Pendekatan normal (dengan koreksi ties)",
            latex=(
                rf"\mu_W = \frac{{n(n+1)}}{{4}} = {fmt(mu)},\quad \sigma_W = \sqrt{{\frac{{n(n+1)(2n+1)}}{{24}} - \frac{{\sum(t^3-t)}}{{48}}}} = {fmt(sigma)},\quad "
                rf"z = \frac{{W^+ - \mu_W}}{{\sigma_W}} = {fmt(z)}"
            ),
        ),
    ]
    test = HypothesisTest(
        r"H_0: \text{median selisih} = 0",
        {
            "two-sided": r"H_1: \text{median selisih} \neq 0",
            "less": r"H_1: \text{median selisih} < 0",
            "greater": r"H_1: \text{median selisih} > 0",
        }[alternative],
        alpha,
        "z",
        float(z),
        stats.norm(),
        "normal baku (pendekatan)",
        alternative,
        reject_text=f"Terdapat cukup bukti bahwa median {subject} {_ALT[alternative].replace('cenderung ', '')} 0.",
        accept_text=f"Tidak terdapat cukup bukti bahwa median {subject} {_ALT[alternative].replace('cenderung ', '')} 0.",
    )
    warnings = []
    if zero:
        warnings.append(f"{zero} selisih bernilai nol dibuang dari perhitungan.")
    exact_p = None
    if n <= 25 and tie == 0 and zero == 0:
        exact_p = float(stats.wilcoxon(d, alternative=alternative, method="exact").pvalue)
        warnings.append(f"Sampel kecil tanpa ties: p-value eksak = {fmt(exact_p, 6)}.")
    return SolverResponse(
        result={
            **test.result(),
            "w_plus": w_plus,
            "w_minus": w_minus,
            "n_effective": n,
            "z": z,
            "p_value_exact": exact_p,
        },
        steps=test.head_steps() + steps + test.tail_steps(),
        charts=[test.chart()],
        summary=summary_items([("W⁺", w_plus), ("W⁻", w_minus), ("n efektif", n)]) + test.summary(),
        warnings=warnings,
        conclusion=test.conclusion,
    )


def kruskal_wallis(groups: list[tuple[str, list[float]]], alpha: float) -> SolverResponse:
    _check_alpha(alpha)
    if len(groups) < 2:
        raise SolverError("Dibutuhkan minimal 2 kelompok.")
    gs = [(name, as_finite_array(v, f"Kelompok {name}")) for name, v in groups]
    pooled = np.concatenate([g for _, g in gs])
    n = pooled.size
    ranks = stats.rankdata(pooled)
    rank_sums, idx = [], 0
    for _, g in gs:
        rank_sums.append(float(ranks[idx : idx + g.size].sum()))
        idx += g.size
    h_raw = 12 / (n * (n + 1)) * sum(r * r / g.size for r, (_, g) in zip(rank_sums, gs, strict=True)) - 3 * (n + 1)
    tie = _tie_term(pooled)
    correction = 1 - tie / (n**3 - n)
    if correction == 0:
        raise SolverError("Semua nilai sama sehingga uji tidak dapat dihitung.")
    h = h_raw / correction
    df = len(gs) - 1
    steps = [
        Step(
            title="Beri peringkat seluruh data gabungan",
            table=Table(
                columns=["Kelompok", "n", "Jumlah peringkat R", "Rata-rata peringkat"],
                rows=[[name, g.size, r, r / g.size] for (name, g), r in zip(gs, rank_sums, strict=True)],
            ),
        ),
        Step(
            title="Hitung statistik H",
            latex=(
                rf"H = \frac{{12}}{{N(N+1)}}\sum\frac{{R_i^2}}{{n_i}} - 3(N+1) = {fmt(h_raw)},\quad "
                rf"H_{{koreksi}} = \frac{{H}}{{1 - \frac{{\sum(t^3-t)}}{{N^3-N}}}} = {fmt(h)}"
            ),
        ),
    ]
    test = HypothesisTest(
        r"H_0: \text{semua populasi memiliki distribusi (median) yang sama}",
        r"H_1: \text{minimal satu populasi berbeda}",
        alpha,
        "H",
        float(h),
        stats.chi2(df),
        f"chi-square dengan df = k − 1 = {df}",
        "greater",
        reject_text="Terdapat perbedaan yang signifikan antarkelompok.",
        accept_text="Tidak terdapat perbedaan yang signifikan antarkelompok.",
    )
    warnings = (
        ["Ada kelompok dengan n < 5; pendekatan chi-square kurang akurat."] if any(g.size < 5 for _, g in gs) else []
    )
    return SolverResponse(
        result={**test.result(), "h_uncorrected": h_raw, "df": df, "rank_sums": rank_sums},
        steps=test.head_steps() + steps + test.tail_steps(),
        charts=[_box(gs), test.chart()],
        summary=test.summary(),
        warnings=warnings,
        conclusion=test.conclusion,
    )


def _box(groups: list[tuple[str, np.ndarray]]) -> Chart:
    return Chart(
        id="groups-boxplot",
        title="Boxplot per kelompok",
        spec=plotly_figure(
            [{"type": "box", "y": g.tolist(), "name": name} for name, g in groups], "Sebaran data", showlegend=False
        ),
    )
