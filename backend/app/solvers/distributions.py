"""Kalkulator distribusi probabilitas (PDF/PMF, CDF, invers) dan tabel statistik ala Appendix 5."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step
from app.solvers._base import fmt, plotly_figure, summary_items


@dataclass(frozen=True)
class Param:
    key: str
    label: str
    default: float
    integer: bool = False


@dataclass(frozen=True)
class Distribution:
    id: str
    title: str
    discrete: bool
    params: list[Param]
    formula: str
    make: Callable[[dict[str, float]], Any]
    validate: Callable[[dict[str, float]], str | None]
    support: str
    notes: list[str] = field(default_factory=list)


def _pos(*keys: str) -> Callable[[dict[str, float]], str | None]:
    def check(p: dict[str, float]) -> str | None:
        for k in keys:
            if p[k] <= 0:
                return f"Parameter {k} harus lebih besar dari 0."
        return None

    return check


def _binom_check(p: dict[str, float]) -> str | None:
    if p["n"] < 1 or not float(p["n"]).is_integer():
        return "n harus bilangan bulat ≥ 1."
    if not 0 <= p["p"] <= 1:
        return "p harus di antara 0 dan 1."
    return None


def _uniform_check(p: dict[str, float]) -> str | None:
    return None if p["b"] > p["a"] else "Batas atas b harus lebih besar dari batas bawah a."


def _gamma_check(p: dict[str, float]) -> str | None:
    return _pos("k", "lam")(p)


DISTRIBUTIONS: dict[str, Distribution] = {
    d.id: d
    for d in [
        Distribution(
            "binomial",
            "Binomial",
            True,
            [Param("n", "n (jumlah percobaan)", 10, True), Param("p", "p (peluang sukses)", 0.5)],
            r"P(X=x) = \binom{n}{x} p^x (1-p)^{n-x}",
            lambda p: stats.binom(int(p["n"]), p["p"]),
            _binom_check,
            r"x = 0, 1, \dots, n",
        ),
        Distribution(
            "poisson",
            "Poisson",
            True,
            [Param("lam", "λ (rata-rata kejadian)", 3)],
            r"P(X=x) = \frac{e^{-\lambda}\lambda^x}{x!}",
            lambda p: stats.poisson(p["lam"]),
            _pos("lam"),
            r"x = 0, 1, 2, \dots",
        ),
        Distribution(
            "normal",
            "Normal",
            False,
            [Param("mu", "μ (rata-rata)", 0), Param("sigma", "σ (simpangan baku)", 1)],
            r"f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{(x-\mu)^2}{2\sigma^2}},\quad F(x) = \Phi\!\left(\frac{x-\mu}{\sigma}\right)",
            lambda p: stats.norm(p["mu"], p["sigma"]),
            _pos("sigma"),
            r"-\infty < x < \infty",
        ),
        Distribution(
            "exponential",
            "Eksponensial (Exponential)",
            False,
            [Param("lam", "λ (laju)", 1)],
            r"f(x) = \lambda e^{-\lambda x},\quad F(x) = 1 - e^{-\lambda x}",
            lambda p: stats.expon(scale=1 / p["lam"]),
            _pos("lam"),
            r"x \ge 0",
            ["Dipakai untuk waktu antarkedatangan dan waktu pelayanan pada teori antrian (Bab 17)."],
        ),
        Distribution(
            "uniform",
            "Seragam (Uniform)",
            False,
            [Param("a", "a (batas bawah)", 0), Param("b", "b (batas atas)", 1)],
            r"f(x) = \frac{1}{b-a},\quad F(x) = \frac{x-a}{b-a}",
            lambda p: stats.uniform(p["a"], p["b"] - p["a"]),
            _uniform_check,
            r"a \le x \le b",
        ),
        Distribution(
            "t",
            "t-Student",
            False,
            [Param("df", "ν (derajat bebas)", 10)],
            r"f(x) = \frac{\Gamma\left(\frac{\nu+1}{2}\right)}{\sqrt{\nu\pi}\,\Gamma\left(\frac{\nu}{2}\right)}\left(1+\frac{x^2}{\nu}\right)^{-\frac{\nu+1}{2}}",
            lambda p: stats.t(p["df"]),
            _pos("df"),
            r"-\infty < x < \infty",
        ),
        Distribution(
            "chi2",
            "Chi-square (χ²)",
            False,
            [Param("df", "k (derajat bebas)", 5)],
            r"f(x) = \frac{x^{k/2-1}e^{-x/2}}{2^{k/2}\Gamma(k/2)}",
            lambda p: stats.chi2(p["df"]),
            _pos("df"),
            r"x \ge 0",
        ),
        Distribution(
            "f",
            "F (Fisher–Snedecor)",
            False,
            [Param("df1", "d₁ (df pembilang)", 5), Param("df2", "d₂ (df penyebut)", 10)],
            r"X = \frac{U_1/d_1}{U_2/d_2},\quad U_i \sim \chi^2_{d_i}",
            lambda p: stats.f(p["df1"], p["df2"]),
            _pos("df1", "df2"),
            r"x \ge 0",
        ),
        Distribution(
            "gamma",
            "Erlang / Gamma",
            False,
            [Param("k", "k (bentuk)", 2), Param("lam", "λ (laju)", 1)],
            r"f(x) = \frac{\lambda^k x^{k-1} e^{-\lambda x}}{\Gamma(k)}",
            lambda p: stats.gamma(p["k"], scale=1 / p["lam"]),
            _gamma_check,
            r"x \ge 0",
            [
                "Bila k bilangan bulat, distribusi ini disebut Erlang: jumlah k variabel eksponensial (Bab 17, model M/Eₖ/s)."
            ],
        ),
    ]
}


def catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": d.id,
            "title": d.title,
            "discrete": d.discrete,
            "formula": d.formula,
            "support": d.support,
            "params": [{"key": p.key, "label": p.label, "default": p.default, "integer": p.integer} for p in d.params],
        }
        for d in DISTRIBUTIONS.values()
    ]


def compute(
    dist: str,
    params: dict[str, float],
    mode: str,
    x: float | None = None,
    p: float | None = None,
    a: float | None = None,
    b: float | None = None,
) -> SolverResponse:
    d = DISTRIBUTIONS.get(dist)
    if d is None:
        raise SolverError("Distribusi tidak dikenal.")
    missing = [q.label for q in d.params if q.key not in params]
    if missing:
        raise SolverError("Parameter belum diisi: " + ", ".join(missing))
    vals = {q.key: float(params[q.key]) for q in d.params}
    err = d.validate(vals)
    if err:
        raise SolverError(err)
    rv = d.make(vals)
    mean, var = (float(v) for v in rv.stats(moments="mv"))
    param_latex = ",\\ ".join(rf"\text{{{q.label.split(' ')[0]}}} = {fmt(vals[q.key])}" for q in d.params)
    steps = [
        Step(
            title=f"Distribusi {d.title}",
            explanation="Rumus fungsi peluang dan domain nilai X.",
            latex=rf"{d.formula},\qquad {d.support}",
        ),
        Step(title="Parameter", latex=param_latex),
    ]
    need = {"pdf": ("x",), "cdf": ("x",), "sf": ("x",), "between": ("a", "b"), "ppf": ("p",)}
    if mode not in need:
        raise SolverError("Mode perhitungan tidak dikenal.")
    given = {"x": x, "a": a, "b": b, "p": p}
    for key in need[mode]:
        if given[key] is None:
            raise SolverError(f"Nilai {key} wajib diisi untuk mode ini.")
    shade: tuple[float, float] | None = None
    if mode == "pdf":
        value = float(rv.pmf(x) if d.discrete else rv.pdf(x))
        symbol = rf"P(X = {fmt(x)})" if d.discrete else rf"f({fmt(x)})"
        explanation = (
            "Peluang X tepat bernilai x."
            if d.discrete
            else "Nilai kepadatan (bukan peluang): untuk variabel kontinu P(X = x) = 0."
        )
        if d.discrete and not float(x).is_integer():
            raise SolverError("Untuk distribusi diskrit, x harus bilangan bulat.")
        point = x
    elif mode == "cdf":
        value = float(rv.cdf(x))
        symbol = rf"P(X \le {fmt(x)})"
        explanation = "Peluang kumulatif dari batas bawah domain sampai x."
        shade = (-np.inf, x)
        point = x
    elif mode == "sf":
        value = float(rv.sf(x))
        symbol = rf"P(X > {fmt(x)}) = 1 - F({fmt(x)})"
        explanation = "Peluang ekor kanan."
        shade = (x, np.inf)
        point = x
    elif mode == "between":
        if b < a:
            raise SolverError("Batas b harus ≥ a.")
        lower = rv.cdf(a - 1) if d.discrete else rv.cdf(a)
        value = float(rv.cdf(b) - lower)
        symbol = rf"P({fmt(a)} \le X \le {fmt(b)}) = F({fmt(b)}) - F({fmt(a - 1) if d.discrete else fmt(a)})"
        explanation = "Selisih dua nilai CDF." + (
            " Untuk diskrit, batas bawah memakai F(a − 1) agar a ikut terhitung." if d.discrete else ""
        )
        shade = (a, b)
        point = None
    else:  # ppf
        if not 0 < p < 1:
            raise SolverError("Peluang p harus di antara 0 dan 1.")
        value = float(rv.ppf(p))
        symbol = rf"F^{{-1}}({fmt(p)})"
        explanation = (
            "Nilai x terkecil dengan P(X ≤ x) ≥ p." if d.discrete else "Kuantil: nilai x sehingga P(X ≤ x) = p."
        )
        shade = (-np.inf, value)
        point = value
    steps.append(Step(title="Hasil perhitungan", explanation=explanation, latex=rf"{symbol} = {fmt(value, 6)}"))
    steps.append(
        Step(
            title="Rata-rata & varians distribusi",
            latex=rf"E[X] = {fmt(mean)},\quad Var(X) = {fmt(var)},\quad \sigma = {fmt(float(np.sqrt(var)) if np.isfinite(var) else float('nan'))}",
        )
    )
    return SolverResponse(
        result={"value": value, "mean": mean, "variance": var, "mode": mode},
        steps=steps,
        charts=[_chart(d, rv, shade, point)],
        summary=summary_items([("Hasil", value), ("E[X]", mean), ("Var(X)", var)]),
        conclusion=f"{d.title}: hasil = {fmt(value, 6)}.",
    )


def _chart(d: Distribution, rv: Any, shade: tuple[float, float] | None, point: float | None) -> Chart:
    lo, hi = float(rv.ppf(0.0005)), float(rv.ppf(0.9995))
    if d.discrete:
        xs = np.arange(int(np.floor(lo)), int(np.ceil(hi)) + 1)
        ys = rv.pmf(xs)
        colors = [
            "#ef4444"
            if shade and shade[0] <= v <= shade[1]
            else ("#f59e0b" if point is not None and v == point else "#6366f1")
            for v in xs
        ]
        traces = [{"type": "bar", "x": xs.tolist(), "y": ys.tolist(), "marker": {"color": colors}, "name": "P(X = x)"}]
        title = "Fungsi massa peluang (PMF)"
    else:
        if point is not None and np.isfinite(point):
            lo, hi = min(lo, point), max(hi, point)
        xs = np.linspace(lo, hi, 400)
        ys = rv.pdf(xs)
        traces = [{"type": "scatter", "mode": "lines", "x": xs.tolist(), "y": ys.tolist(), "name": "f(x)"}]
        if shade:
            mask = (xs >= shade[0]) & (xs <= shade[1])
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": xs[mask].tolist(),
                    "y": ys[mask].tolist(),
                    "fill": "tozeroy",
                    "name": "Peluang",
                    "line": {"color": "#ef4444"},
                }
            )
        if point is not None and np.isfinite(point):
            traces.append(
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": [point],
                    "y": [float(rv.pdf(point))],
                    "name": f"x = {fmt(point)}",
                    "marker": {"size": 10, "color": "#f59e0b"},
                }
            )
        title = "Fungsi kepadatan peluang (PDF)"
    return Chart(
        id="distribution",
        title=title,
        spec=plotly_figure(traces, f"{d.title} — {title}", xaxis={"title": {"text": "x"}}),
    )


# --------------------------------------------------------------------------- tabel statistik

_T_ALPHAS = [0.10, 0.05, 0.025, 0.01, 0.005]
_CHI_ALPHAS = [0.995, 0.99, 0.975, 0.95, 0.90, 0.10, 0.05, 0.025, 0.01, 0.005]
_DFS = [*range(1, 31), 40, 50, 60, 80, 100, 120]


def table(kind: str, alpha: float = 0.05) -> SolverResponse:
    if kind == "z":
        rows = []
        for i in range(35):
            z0 = i / 10
            rows.append([f"{z0:.1f}", *[round(float(stats.norm.cdf(z0 + j / 100)), 4) for j in range(10)]])
        t = NamedTable(
            title="Tabel distribusi normal baku: Φ(z) = P(Z ≤ z)",
            columns=["z", *[f".0{j}" for j in range(10)]],
            rows=rows,
        )
        note = "Baris = digit pertama z, kolom = digit kedua desimal. Contoh: Φ(1,96) di baris 1.9 kolom .06 = 0,9750."
    elif kind == "t":
        rows = [[df, *[round(float(stats.t.ppf(1 - a, df)), 4) for a in _T_ALPHAS]] for df in _DFS]
        rows.append(["∞", *[round(float(stats.norm.ppf(1 - a)), 4) for a in _T_ALPHAS]])
        t = NamedTable(
            title="Nilai kritis t: P(T > t) = α", columns=["df", *[f"α = {a}" for a in _T_ALPHAS]], rows=rows
        )
        note = "Untuk uji dua sisi dengan α total, gunakan kolom α/2."
    elif kind == "chi2":
        rows = [[df, *[round(float(stats.chi2.isf(a, df)), 4) for a in _CHI_ALPHAS]] for df in _DFS]
        t = NamedTable(
            title="Nilai kritis chi-square: P(χ² > x) = α",
            columns=["df", *[f"α = {a}" for a in _CHI_ALPHAS]],
            rows=rows,
        )
        note = "Kolom α besar (0,995 … 0,90) dipakai untuk batas bawah interval varians."
    elif kind == "f":
        if not 0 < alpha < 1:
            raise SolverError("α harus di antara 0 dan 1.")
        df1s = [*range(1, 11), 12, 15, 20, 30, 60]
        rows = [[df2, *[round(float(stats.f.isf(alpha, d1, df2)), 3) for d1 in df1s]] for df2 in _DFS]
        t = NamedTable(
            title=f"Nilai kritis F untuk α = {alpha}", columns=["df₂ \\ df₁", *[str(d) for d in df1s]], rows=rows
        )
        note = "Baris = df penyebut (df₂), kolom = df pembilang (df₁)."
    else:
        raise SolverError("Jenis tabel harus salah satu dari: z, t, chi2, f.")
    return SolverResponse(result={"kind": kind}, tables=[t], steps=[Step(title="Cara membaca tabel", explanation=note)])
