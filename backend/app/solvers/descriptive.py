"""Statistik deskriptif — dihitung manual agar langkahnya bisa ditampilkan."""

from collections import Counter

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, SolverResponse, Step, Table
from app.solvers._base import as_finite_array, fmt, plotly_figure

_MAX_TABLE_ROWS = 50


def _quantile_type7(sorted_x: np.ndarray, p: float) -> float:
    """Kuartil metode interpolasi linier (Hyndman–Fan tipe 7, = Excel QUARTILE.INC)."""
    h = (len(sorted_x) - 1) * p
    lo = int(np.floor(h))
    hi = min(lo + 1, len(sorted_x) - 1)
    return float(sorted_x[lo] + (h - lo) * (sorted_x[hi] - sorted_x[lo]))


def summary(data: list[float]) -> SolverResponse:
    x = as_finite_array(data)
    n = x.size
    if n < 2:
        raise SolverError("Statistik deskriptif membutuhkan minimal 2 data.")

    steps: list[Step] = []
    warnings: list[str] = []
    xs = np.sort(x)

    steps.append(
        Step(
            title="1. Urutkan data",
            explanation=f"Data diurutkan dari terkecil ke terbesar (n = {n}).",
            latex=r"x_{(1)} \le x_{(2)} \le \dots \le x_{(n)}",
            table=Table(columns=["i", "x_(i)"], rows=[[i + 1, float(v)] for i, v in enumerate(xs)])
            if n <= _MAX_TABLE_ROWS
            else None,
        )
    )

    total = float(np.sum(x))
    mean = total / n
    steps.append(
        Step(
            title="2. Rata-rata (Mean)",
            explanation="Jumlahkan seluruh data lalu bagi dengan banyaknya data.",
            latex=rf"\bar{{x}} = \frac{{\sum x_i}}{{n}} = \frac{{{fmt(total)}}}{{{n}}} = {fmt(mean)}",
        )
    )

    if n % 2 == 1:
        median = float(xs[n // 2])
        median_latex = rf"\tilde{{x}} = x_{{({(n + 1) // 2})}} = {fmt(median)}"
    else:
        a, b = float(xs[n // 2 - 1]), float(xs[n // 2])
        median = (a + b) / 2
        median_latex = (
            rf"\tilde{{x}} = \frac{{x_{{({n // 2})}} + x_{{({n // 2 + 1})}}}}{{2}}"
            rf" = \frac{{{fmt(a)} + {fmt(b)}}}{{2}} = {fmt(median)}"
        )
    steps.append(
        Step(
            title="3. Median",
            explanation="Nilai tengah data terurut (rata-rata dua nilai tengah bila n genap).",
            latex=median_latex,
        )
    )

    counts = Counter(x.tolist())
    max_freq = max(counts.values())
    modes = sorted(v for v, c in counts.items() if c == max_freq) if max_freq > 1 else []
    if not modes:
        warnings.append("Tidak ada modus: setiap nilai muncul tepat satu kali.")
    steps.append(
        Step(
            title="4. Modus (Mode)",
            explanation=(
                f"Nilai dengan frekuensi terbesar ({max_freq} kali): {', '.join(fmt(m) for m in modes)}."
                if modes
                else "Semua nilai muncul satu kali sehingga data tidak memiliki modus."
            ),
        )
    )

    dev = x - mean
    ss = float(np.sum(dev**2))
    variance = ss / (n - 1)
    std = float(np.sqrt(variance))
    steps.append(
        Step(
            title="5. Varians & simpangan baku sampel",
            explanation="Hitung kuadrat simpangan setiap data terhadap rata-rata, jumlahkan, lalu bagi dengan n − 1.",
            latex=(
                rf"s^2 = \frac{{\sum (x_i - \bar{{x}})^2}}{{n-1}} = \frac{{{fmt(ss)}}}{{{n - 1}}} = {fmt(variance)}"
                rf",\quad s = \sqrt{{s^2}} = {fmt(std)}"
            ),
            table=Table(
                columns=["x_i", "x_i − x̄", "(x_i − x̄)²"],
                rows=[[float(v), round(float(d), 6), round(float(d * d), 6)] for v, d in zip(x, dev, strict=True)],
            )
            if n <= _MAX_TABLE_ROWS
            else None,
        )
    )

    q1, q2, q3 = (_quantile_type7(xs, p) for p in (0.25, 0.5, 0.75))
    iqr = q3 - q1
    steps.append(
        Step(
            title="6. Kuartil & jangkauan antarkuartil (IQR)",
            explanation=(
                "Posisi kuartil ke-p: h = (n − 1)·p, lalu interpolasi linier antara x_(⌊h⌋+1) dan x_(⌊h⌋+2) "
                "(metode tipe 7, sama dengan Excel QUARTILE.INC)."
            ),
            latex=rf"Q_1 = {fmt(q1)},\; Q_2 = {fmt(q2)},\; Q_3 = {fmt(q3)},\; IQR = Q_3 - Q_1 = {fmt(iqr)}",
        )
    )

    skewness: float | None = None
    kurtosis: float | None = None
    m2 = ss / n
    if n >= 3 and m2 > 0:
        m3 = float(np.sum(dev**3)) / n
        g1 = m3 / m2**1.5
        skewness = float(np.sqrt(n * (n - 1)) / (n - 2) * g1)
    else:
        warnings.append("Skewness membutuhkan minimal 3 data dengan variasi tidak nol.")
    if n >= 4 and m2 > 0:
        m4 = float(np.sum(dev**4)) / n
        g2 = m4 / m2**2 - 3
        kurtosis = float((n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * g2 + 6))
    else:
        warnings.append("Kurtosis membutuhkan minimal 4 data dengan variasi tidak nol.")
    steps.append(
        Step(
            title="7. Kemencengan (Skewness) & keruncingan (Kurtosis)",
            explanation=(
                "Menggunakan estimator sampel terkoreksi bias (sama dengan Excel SKEW/KURT dan SPSS). "
                "Kurtosis yang ditampilkan adalah excess kurtosis (distribusi normal = 0)."
            ),
            latex=(
                r"G_1 = \frac{\sqrt{n(n-1)}}{n-2}\cdot\frac{m_3}{m_2^{3/2}} = "
                + fmt(skewness)
                + r",\quad G_2 = \frac{n-1}{(n-2)(n-3)}\left[(n+1)\left(\frac{m_4}{m_2^2}-3\right)+6\right] = "
                + fmt(kurtosis)
            ),
        )
    )

    result = {
        "n": n,
        "sum": total,
        "mean": mean,
        "median": median,
        "modes": modes,
        "variance": variance,
        "std": std,
        "min": float(xs[0]),
        "max": float(xs[-1]),
        "range": float(xs[-1] - xs[0]),
        "q1": q1,
        "q2": q2,
        "q3": q3,
        "iqr": iqr,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "standard_error": std / np.sqrt(n),
        "coefficient_of_variation": std / mean if mean != 0 else None,
    }

    (osm, osr), (slope, intercept, _) = stats.probplot(x, dist="norm")
    charts = [
        Chart(
            id="histogram",
            title="Histogram",
            spec=plotly_figure(
                [{"type": "histogram", "x": x.tolist(), "name": "Frekuensi"}],
                "Histogram",
                xaxis={"title": {"text": "Nilai"}},
                yaxis={"title": {"text": "Frekuensi"}},
                bargap=0.05,
            ),
        ),
        Chart(
            id="boxplot",
            title="Boxplot",
            spec=plotly_figure(
                [{"type": "box", "y": x.tolist(), "name": "Data", "boxpoints": "outliers", "boxmean": True}],
                "Boxplot",
            ),
        ),
        Chart(
            id="qqplot",
            title="Q-Q Plot (Normal)",
            spec=plotly_figure(
                [
                    {"type": "scatter", "mode": "markers", "x": osm.tolist(), "y": osr.tolist(), "name": "Data"},
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "x": [float(osm[0]), float(osm[-1])],
                        "y": [float(intercept + slope * osm[0]), float(intercept + slope * osm[-1])],
                        "name": "Garis referensi",
                    },
                ],
                "Q-Q Plot (Normal)",
                xaxis={"title": {"text": "Kuantil teoretis"}},
                yaxis={"title": {"text": "Kuantil sampel"}},
            ),
        ),
    ]

    return SolverResponse(result=result, steps=steps, charts=charts, warnings=warnings)
