"""Helper bersama untuk solver: format angka dan pembuat grafik Plotly."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, Step, SummaryItem


def fmt(x: float, digits: int = 4) -> str:
    """Format angka untuk teks/LaTeX: bulat tanpa desimal, lainnya dibulatkan."""
    if x is None or not np.isfinite(x):
        return "—"
    if float(x).is_integer():
        return str(int(x))
    if abs(x) < 10 ** -min(digits, 4):
        return f"{x:.3g}"  # mis. p-value 3.21e-07, jangan dibulatkan menjadi 0
    return f"{x:.{digits}f}".rstrip("0").rstrip(".")


def as_finite_array(values: Sequence[float], name: str = "data") -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        raise SolverError(f"{name} kosong. Masukkan minimal satu nilai.")
    if not np.all(np.isfinite(arr)):
        raise SolverError(f"{name} mengandung nilai kosong/tak berhingga. Bersihkan data terlebih dahulu.")
    return arr


def plotly_figure(data: list[dict[str, Any]], title: str, **layout: Any) -> dict[str, Any]:
    return {"data": data, "layout": {"title": {"text": title}, **layout}}


def summary_items(pairs: list[tuple[str, Any]]) -> list[SummaryItem]:
    return [SummaryItem(label=label, value=_jsonable(value)) for label, value in pairs]


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


Alternative = Literal["two-sided", "less", "greater"]

_ALT_SYMBOL = {"two-sided": r"\neq", "less": "<", "greater": ">"}


def hypotheses(param: str, null_value: str, alternative: Alternative) -> tuple[str, str]:
    """LaTeX H0 dan H1 untuk uji satu parameter."""
    h0_symbol = {"two-sided": "=", "less": r"\ge", "greater": r"\le"}[alternative]
    return (
        rf"H_0: {param} {h0_symbol} {null_value}",
        rf"H_1: {param} {_ALT_SYMBOL[alternative]} {null_value}",
    )


@dataclass
class HypothesisTest:
    """Kerangka uji hipotesis: hipotesis → α → (langkah hitung) → keputusan → kesimpulan.

    `dist` adalah distribusi statistik uji di bawah H0 (objek frozen scipy.stats).
    """

    h0: str
    h1: str
    alpha: float
    stat_symbol: str
    stat: float
    dist: Any
    dist_label: str
    alternative: Alternative
    reject_text: str
    accept_text: str

    @property
    def p_value(self) -> float:
        if self.alternative == "greater":
            return float(self.dist.sf(self.stat))
        if self.alternative == "less":
            return float(self.dist.cdf(self.stat))
        return float(min(1.0, 2 * min(self.dist.cdf(self.stat), self.dist.sf(self.stat))))

    @property
    def critical(self) -> tuple[float | None, float | None]:
        """(batas bawah, batas atas) daerah kritis; None bila tidak ada sisi tersebut."""
        a = self.alpha
        if self.alternative == "greater":
            return None, float(self.dist.ppf(1 - a))
        if self.alternative == "less":
            return float(self.dist.ppf(a)), None
        return float(self.dist.ppf(a / 2)), float(self.dist.ppf(1 - a / 2))

    @property
    def reject(self) -> bool:
        return self.p_value < self.alpha

    @property
    def conclusion(self) -> str:
        return self.reject_text if self.reject else self.accept_text

    def head_steps(self) -> list[Step]:
        return [
            Step(
                title="Rumuskan hipotesis",
                explanation="H₀ adalah pernyataan yang diuji; H₁ adalah dugaan alternatifnya.",
                latex=rf"{self.h0} \qquad {self.h1}",
            ),
            Step(
                title="Tentukan taraf signifikansi",
                explanation=f"Peluang maksimum menolak H₀ padahal H₀ benar (galat tipe I) adalah α = {fmt(self.alpha)}.",
                latex=rf"\alpha = {fmt(self.alpha)}",
            ),
        ]

    def tail_steps(self) -> list[Step]:
        lo, hi = self.critical
        s = self.stat_symbol
        if self.alternative == "greater":
            region = rf"{s} > {fmt(hi)}"
        elif self.alternative == "less":
            region = rf"{s} < {fmt(lo)}"
        else:
            region = rf"{s} < {fmt(lo)} \text{{ atau }} {s} > {fmt(hi)}"
        decision = "Tolak H₀" if self.reject else "Gagal menolak H₀"
        return [
            Step(
                title="Daerah kritis & p-value",
                explanation=f"Di bawah H₀, statistik uji berdistribusi {self.dist_label}. "
                f"Tolak H₀ bila statistik jatuh di daerah kritis, atau setara bila p-value < α.",
                latex=rf"\text{{Daerah kritis: }} {region},\qquad p\text{{-value}} = {fmt(self.p_value, 6)}",
            ),
            Step(
                title="Keputusan & kesimpulan",
                explanation=f"{decision} karena p-value = {fmt(self.p_value, 6)} "
                f"{'<' if self.reject else '≥'} α = {fmt(self.alpha)}. {self.conclusion}",
                latex=rf"{s} = {fmt(self.stat)}",
            ),
        ]

    def summary(self) -> list[SummaryItem]:
        lo, hi = self.critical
        crit = " dan ".join(fmt(c) for c in (lo, hi) if c is not None)
        return summary_items(
            [
                ("Statistik uji", self.stat),
                ("p-value", self.p_value),
                ("Nilai kritis", crit),
                ("α", self.alpha),
                ("Keputusan", "Tolak H₀" if self.reject else "Gagal menolak H₀"),
            ]
        )

    def result(self) -> dict[str, Any]:
        lo, hi = self.critical
        return {
            "statistic": self.stat,
            "p_value": self.p_value,
            "critical_lower": lo,
            "critical_upper": hi,
            "alpha": self.alpha,
            "reject_h0": self.reject,
        }

    def chart(self) -> Chart:
        d = self.dist
        lo_x = min(float(d.ppf(0.0005)), self.stat)
        hi_x = max(float(d.ppf(0.9995)), self.stat)
        pad = (hi_x - lo_x) * 0.05
        xs = np.linspace(lo_x - pad, hi_x + pad, 400)
        ys = d.pdf(xs)
        traces: list[dict[str, Any]] = [
            {"type": "scatter", "mode": "lines", "x": xs.tolist(), "y": ys.tolist(), "name": self.dist_label}
        ]
        lo, hi = self.critical
        for bound, side in ((lo, "lower"), (hi, "upper")):
            if bound is None:
                continue
            mask = xs <= bound if side == "lower" else xs >= bound
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": xs[mask].tolist(),
                    "y": ys[mask].tolist(),
                    "fill": "tozeroy",
                    "name": "Daerah kritis",
                    "line": {"color": "#ef4444"},
                    "showlegend": side == "upper" or hi is None,
                }
            )
        stat_y = float(d.pdf(self.stat))
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": [self.stat, self.stat],
                "y": [0, max(stat_y, float(ys.max()) * 0.15)],
                "name": f"Statistik uji = {fmt(self.stat)}",
                "line": {"color": "#f59e0b", "dash": "dash"},
            }
        )
        return Chart(
            id="test-distribution",
            title="Distribusi statistik uji & daerah kritis",
            spec=plotly_figure(
                traces, "Distribusi statistik uji di bawah H₀", xaxis={"title": {"text": self.stat_symbol}}
            ),
        )
