"""Statistik inferensial: interval kepercayaan, uji z/t, uji proporsi, chi-square, uji F."""

from dataclasses import dataclass

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, SolverResponse, Step, Table
from app.solvers._base import (
    Alternative,
    HypothesisTest,
    as_finite_array,
    fmt,
    hypotheses,
    plotly_figure,
    summary_items,
)


@dataclass
class SampleStats:
    n: int
    mean: float
    sd: float | None


def sample_stats(
    data: list[float] | None, n: int | None = None, mean: float | None = None, sd: float | None = None
) -> tuple[SampleStats, Step]:
    """Ambil n, x̄, s dari data mentah atau dari ringkasan yang diketik pengguna."""
    if data is not None:
        x = as_finite_array(data)
        if x.size < 2:
            raise SolverError("Sampel membutuhkan minimal 2 data.")
        s = SampleStats(int(x.size), float(x.mean()), float(x.std(ddof=1)))
        return s, Step(
            title="Hitung statistik sampel",
            explanation="Rata-rata dan simpangan baku sampel dihitung dari data.",
            latex=(
                rf"n = {s.n},\quad \bar{{x}} = \frac{{\sum x_i}}{{n}} = {fmt(s.mean)},\quad "
                rf"s = \sqrt{{\frac{{\sum (x_i-\bar{{x}})^2}}{{n-1}}}} = {fmt(s.sd)}"
            ),
        )
    if n is None or mean is None:
        raise SolverError("Isi data sampel, atau isi ringkasan n dan rata-rata.")
    if n < 2:
        raise SolverError("Ukuran sampel n minimal 2.")
    if sd is not None and sd <= 0:
        raise SolverError("Simpangan baku harus lebih besar dari 0.")
    s = SampleStats(int(n), float(mean), None if sd is None else float(sd))
    return s, Step(
        title="Statistik sampel (diketahui)",
        explanation="Ringkasan sampel diambil langsung dari soal.",
        latex=rf"n = {s.n},\quad \bar{{x}} = {fmt(s.mean)}" + (rf",\quad s = {fmt(s.sd)}" if s.sd is not None else ""),
    )


def _check_alpha(alpha: float) -> None:
    if not 0 < alpha < 1:
        raise SolverError("Taraf signifikansi α harus di antara 0 dan 1.")


def _response(test: HypothesisTest, steps: list[Step], extra: dict | None = None, **kw) -> SolverResponse:
    return SolverResponse(
        result={**test.result(), **(extra or {})},
        steps=test.head_steps() + steps + test.tail_steps(),
        charts=[test.chart(), *kw.pop("charts", [])],
        summary=kw.pop("summary_prefix", []) + test.summary(),
        conclusion=test.conclusion,
        **kw,
    )


# --------------------------------------------------------------------------- interval kepercayaan


def confidence_interval(
    kind: str,
    confidence: float,
    data: list[float] | None = None,
    n: int | None = None,
    mean: float | None = None,
    sd: float | None = None,
    sigma: float | None = None,
    successes: int | None = None,
) -> SolverResponse:
    if not 0 < confidence < 1:
        raise SolverError("Tingkat kepercayaan harus di antara 0 dan 1 (mis. 0.95).")
    alpha = 1 - confidence
    steps: list[Step] = []
    warnings: list[str] = []

    if kind == "proportion":
        if successes is None or n is None:
            raise SolverError("Isi jumlah sukses (x) dan ukuran sampel (n).")
        if n <= 0 or not 0 <= successes <= n:
            raise SolverError("Jumlah sukses harus di antara 0 dan n.")
        p_hat = successes / n
        z = float(stats.norm.ppf(1 - alpha / 2))
        se = float(np.sqrt(p_hat * (1 - p_hat) / n))
        lo, hi = p_hat - z * se, p_hat + z * se
        if n * p_hat < 5 or n * (1 - p_hat) < 5:
            warnings.append("n·p̂ atau n·(1−p̂) < 5: pendekatan normal kurang akurat.")
        steps += [
            Step(
                title="Proporsi sampel",
                latex=rf"\hat{{p}} = \frac{{x}}{{n}} = \frac{{{successes}}}{{{n}}} = {fmt(p_hat)}",
            ),
            Step(
                title="Nilai kritis z",
                explanation=f"Untuk tingkat kepercayaan {fmt(confidence * 100)}%, α/2 = {fmt(alpha / 2)}.",
                latex=rf"z_{{\alpha/2}} = z_{{{fmt(alpha / 2)}}} = {fmt(z)}",
            ),
            Step(
                title="Galat baku & interval",
                latex=(
                    rf"SE = \sqrt{{\frac{{\hat{{p}}(1-\hat{{p}})}}{{n}}}} = {fmt(se)},\quad "
                    rf"\hat{{p}} \pm z_{{\alpha/2}} SE = {fmt(p_hat)} \pm {fmt(z * se)} = [{fmt(lo)},\ {fmt(hi)}]"
                ),
            ),
        ]
        estimate, param = p_hat, "p"
    else:
        s, step = sample_stats(data, n, mean, sd)
        steps.append(step)
        if kind == "mean_z":
            if sigma is None or sigma <= 0:
                raise SolverError("Interval-z membutuhkan simpangan baku populasi σ yang diketahui (> 0).")
            crit = float(stats.norm.ppf(1 - alpha / 2))
            se = sigma / np.sqrt(s.n)
            crit_latex, se_latex = (
                rf"z_{{\alpha/2}} = {fmt(crit)}",
                rf"\frac{{\sigma}}{{\sqrt{{n}}}} = \frac{{{fmt(sigma)}}}{{\sqrt{{{s.n}}}}}",
            )
            estimate, param = s.mean, r"\mu"
        elif kind == "mean_t":
            if s.sd is None:
                raise SolverError("Interval-t membutuhkan simpangan baku sampel s.")
            df = s.n - 1
            crit = float(stats.t.ppf(1 - alpha / 2, df))
            se = s.sd / np.sqrt(s.n)
            crit_latex = rf"t_{{\alpha/2,\,{df}}} = {fmt(crit)}"
            se_latex = rf"\frac{{s}}{{\sqrt{{n}}}} = \frac{{{fmt(s.sd)}}}{{\sqrt{{{s.n}}}}}"
            estimate, param = s.mean, r"\mu"
        elif kind == "variance":
            if s.sd is None:
                raise SolverError("Interval varians membutuhkan simpangan baku sampel s.")
            df = s.n - 1
            var = s.sd**2
            chi_hi = float(stats.chi2.ppf(1 - alpha / 2, df))
            chi_lo = float(stats.chi2.ppf(alpha / 2, df))
            lo, hi = df * var / chi_hi, df * var / chi_lo
            steps += [
                Step(
                    title="Nilai kritis chi-square",
                    latex=rf"\chi^2_{{\alpha/2,\,{df}}} = {fmt(chi_hi)},\quad \chi^2_{{1-\alpha/2,\,{df}}} = {fmt(chi_lo)}",
                ),
                Step(
                    title="Interval kepercayaan varians",
                    explanation="Distribusi chi-square tidak simetris, sehingga interval tidak simetris terhadap s².",
                    latex=(
                        rf"\left[\frac{{(n-1)s^2}}{{\chi^2_{{\alpha/2}}}},\ \frac{{(n-1)s^2}}{{\chi^2_{{1-\alpha/2}}}}\right]"
                        rf" = \left[\frac{{{df}\cdot{fmt(var)}}}{{{fmt(chi_hi)}}},\ \frac{{{df}\cdot{fmt(var)}}}{{{fmt(chi_lo)}}}\right]"
                        rf" = [{fmt(lo)},\ {fmt(hi)}]"
                    ),
                ),
            ]
            estimate, param = var, r"\sigma^2"
        else:
            raise SolverError("Jenis interval tidak dikenal.")
        if kind in ("mean_z", "mean_t"):
            margin = crit * se
            lo, hi = s.mean - margin, s.mean + margin
            steps += [
                Step(title="Nilai kritis", latex=crit_latex),
                Step(title="Galat baku (standard error)", latex=rf"SE = {se_latex} = {fmt(se)}"),
                Step(
                    title="Margin galat & interval",
                    latex=rf"\bar{{x}} \pm E = {fmt(s.mean)} \pm {fmt(margin)} = [{fmt(lo)},\ {fmt(hi)}]",
                ),
            ]

    pct = fmt(confidence * 100)
    conclusion = (
        f"Dengan tingkat kepercayaan {pct}%, parameter populasi diperkirakan berada di antara {fmt(lo)} dan {fmt(hi)}."
    )
    return SolverResponse(
        result={"estimate": estimate, "lower": lo, "upper": hi, "confidence": confidence},
        steps=steps,
        summary=summary_items(
            [("Estimasi titik", estimate), ("Batas bawah", lo), ("Batas atas", hi), ("Tingkat kepercayaan", f"{pct}%")]
        ),
        conclusion=conclusion,
        warnings=warnings,
        charts=[
            Chart(
                id="interval",
                title="Interval kepercayaan",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "markers",
                            "x": [estimate],
                            "y": [f"${param}$"],
                            "error_x": {
                                "type": "data",
                                "symmetric": False,
                                "array": [hi - estimate],
                                "arrayminus": [estimate - lo],
                            },
                            "marker": {"size": 12},
                            "name": "Estimasi",
                        }
                    ],
                    f"Interval kepercayaan {pct}%",
                    height=260,
                ),
            )
        ],
    )


# --------------------------------------------------------------------------- uji rata-rata


def z_test(
    mu0: float,
    sigma: float,
    alternative: Alternative,
    alpha: float,
    data: list[float] | None = None,
    n: int | None = None,
    mean: float | None = None,
) -> SolverResponse:
    _check_alpha(alpha)
    if sigma <= 0:
        raise SolverError("Simpangan baku populasi σ harus lebih besar dari 0.")
    s, step = sample_stats(data, n, mean)
    se = sigma / np.sqrt(s.n)
    z = (s.mean - mu0) / se
    h0, h1 = hypotheses(r"\mu", fmt(mu0), alternative)
    test = HypothesisTest(
        h0,
        h1,
        alpha,
        "z",
        float(z),
        stats.norm(),
        "normal baku N(0, 1)",
        alternative,
        reject_text=f"Terdapat cukup bukti bahwa rata-rata populasi {_alt_text(alternative)} {fmt(mu0)}.",
        accept_text=f"Tidak terdapat cukup bukti bahwa rata-rata populasi {_alt_text(alternative)} {fmt(mu0)}.",
    )
    steps = [
        step,
        Step(
            title="Hitung statistik uji z",
            explanation="σ populasi diketahui, sehingga digunakan uji-z.",
            latex=(
                rf"z = \frac{{\bar{{x}} - \mu_0}}{{\sigma/\sqrt{{n}}}} = "
                rf"\frac{{{fmt(s.mean)} - {fmt(mu0)}}}{{{fmt(sigma)}/\sqrt{{{s.n}}}}} = {fmt(z)}"
            ),
        ),
    ]
    return _response(test, steps, {"n": s.n, "mean": s.mean, "standard_error": se})


def t_one_sample(
    mu0: float,
    alternative: Alternative,
    alpha: float,
    data: list[float] | None = None,
    n: int | None = None,
    mean: float | None = None,
    sd: float | None = None,
) -> SolverResponse:
    _check_alpha(alpha)
    s, step = sample_stats(data, n, mean, sd)
    if s.sd is None:
        raise SolverError("Uji-t membutuhkan simpangan baku sampel s.")
    df = s.n - 1
    se = s.sd / np.sqrt(s.n)
    t = (s.mean - mu0) / se
    h0, h1 = hypotheses(r"\mu", fmt(mu0), alternative)
    test = HypothesisTest(
        h0,
        h1,
        alpha,
        "t",
        float(t),
        stats.t(df),
        f"t dengan derajat bebas {df}",
        alternative,
        reject_text=f"Terdapat cukup bukti bahwa rata-rata populasi {_alt_text(alternative)} {fmt(mu0)}.",
        accept_text=f"Tidak terdapat cukup bukti bahwa rata-rata populasi {_alt_text(alternative)} {fmt(mu0)}.",
    )
    steps = [
        step,
        Step(
            title="Hitung statistik uji t",
            explanation=f"σ populasi tidak diketahui sehingga diganti s; derajat bebas df = n − 1 = {df}.",
            latex=(
                rf"t = \frac{{\bar{{x}} - \mu_0}}{{s/\sqrt{{n}}}} = "
                rf"\frac{{{fmt(s.mean)} - {fmt(mu0)}}}{{{fmt(s.sd)}/\sqrt{{{s.n}}}}} = {fmt(t)}"
            ),
        ),
    ]
    return _response(test, steps, {"n": s.n, "mean": s.mean, "sd": s.sd, "df": df, "standard_error": se})


def t_independent(
    x: list[float], y: list[float], equal_var: bool, alternative: Alternative, alpha: float
) -> SolverResponse:
    _check_alpha(alpha)
    a, b = as_finite_array(x, "Sampel 1"), as_finite_array(y, "Sampel 2")
    if a.size < 2 or b.size < 2:
        raise SolverError("Setiap sampel membutuhkan minimal 2 data.")
    n1, n2 = a.size, b.size
    m1, m2 = float(a.mean()), float(b.mean())
    v1, v2 = float(a.var(ddof=1)), float(b.var(ddof=1))
    steps = [
        Step(
            title="Statistik tiap sampel",
            table=Table(
                columns=["Sampel", "n", "Rata-rata", "Varians"],
                rows=[["1", n1, m1, v1], ["2", n2, m2, v2]],
            ),
        )
    ]
    if equal_var:
        df = float(n1 + n2 - 2)
        sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / df
        se = float(np.sqrt(sp2 * (1 / n1 + 1 / n2)))
        steps.append(
            Step(
                title="Varians gabungan (pooled variance)",
                explanation="Diasumsikan kedua populasi memiliki varians sama.",
                latex=(
                    rf"s_p^2 = \frac{{(n_1-1)s_1^2 + (n_2-1)s_2^2}}{{n_1+n_2-2}} = {fmt(sp2)},\quad "
                    rf"SE = \sqrt{{s_p^2\left(\frac{{1}}{{n_1}}+\frac{{1}}{{n_2}}\right)}} = {fmt(se)}"
                ),
            )
        )
        df_label = f"t dengan df = n₁ + n₂ − 2 = {fmt(df)}"
    else:
        q1, q2 = v1 / n1, v2 / n2
        se = float(np.sqrt(q1 + q2))
        df = (q1 + q2) ** 2 / (q1**2 / (n1 - 1) + q2**2 / (n2 - 1))
        steps.append(
            Step(
                title="Galat baku & derajat bebas Welch",
                explanation="Varians tidak diasumsikan sama (uji Welch); df dihitung dengan rumus Welch–Satterthwaite.",
                latex=(
                    rf"SE = \sqrt{{\frac{{s_1^2}}{{n_1}}+\frac{{s_2^2}}{{n_2}}}} = {fmt(se)},\quad "
                    rf"df = \frac{{\left(\frac{{s_1^2}}{{n_1}}+\frac{{s_2^2}}{{n_2}}\right)^2}}"
                    rf"{{\frac{{(s_1^2/n_1)^2}}{{n_1-1}}+\frac{{(s_2^2/n_2)^2}}{{n_2-1}}}} = {fmt(df)}"
                ),
            )
        )
        df_label = f"t dengan df Welch = {fmt(df)}"
    t = (m1 - m2) / se
    steps.append(
        Step(
            title="Hitung statistik uji t",
            latex=rf"t = \frac{{\bar{{x}}_1 - \bar{{x}}_2}}{{SE}} = \frac{{{fmt(m1)} - {fmt(m2)}}}{{{fmt(se)}}} = {fmt(t)}",
        )
    )
    h0, h1 = hypotheses(r"\mu_1", r"\mu_2", alternative)
    test = HypothesisTest(
        h0,
        h1,
        alpha,
        "t",
        float(t),
        stats.t(df),
        df_label,
        alternative,
        reject_text=f"Terdapat cukup bukti bahwa rata-rata populasi 1 {_alt_text(alternative)} rata-rata populasi 2.",
        accept_text=f"Tidak terdapat cukup bukti bahwa rata-rata populasi 1 {_alt_text(alternative)} rata-rata populasi 2.",
    )
    return _response(test, steps, {"mean_diff": m1 - m2, "df": df, "standard_error": se})


def t_paired(x: list[float], y: list[float], alternative: Alternative, alpha: float) -> SolverResponse:
    _check_alpha(alpha)
    a, b = as_finite_array(x, "Sampel sebelum"), as_finite_array(y, "Sampel sesudah")
    if a.size != b.size:
        raise SolverError(f"Uji berpasangan membutuhkan jumlah data yang sama (sekarang {a.size} dan {b.size}).")
    if a.size < 2:
        raise SolverError("Uji berpasangan membutuhkan minimal 2 pasang data.")
    d = a - b
    n = d.size
    d_bar, s_d = float(d.mean()), float(d.std(ddof=1))
    if s_d == 0:
        raise SolverError("Semua selisih sama persis sehingga simpangan baku selisih = 0; uji-t tidak dapat dihitung.")
    se = s_d / np.sqrt(n)
    t = d_bar / se
    steps = [
        Step(
            title="Hitung selisih setiap pasangan",
            explanation="Uji berpasangan = uji-t satu sampel terhadap selisih d = x₁ − x₂.",
            table=Table(
                columns=["x₁", "x₂", "d = x₁ − x₂"],
                rows=[[float(p), float(q), float(r)] for p, q, r in zip(a, b, d, strict=True)],
            ),
        ),
        Step(
            title="Rata-rata & simpangan baku selisih",
            latex=rf"\bar{{d}} = {fmt(d_bar)},\quad s_d = {fmt(s_d)},\quad n = {n}",
        ),
        Step(
            title="Hitung statistik uji t",
            latex=rf"t = \frac{{\bar{{d}}}}{{s_d/\sqrt{{n}}}} = \frac{{{fmt(d_bar)}}}{{{fmt(s_d)}/\sqrt{{{n}}}}} = {fmt(t)}",
        ),
    ]
    h0, h1 = hypotheses(r"\mu_d", "0", alternative)
    test = HypothesisTest(
        h0,
        h1,
        alpha,
        "t",
        float(t),
        stats.t(n - 1),
        f"t dengan df = n − 1 = {n - 1}",
        alternative,
        reject_text=f"Terdapat cukup bukti bahwa rata-rata selisih {_alt_text(alternative)} 0.",
        accept_text=f"Tidak terdapat cukup bukti bahwa rata-rata selisih {_alt_text(alternative)} 0.",
    )
    return _response(test, steps, {"mean_diff": d_bar, "sd_diff": s_d, "df": n - 1})


# --------------------------------------------------------------------------- uji proporsi


def proportion_test(
    alternative: Alternative,
    alpha: float,
    x1: int,
    n1: int,
    p0: float | None = None,
    x2: int | None = None,
    n2: int | None = None,
) -> SolverResponse:
    _check_alpha(alpha)
    for x, n, label in ((x1, n1, "1"), (x2, n2, "2")):
        if n is None:
            continue
        if n <= 0 or x is None or not 0 <= x <= n:
            raise SolverError(f"Sampel {label}: jumlah sukses harus di antara 0 dan n (n > 0).")
    warnings: list[str] = []
    p1 = x1 / n1
    if x2 is None or n2 is None:
        if p0 is None or not 0 < p0 < 1:
            raise SolverError("Proporsi hipotesis p₀ harus di antara 0 dan 1.")
        se = float(np.sqrt(p0 * (1 - p0) / n1))
        z = (p1 - p0) / se
        if n1 * p0 < 5 or n1 * (1 - p0) < 5:
            warnings.append("n·p₀ atau n·(1−p₀) < 5: pendekatan normal kurang akurat.")
        steps = [
            Step(title="Proporsi sampel", latex=rf"\hat{{p}} = \frac{{{x1}}}{{{n1}}} = {fmt(p1)}"),
            Step(
                title="Hitung statistik uji z",
                latex=(
                    rf"z = \frac{{\hat{{p}} - p_0}}{{\sqrt{{p_0(1-p_0)/n}}}} = "
                    rf"\frac{{{fmt(p1)} - {fmt(p0)}}}{{\sqrt{{{fmt(p0)}(1-{fmt(p0)})/{n1}}}}} = {fmt(z)}"
                ),
            ),
        ]
        h0, h1 = hypotheses("p", fmt(p0), alternative)
        subject = f"proporsi populasi {_alt_text(alternative)} {fmt(p0)}"
        extra = {"p_hat": p1}
    else:
        p2 = x2 / n2
        pooled = (x1 + x2) / (n1 + n2)
        se = float(np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2)))
        if se == 0:
            raise SolverError("Proporsi gabungan 0 atau 1 sehingga galat baku = 0; uji tidak dapat dihitung.")
        z = (p1 - p2) / se
        steps = [
            Step(
                title="Proporsi tiap sampel & proporsi gabungan",
                latex=(
                    rf"\hat{{p}}_1 = \frac{{{x1}}}{{{n1}}} = {fmt(p1)},\quad \hat{{p}}_2 = \frac{{{x2}}}{{{n2}}} = {fmt(p2)},\quad "
                    rf"\bar{{p}} = \frac{{x_1+x_2}}{{n_1+n_2}} = {fmt(pooled)}"
                ),
            ),
            Step(
                title="Hitung statistik uji z",
                latex=(
                    rf"z = \frac{{\hat{{p}}_1 - \hat{{p}}_2}}{{\sqrt{{\bar{{p}}(1-\bar{{p}})\left(\frac{{1}}{{n_1}}+\frac{{1}}{{n_2}}\right)}}}}"
                    rf" = \frac{{{fmt(p1 - p2)}}}{{{fmt(se)}}} = {fmt(z)}"
                ),
            ),
        ]
        h0, h1 = hypotheses("p_1", "p_2", alternative)
        subject = f"proporsi populasi 1 {_alt_text(alternative)} proporsi populasi 2"
        extra = {"p1_hat": p1, "p2_hat": p2, "pooled": pooled}
    test = HypothesisTest(
        h0,
        h1,
        alpha,
        "z",
        float(z),
        stats.norm(),
        "normal baku N(0, 1)",
        alternative,
        reject_text=f"Terdapat cukup bukti bahwa {subject}.",
        accept_text=f"Tidak terdapat cukup bukti bahwa {subject}.",
    )
    return _response(test, steps, extra, warnings=warnings)


# --------------------------------------------------------------------------- chi-square


def chi_square_gof(
    observed: list[float],
    alpha: float,
    expected: list[float] | None = None,
    categories: list[str] | None = None,
    estimated_params: int = 0,
) -> SolverResponse:
    _check_alpha(alpha)
    o = as_finite_array(observed, "Frekuensi observasi")
    k = o.size
    if k < 2:
        raise SolverError("Uji goodness of fit membutuhkan minimal 2 kategori.")
    if np.any(o < 0):
        raise SolverError("Frekuensi observasi tidak boleh negatif.")
    total = float(o.sum())
    if expected is None:
        e = np.full(k, total / k)
        e_note = "Tanpa frekuensi harapan, setiap kategori diasumsikan berpeluang sama: Eᵢ = N/k."
    else:
        e = as_finite_array(expected, "Frekuensi harapan")
        if e.size != k:
            raise SolverError("Jumlah frekuensi harapan harus sama dengan jumlah kategori.")
        if np.any(e <= 0):
            raise SolverError("Frekuensi harapan harus lebih besar dari 0.")
        if abs(e.sum() - 1) < 1e-9:
            e = e * total
            e_note = "Frekuensi harapan diberikan sebagai peluang, lalu dikalikan N."
        else:
            if abs(e.sum() - total) > 1e-6 * max(total, 1):
                raise SolverError(
                    f"Jumlah frekuensi harapan ({fmt(float(e.sum()))}) harus sama dengan jumlah observasi ({fmt(total)}), "
                    "atau isi peluang yang berjumlah 1."
                )
            e_note = "Frekuensi harapan diambil dari soal."
    labels = categories if categories and len(categories) == k else [f"K{i + 1}" for i in range(k)]
    contrib = (o - e) ** 2 / e
    chi2 = float(contrib.sum())
    df = k - 1 - estimated_params
    if df < 1:
        raise SolverError("Derajat bebas harus ≥ 1; kurangi jumlah parameter yang diestimasi.")
    warnings = ["Ada frekuensi harapan < 5; hasil uji chi-square kurang dapat diandalkan."] if np.any(e < 5) else []
    steps = [
        Step(title="Frekuensi harapan", explanation=e_note),
        Step(
            title="Hitung kontribusi setiap kategori",
            latex=r"\chi^2 = \sum_{i=1}^{k} \frac{(O_i - E_i)^2}{E_i}",
            table=Table(
                columns=["Kategori", "O", "E", "(O − E)²/E"],
                rows=[
                    [lab, float(a), round(float(b), 6), round(float(c), 6)]
                    for lab, a, b, c in zip(labels, o, e, contrib, strict=True)
                ],
            ),
        ),
        Step(
            title="Statistik uji & derajat bebas",
            latex=rf"\chi^2 = {fmt(chi2)},\quad df = k - 1 - m = {k} - 1 - {estimated_params} = {df}",
        ),
    ]
    test = HypothesisTest(
        r"H_0: \text{data mengikuti distribusi yang dihipotesiskan}",
        r"H_1: \text{data tidak mengikuti distribusi tersebut}",
        alpha,
        r"\chi^2",
        chi2,
        stats.chi2(df),
        f"chi-square dengan df = {df}",
        "greater",
        reject_text="Data tidak sesuai dengan distribusi yang dihipotesiskan.",
        accept_text="Data sesuai (tidak berbeda nyata) dengan distribusi yang dihipotesiskan.",
    )
    bar = Chart(
        id="observed-expected",
        title="Observasi vs harapan",
        spec=plotly_figure(
            [
                {"type": "bar", "x": labels, "y": o.tolist(), "name": "Observasi (O)"},
                {"type": "bar", "x": labels, "y": e.tolist(), "name": "Harapan (E)"},
            ],
            "Frekuensi observasi vs harapan",
            barmode="group",
        ),
    )
    return _response(test, steps, {"df": df, "expected": e.tolist()}, warnings=warnings, charts=[bar])


def chi_square_independence(
    table: list[list[float]], alpha: float, row_labels: list[str] | None = None, col_labels: list[str] | None = None
) -> SolverResponse:
    _check_alpha(alpha)
    try:
        o = np.asarray(table, dtype=float)
    except ValueError as exc:
        raise SolverError("Tabel kontingensi harus berupa matriks angka dengan jumlah kolom yang sama.") from exc
    if o.ndim != 2 or o.shape[0] < 2 or o.shape[1] < 2:
        raise SolverError("Tabel kontingensi minimal berukuran 2 × 2.")
    if not np.all(np.isfinite(o)) or np.any(o < 0):
        raise SolverError("Isi tabel kontingensi harus angka tidak negatif.")
    r, c = o.shape
    rows_tot, cols_tot, total = o.sum(axis=1), o.sum(axis=0), float(o.sum())
    if np.any(rows_tot == 0) or np.any(cols_tot == 0):
        raise SolverError("Ada baris atau kolom yang seluruhnya nol; hapus baris/kolom tersebut.")
    e = np.outer(rows_tot, cols_tot) / total
    chi2 = float(((o - e) ** 2 / e).sum())
    df = (r - 1) * (c - 1)
    rl = row_labels if row_labels and len(row_labels) == r else [f"B{i + 1}" for i in range(r)]
    cl = col_labels if col_labels and len(col_labels) == c else [f"K{j + 1}" for j in range(c)]
    cramers_v = float(np.sqrt(chi2 / (total * (min(r, c) - 1))))
    warnings = ["Ada frekuensi harapan < 5; pertimbangkan menggabungkan kategori."] if np.any(e < 5) else []
    steps = [
        Step(
            title="Hitung frekuensi harapan",
            explanation="Frekuensi harapan tiap sel bila kedua variabel independen.",
            latex=r"E_{ij} = \frac{(\text{total baris } i)(\text{total kolom } j)}{N}",
            table=Table(columns=["", *cl], rows=[[rl[i], *[round(float(v), 4) for v in e[i]]] for i in range(r)]),
        ),
        Step(
            title="Hitung statistik chi-square",
            latex=rf"\chi^2 = \sum_i\sum_j \frac{{(O_{{ij}}-E_{{ij}})^2}}{{E_{{ij}}}} = {fmt(chi2)},\quad df = (r-1)(c-1) = {df}",
        ),
        Step(
            title="Kekuatan hubungan (Cramér's V)",
            latex=rf"V = \sqrt{{\frac{{\chi^2}}{{N(\min(r,c)-1)}}}} = {fmt(cramers_v)}",
        ),
    ]
    test = HypothesisTest(
        r"H_0: \text{kedua variabel independen}",
        r"H_1: \text{kedua variabel saling berhubungan}",
        alpha,
        r"\chi^2",
        chi2,
        stats.chi2(df),
        f"chi-square dengan df = {df}",
        "greater",
        reject_text="Terdapat hubungan yang signifikan antara kedua variabel.",
        accept_text="Tidak terdapat hubungan yang signifikan antara kedua variabel (independen).",
    )
    heat = Chart(
        id="contingency",
        title="Tabel kontingensi",
        spec=plotly_figure(
            [{"type": "heatmap", "z": o.tolist(), "x": cl, "y": rl, "colorscale": "Blues", "texttemplate": "%{z}"}],
            "Frekuensi observasi",
        ),
    )
    return _response(
        test, steps, {"df": df, "expected": e.tolist(), "cramers_v": cramers_v}, warnings=warnings, charts=[heat]
    )


# --------------------------------------------------------------------------- uji F


def f_test(x: list[float], y: list[float], alternative: Alternative, alpha: float) -> SolverResponse:
    _check_alpha(alpha)
    a, b = as_finite_array(x, "Sampel 1"), as_finite_array(y, "Sampel 2")
    if a.size < 2 or b.size < 2:
        raise SolverError("Setiap sampel membutuhkan minimal 2 data.")
    v1, v2 = float(a.var(ddof=1)), float(b.var(ddof=1))
    if v2 == 0:
        raise SolverError("Varians sampel 2 bernilai 0; rasio F tidak terdefinisi.")
    f = v1 / v2
    df1, df2 = a.size - 1, b.size - 1
    steps = [
        Step(
            title="Varians tiap sampel",
            latex=rf"s_1^2 = {fmt(v1)}\ (n_1 = {a.size}),\quad s_2^2 = {fmt(v2)}\ (n_2 = {b.size})",
        ),
        Step(
            title="Hitung statistik uji F",
            latex=rf"F = \frac{{s_1^2}}{{s_2^2}} = \frac{{{fmt(v1)}}}{{{fmt(v2)}}} = {fmt(f)},\quad df_1 = {df1},\ df_2 = {df2}",
        ),
    ]
    h0, h1 = hypotheses(r"\sigma_1^2", r"\sigma_2^2", alternative)
    test = HypothesisTest(
        h0,
        h1,
        alpha,
        "F",
        f,
        stats.f(df1, df2),
        f"F dengan df = ({df1}, {df2})",
        alternative,
        reject_text=f"Terdapat cukup bukti bahwa varians populasi 1 {_alt_text(alternative)} varians populasi 2.",
        accept_text=f"Tidak terdapat cukup bukti bahwa varians populasi 1 {_alt_text(alternative)} varians populasi 2.",
    )
    return _response(test, steps, {"df1": df1, "df2": df2, "var1": v1, "var2": v2})


def _alt_text(alternative: Alternative) -> str:
    return {"two-sided": "berbeda dari", "less": "lebih kecil dari", "greater": "lebih besar dari"}[alternative]
