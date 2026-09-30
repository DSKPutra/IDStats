"""Uji normalitas: Shapiro-Wilk dan Kolmogorov-Smirnov (termasuk varian Lilliefors)."""

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, SolverResponse, Step, Table
from app.solvers._base import as_finite_array, fmt, plotly_figure, summary_items

_LILLIEFORS_SIMULATIONS = 4000


def _check_alpha(alpha: float) -> None:
    if not 0 < alpha < 1:
        raise SolverError("Taraf signifikansi α harus di antara 0 dan 1.")


def _qq_chart(x: np.ndarray) -> Chart:
    (osm, osr), (slope, intercept, _) = stats.probplot(x, dist="norm")
    return Chart(
        id="qqplot",
        title="Q-Q plot normal",
        spec=plotly_figure(
            [
                {"type": "scatter", "mode": "markers", "x": osm.tolist(), "y": osr.tolist(), "name": "Data"},
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": [float(osm[0]), float(osm[-1])],
                    "y": [float(intercept + slope * osm[0]), float(intercept + slope * osm[-1])],
                    "name": "Garis normal",
                },
            ],
            "Q-Q plot normal",
            xaxis={"title": {"text": "Kuantil teoretis"}},
            yaxis={"title": {"text": "Kuantil sampel"}},
        ),
    )


def _decision(p: float, alpha: float) -> tuple[bool, str]:
    normal = p >= alpha
    return normal, (
        f"p-value = {fmt(p, 6)} ≥ α = {fmt(alpha)}: gagal menolak H₀, data dapat dianggap berdistribusi normal."
        if normal
        else f"p-value = {fmt(p, 6)} < α = {fmt(alpha)}: tolak H₀, data tidak berdistribusi normal."
    )


_HYP = Step(
    title="Rumuskan hipotesis",
    latex=r"H_0: \text{data berasal dari populasi berdistribusi normal} \qquad H_1: \text{data tidak berdistribusi normal}",
)


def shapiro_wilk(data: list[float], alpha: float) -> SolverResponse:
    _check_alpha(alpha)
    x = as_finite_array(data)
    n = x.size
    if n < 3:
        raise SolverError("Uji Shapiro-Wilk membutuhkan minimal 3 data.")
    if n > 5000:
        raise SolverError("Uji Shapiro-Wilk dibatasi maksimal 5000 data; gunakan uji Kolmogorov-Smirnov.")
    if np.all(x == x[0]):
        raise SolverError("Semua data bernilai sama; uji normalitas tidak dapat dihitung.")
    w, p = stats.shapiro(x)
    w, p = float(w), float(p)
    normal, text = _decision(p, alpha)
    xs = np.sort(x)
    ss = float(((x - x.mean()) ** 2).sum())
    steps = [
        _HYP,
        Step(
            title="Urutkan data & hitung jumlah kuadrat",
            latex=rf"x_{{(1)}} \le \dots \le x_{{({n})}},\quad SS = \sum (x_i - \bar{{x}})^2 = {fmt(ss)}",
        ),
        Step(
            title="Statistik W",
            explanation=(
                "Koefisien aᵢ diturunkan dari nilai harapan statistik terurut distribusi normal baku "
                "(algoritma AS R94 Royston). W mendekati 1 bila data mendekati normal."
            ),
            latex=rf"W = \frac{{\left(\sum_{{i=1}}^{{n}} a_i x_{{(i)}}\right)^2}}{{\sum (x_i-\bar{{x}})^2}} = {fmt(w, 6)}",
        ),
        Step(title="Keputusan", explanation=text, latex=rf"W = {fmt(w, 6)},\quad p = {fmt(p, 6)}"),
    ]
    return SolverResponse(
        result={
            "statistic": w,
            "p_value": p,
            "alpha": alpha,
            "normal": normal,
            "n": n,
            "min": float(xs[0]),
            "max": float(xs[-1]),
        },
        steps=steps,
        charts=[_qq_chart(x)],
        summary=summary_items(
            [("W", w), ("p-value", p), ("n", n), ("Keputusan", "Normal" if normal else "Tidak normal")]
        ),
        conclusion=text,
    )


def kolmogorov_smirnov(
    data: list[float], alpha: float, mean: float | None = None, sd: float | None = None, seed: int = 0
) -> SolverResponse:
    """Bila μ dan σ tidak diberikan, keduanya diestimasi dari sampel dan p-value dihitung dengan
    koreksi Lilliefors (simulasi Monte Carlo), karena tabel KS biasa menjadi terlalu konservatif."""
    _check_alpha(alpha)
    x = as_finite_array(data)
    n = x.size
    if n < 3:
        raise SolverError("Uji Kolmogorov-Smirnov membutuhkan minimal 3 data.")
    estimated = mean is None or sd is None
    mu = float(x.mean()) if mean is None else float(mean)
    sigma = float(x.std(ddof=1)) if sd is None else float(sd)
    if sigma <= 0:
        raise SolverError("Simpangan baku harus lebih besar dari 0.")
    xs = np.sort(x)
    f = stats.norm.cdf(xs, mu, sigma)
    i = np.arange(1, n + 1)
    d_plus = i / n - f
    d_minus = f - (i - 1) / n
    d = float(max(d_plus.max(), d_minus.max()))
    if estimated:
        rng = np.random.default_rng(seed)
        sims = rng.standard_normal((_LILLIEFORS_SIMULATIONS, n))
        sims.sort(axis=1)
        z = (sims - sims.mean(axis=1, keepdims=True)) / sims.std(axis=1, ddof=1, keepdims=True)
        fs = stats.norm.cdf(z)
        d_sim = np.maximum((i / n - fs).max(axis=1), (fs - (i - 1) / n).max(axis=1))
        p = float((np.sum(d_sim >= d) + 1) / (_LILLIEFORS_SIMULATIONS + 1))
        d_crit = float(np.quantile(d_sim, 1 - alpha))
        method = "Lilliefors (μ dan σ diestimasi dari sampel)"
    else:
        p = float(stats.kstwo.sf(d, n))
        d_crit = float(stats.kstwo.ppf(1 - alpha, n))
        method = "Kolmogorov-Smirnov (μ dan σ diketahui)"
    normal, text = _decision(p, alpha)
    show = n <= 60
    steps = [
        _HYP,
        Step(
            title="Parameter distribusi normal acuan",
            explanation="μ dan σ diestimasi dari sampel." if estimated else "μ dan σ diambil dari soal.",
            latex=rf"\mu = {fmt(mu)},\quad \sigma = {fmt(sigma)}",
        ),
        Step(
            title="Bandingkan CDF empiris dengan CDF normal",
            latex=(
                r"D = \max_i \left\{ \frac{i}{n} - F(x_{(i)}),\ F(x_{(i)}) - \frac{i-1}{n} \right\}"
                rf" = {fmt(d, 6)}"
            ),
            table=Table(
                columns=["i", "x₍ᵢ₎", "F(x₍ᵢ₎)", "i/n − F", "F − (i−1)/n"],
                rows=[
                    [int(k), float(v), round(float(fv), 6), round(float(a), 6), round(float(b), 6)]
                    for k, v, fv, a, b in zip(i, xs, f, d_plus, d_minus, strict=True)
                ],
            )
            if show
            else None,
        ),
        Step(
            title="Nilai kritis & keputusan",
            explanation=f"Metode: {method}. {text}",
            latex=rf"D = {fmt(d, 6)},\quad D_{{kritis}} = {fmt(d_crit, 6)},\quad p = {fmt(p, 6)}",
        ),
    ]
    grid = np.linspace(xs[0] - sigma * 0.5, xs[-1] + sigma * 0.5, 200)
    ecdf_x = np.repeat(xs, 2)
    ecdf_y = np.concatenate([[0], np.repeat(i / n, 2)[:-1]])
    chart = Chart(
        id="ecdf",
        title="CDF empiris vs CDF normal",
        spec=plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": ecdf_x.tolist(),
                    "y": ecdf_y.tolist(),
                    "name": "CDF empiris",
                    "line": {"shape": "hv"},
                },
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": grid.tolist(),
                    "y": stats.norm.cdf(grid, mu, sigma).tolist(),
                    "name": "CDF normal",
                },
            ],
            "CDF empiris vs CDF normal",
        ),
    )
    warnings = (
        [f"p-value Lilliefors dihitung dengan {_LILLIEFORS_SIMULATIONS} simulasi Monte Carlo."] if estimated else []
    )
    return SolverResponse(
        result={
            "statistic": d,
            "p_value": p,
            "critical_value": d_crit,
            "alpha": alpha,
            "normal": normal,
            "method": method,
            "mean": mu,
            "sd": sigma,
        },
        steps=steps,
        charts=[chart, _qq_chart(x)],
        summary=summary_items(
            [
                ("D", d),
                ("D kritis", d_crit),
                ("p-value", p),
                ("Metode", method),
                ("Keputusan", "Normal" if normal else "Tidak normal"),
            ]
        ),
        warnings=warnings,
        conclusion=text,
    )
