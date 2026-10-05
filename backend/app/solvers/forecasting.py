"""Peramalan (Bab 20): last value, rata-rata bergerak, exponential smoothing, penyesuaian musiman, Holt (tren),
ukuran galat (MAD, MSE, MAPE), Box-Jenkins ARIMA(p, d, q), dan regresi linier kausal/tren."""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import minimize

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import as_finite_array, plotly_figure, summary_items


def _r(x: float) -> float:
    return float(round(x, 6)) if x is not None and math.isfinite(x) else None


def _errors(actual: np.ndarray, fc: np.ndarray) -> dict:
    mask = ~np.isnan(fc)
    e = actual[mask] - fc[mask]
    if e.size == 0:
        return {"mad": math.nan, "mse": math.nan, "mape": math.nan, "n": 0}
    nz = actual[mask] != 0
    return {
        "mad": float(np.mean(np.abs(e))),
        "mse": float(np.mean(e**2)),
        "mape": float(np.mean(np.abs(e[nz] / actual[mask][nz])) * 100) if nz.any() else math.nan,
        "n": int(e.size),
    }


def _response(
    name: str, y: np.ndarray, fc: np.ndarray, future: list[float], steps: list[Step], extra: dict | None = None
) -> SolverResponse:
    err = _errors(y, fc)
    t = list(range(1, len(y) + 1))
    tf = list(range(len(y) + 1, len(y) + 1 + len(future)))
    rows = [
        [i + 1, _r(y[i]), _r(fc[i]) if not np.isnan(fc[i]) else "—", _r(y[i] - fc[i]) if not np.isnan(fc[i]) else "—"]
        for i in range(len(y))
    ]
    rows += [[k, "—", _r(v), "—"] for k, v in zip(tf, future, strict=True)]
    table = NamedTable(title="Data aktual & ramalan", columns=["Periode", "Aktual", "Ramalan", "Galat"], rows=rows)
    err_table = NamedTable(
        title="Ukuran galat ramalan",
        columns=["Ukuran", "Nilai"],
        rows=[
            ["MAD (mean absolute deviation)", _r(err["mad"])],
            ["MSE (mean squared error)", _r(err["mse"])],
            ["MAPE (%)", _r(err["mape"])],
            ["Jumlah ramalan dinilai", err["n"]],
        ],
    )
    steps = steps + [
        Step(
            title="Ukuran galat",
            latex=r"MAD = \frac{1}{n}\sum|y_t - F_t|,\quad MSE = \frac{1}{n}\sum (y_t - F_t)^2,\quad MAPE = \frac{100}{n}\sum\left|\frac{y_t - F_t}{y_t}\right|",
            table=err_table,
        )
    ]
    chart = Chart(
        id="forecast",
        title="Ramalan",
        spec=plotly_figure(
            [
                {"type": "scatter", "mode": "lines+markers", "x": t, "y": y.tolist(), "name": "Aktual"},
                {
                    "type": "scatter",
                    "mode": "lines+markers",
                    "x": t + tf,
                    "y": [None if np.isnan(v) else float(v) for v in fc] + list(map(float, future)),
                    "name": "Ramalan",
                    "line": {"dash": "dash"},
                },
            ],
            f"Peramalan: {name}",
            xaxis={"title": {"text": "Periode"}},
        ),
    )
    return SolverResponse(
        result={
            "forecast": [None if np.isnan(v) else float(v) for v in fc],
            "future": list(map(float, future)),
            **{k: _r(v) for k, v in err.items() if k != "n"},
            **(extra or {}),
        },
        steps=steps,
        tables=[table, err_table],
        charts=[chart],
        summary=summary_items(
            [
                ("Ramalan periode berikutnya", _r(future[0]) if future else "—"),
                ("MAD", _r(err["mad"])),
                ("MSE", _r(err["mse"])),
                ("MAPE (%)", _r(err["mape"])),
            ]
        ),
        conclusion=f"{name}: ramalan periode berikutnya ≈ {future[0]:.4f}; MAD = {err['mad']:.4f}."
        if future
        else f"{name}: MAD = {err['mad']:.4f}.",
    )


def _series(data: list[float], minimum: int = 2) -> np.ndarray:
    y = as_finite_array(data, "Deret waktu")
    if y.size < minimum:
        raise SolverError(f"Deret waktu minimal {minimum} data.")
    return y


def last_value(data: list[float], horizon: int) -> SolverResponse:
    y = _series(data)
    fc = np.r_[np.nan, y[:-1]]
    return _response(
        "Last value (naive)",
        y,
        fc,
        [float(y[-1])] * horizon,
        [
            Step(
                title="Metode last value",
                latex=r"F_{t+1} = y_t",
                explanation="Ramalan = nilai aktual terakhir. Cocok bila kondisi berubah cepat dan acak.",
            )
        ],
    )


def moving_average(data: list[float], n: int, horizon: int) -> SolverResponse:
    y = _series(data, n + 1)
    if n < 1:
        raise SolverError("Jumlah periode rata-rata bergerak minimal 1.")
    fc = np.array([np.nan] * n + [float(y[t - n : t].mean()) for t in range(n, len(y))])
    nxt = float(y[-n:].mean())
    return _response(
        f"Rata-rata bergerak (n = {n})",
        y,
        fc,
        [nxt] * horizon,
        [
            Step(
                title="Rata-rata bergerak",
                latex=rf"F_{{t+1}} = \frac{{1}}{{{n}}}\sum_{{i=t-{n}+1}}^{{t}} y_i",
                explanation="Rata-rata n periode terakhir; makin besar n makin halus tetapi makin lambat merespons perubahan.",
            )
        ],
    )


def exp_smoothing(data: list[float], alpha: float, initial: float | None, horizon: int) -> SolverResponse:
    y = _series(data)
    if not 0 < alpha <= 1:
        raise SolverError("α harus di antara 0 dan 1.")
    f = initial if initial is not None else float(y[0])
    fc = []
    for v in y:
        fc.append(f)
        f = alpha * v + (1 - alpha) * f
    return _response(
        f"Exponential smoothing (α = {alpha:g})",
        y,
        np.array(fc),
        [f] * horizon,
        [
            Step(
                title="Exponential smoothing",
                latex=rf"F_{{t+1}} = \alpha y_t + (1-\alpha)F_t,\quad \alpha = {alpha:g},\ F_1 = {fc[0]:g}",
                explanation="Rata-rata berbobot yang bobotnya menurun secara eksponensial untuk data yang lebih lama.",
            )
        ],
    )


def holt(data: list[float], alpha: float, beta: float, horizon: int) -> SolverResponse:
    y = _series(data, 3)
    if not (0 < alpha <= 1 and 0 < beta <= 1):
        raise SolverError("α dan β harus di antara 0 dan 1.")
    level, trend = float(y[0]), float(y[1] - y[0])
    fc = [np.nan]
    rows = [[1, _r(y[0]), _r(level), _r(trend), "—"]]
    for t in range(1, len(y)):
        f = level + trend
        fc.append(f)
        new_level = alpha * y[t] + (1 - alpha) * (level + trend)
        trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
        rows.append([t + 1, _r(y[t]), _r(level), _r(trend), _r(f)])
    future = [level + k * trend for k in range(1, horizon + 1)]
    steps = [
        Step(
            title="Exponential smoothing dengan tren (Holt)",
            latex=r"L_t = \alpha y_t + (1-\alpha)(L_{t-1} + T_{t-1}),\quad T_t = \beta(L_t - L_{t-1}) + (1-\beta)T_{t-1},\quad F_{t+k} = L_t + kT_t",
            explanation=f"α = {alpha:g}, β = {beta:g}. Inisialisasi L₁ = y₁, T₁ = y₂ − y₁.",
        ),
        Step(title="Iterasi", table=Table(columns=["t", "yₜ", "Lₜ", "Tₜ", "Fₜ"], rows=rows)),
    ]
    return _response(f"Holt (α = {alpha:g}, β = {beta:g})", y, np.array(fc), future, steps)


def seasonal(data: list[float], season: int, method: str, alpha: float, horizon: int) -> SolverResponse:
    y = _series(data, 2 * season)
    if season < 2:
        raise SolverError("Panjang musim minimal 2.")
    k = len(y) // season
    trimmed = y[: k * season].reshape(k, season)
    factors = trimmed.mean(axis=0) / trimmed.mean()
    adj = y / np.resize(factors, len(y))
    if method == "last":
        base = np.r_[np.nan, adj[:-1]]
        nxt_base = adj[-1]
    else:
        f = adj[0]
        base_list = []
        for v in adj:
            base_list.append(f)
            f = alpha * v + (1 - alpha) * f
        base, nxt_base = np.array(base_list), f
    fc = base * np.resize(factors, len(y))
    future = [float(nxt_base * factors[(len(y) + h) % season]) for h in range(horizon)]
    steps = [
        Step(
            title="Faktor musiman",
            explanation="Faktor musiman = rata-rata periode musim tersebut ÷ rata-rata keseluruhan.",
            table=Table(columns=["Musim", "Faktor"], rows=[[i + 1, _r(v)] for i, v in enumerate(factors)]),
        ),
        Step(
            title="Data disesuaikan musim",
            latex=r"y_t^{adj} = \frac{y_t}{\text{faktor musiman}},\qquad F_{t+1} = F_{t+1}^{adj}\times\text{faktor musiman}",
            explanation="Ramalkan deret yang sudah disesuaikan musim ("
            + ("last value" if method == "last" else f"exponential smoothing α = {alpha:g}")
            + "), lalu kalikan kembali dengan faktor musiman.",
        ),
    ]
    return _response("Penyesuaian musiman", y, fc, future, steps, {"seasonal_factors": factors.tolist()})


def trend_regression(
    data: list[float], x: list[float] | None, future_x: list[float] | None, horizon: int
) -> SolverResponse:
    y = _series(data, 3)
    xs = np.arange(1, len(y) + 1, dtype=float) if not x else as_finite_array(x, "Variabel x")
    if xs.size != y.size:
        raise SolverError("Jumlah data x dan y harus sama.")
    b1 = float(((xs - xs.mean()) * (y - y.mean())).sum() / ((xs - xs.mean()) ** 2).sum())
    b0 = float(y.mean() - b1 * xs.mean())
    fc = b0 + b1 * xs
    fx = list(future_x) if future_x else list(np.arange(len(y) + 1, len(y) + 1 + horizon, dtype=float))
    future = [b0 + b1 * v for v in fx]
    label = "Regresi tren linier" if not x else "Regresi linier kausal"
    return _response(
        label,
        y,
        fc,
        future,
        [
            Step(
                title=label,
                latex=rf"\hat{{y}} = a + bx = {b0:.4f} {'+' if b1 >= 0 else '-'} {abs(b1):.4f}x",
                explanation="Koefisien dengan metode kuadrat terkecil; x = indeks waktu (tren) atau variabel penjelas (kausal).",
            )
        ],
        {"intercept": b0, "slope": b1},
    )


# --------------------------------------------------------------------------- ARIMA


def _css(params: np.ndarray, w: np.ndarray, p: int, q: int) -> tuple[float, np.ndarray]:
    c = params[0]
    phi = params[1 : 1 + p]
    theta = params[1 + p : 1 + p + q]
    e = np.zeros_like(w)
    for t in range(len(w)):
        pred = c
        for i in range(p):
            if t - i - 1 >= 0:
                pred += phi[i] * w[t - i - 1]
        for j in range(q):
            if t - j - 1 >= 0:
                pred += theta[j] * e[t - j - 1]
        e[t] = w[t] - pred
    start = p
    return float((e[start:] ** 2).sum()), e


def arima(data: list[float], p: int, d: int, q: int, horizon: int) -> SolverResponse:
    y = _series(data, max(8, p + q + d + 4))
    if not (0 <= p <= 5 and 0 <= d <= 2 and 0 <= q <= 5):
        raise SolverError("Gunakan 0 ≤ p ≤ 5, 0 ≤ d ≤ 2, 0 ≤ q ≤ 5.")
    w = np.diff(y, n=d) if d else y.copy()
    x0 = np.r_[w.mean() * (1 - 0.1 * p), np.full(p, 0.1), np.full(q, 0.1)]
    res = minimize(
        lambda prm: _css(prm, w, p, q)[0], x0, method="L-BFGS-B", bounds=[(None, None)] + [(-0.99, 0.99)] * (p + q)
    )
    params = res.x
    sse, e = _css(params, w, p, q)
    c, phi, theta = params[0], params[1 : 1 + p], params[1 + p :]
    # ramalan deret terdiferensiasi
    w_ext, e_ext = list(w), list(e)
    for _ in range(horizon):
        pred = c + sum(phi[i] * w_ext[-i - 1] for i in range(p)) + sum(theta[j] * e_ext[-j - 1] for j in range(q))
        w_ext.append(pred)
        e_ext.append(0.0)
    w_future = np.array(w_ext[len(w) :])
    # integrasi balik
    future = w_future
    if d:
        hist = [y]
        for _ in range(d):
            hist.append(np.diff(hist[-1]))
        for level in range(d - 1, -1, -1):
            future = hist[level][-1] + np.cumsum(future)
    # nilai fitted: ŷₜ = yₜ − εₜ (diferensiasi linier dengan koefisien yₜ = 1)
    fitted = np.r_[[np.nan] * d, y[d:] - e].astype(float)
    fitted[d : d + p] = np.nan
    sigma2 = sse / max(1, len(w) - p - (p + q + 1))
    k = p + q + 1
    aic = len(w) * math.log(sse / len(w)) + 2 * k
    coef_rows = (
        [["Konstanta c", _r(c)]]
        + [[f"φ{i + 1} (AR)", _r(v)] for i, v in enumerate(phi)]
        + [[f"θ{j + 1} (MA)", _r(v)] for j, v in enumerate(theta)]
    )
    acf = [1.0] + [float(np.corrcoef(w[:-lag], w[lag:])[0, 1]) for lag in range(1, min(12, len(w) // 2))]
    steps = [
        Step(
            title="Identifikasi",
            explanation=f"Diferensiasi d = {d} kali agar deret stasioner. ACF deret terdiferensiasi membantu memilih q, PACF membantu memilih p.",
            table=Table(columns=["Lag", "ACF"], rows=[[i, _r(v)] for i, v in enumerate(acf)]),
        ),
        Step(
            title=f"Estimasi ARIMA({p}, {d}, {q})",
            latex=r"w_t = c + \sum_{i=1}^{p}\phi_i w_{t-i} + \varepsilon_t + \sum_{j=1}^{q}\theta_j \varepsilon_{t-j},\quad w_t = \nabla^d y_t",
            explanation="Parameter diestimasi dengan conditional sum of squares (meminimumkan jumlah kuadrat galat).",
            table=Table(columns=["Parameter", "Estimasi"], rows=coef_rows),
        ),
        Step(
            title="Diagnostik",
            latex=rf"\hat{{\sigma}}^2 = {sigma2:.4f},\quad AIC \approx {aic:.4f}",
            explanation="Pilih model dengan AIC lebih kecil; residual sebaiknya menyerupai white noise.",
        ),
    ]
    out = _response(
        f"ARIMA({p},{d},{q})",
        y,
        fitted,
        [float(v) for v in future],
        steps,
        {"params": params.tolist(), "aic": aic, "sigma2": sigma2},
    )
    out.charts.append(
        Chart(
            id="acf",
            title="ACF",
            spec=plotly_figure(
                [{"type": "bar", "x": list(range(len(acf))), "y": acf, "name": "ACF"}],
                "Autokorelasi deret terdiferensiasi",
                xaxis={"title": {"text": "Lag"}},
            ),
        )
    )
    return out
