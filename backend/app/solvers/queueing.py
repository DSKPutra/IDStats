"""Teori antrian (Bab 17–18): model kelahiran-kematian M/M/s, kapasitas terbatas, populasi terbatas, M/G/1,
M/D/s & M/Eₖ/s, disiplin prioritas, jaringan Jackson, dan optimasi biaya jumlah server."""

from __future__ import annotations

import math

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step
from app.solvers._base import plotly_figure, summary_items


def _r(x: float) -> float:
    return float(round(x, 6)) if math.isfinite(x) else x


def _bd(lam_n, mu_n, n_max: int) -> np.ndarray:
    """Distribusi steady-state proses kelahiran-kematian: Cₙ = Π λ/μ."""
    c = [1.0]
    for n in range(1, n_max + 1):
        c.append(c[-1] * lam_n(n - 1) / mu_n(n))
    c = np.array(c)
    return c / c.sum()


def mms_metrics(lam: float, mu: float, s: int) -> dict:
    rho = lam / (s * mu)
    if rho >= 1:
        raise SolverError(f"Sistem tidak stabil: ρ = λ/(sμ) = {rho:.4f} ≥ 1. Tambah server atau percepat pelayanan.")
    a = lam / mu
    p0 = 1 / (sum(a**n / math.factorial(n) for n in range(s)) + a**s / (math.factorial(s) * (1 - rho)))
    lq = p0 * a**s * rho / (math.factorial(s) * (1 - rho) ** 2)
    wq = lq / lam
    w = wq + 1 / mu
    return {
        "rho": rho,
        "p0": p0,
        "lq": lq,
        "l": lam * w,
        "wq": wq,
        "w": w,
        "p_wait": p0 * a**s / (math.factorial(s) * (1 - rho)),
    }


def _pn_chart(pn: np.ndarray, title: str) -> Chart:
    return Chart(
        id="pn",
        title="Distribusi Pₙ",
        spec=plotly_figure(
            [{"type": "bar", "x": list(range(len(pn))), "y": pn.tolist(), "name": "Pₙ"}],
            title,
            xaxis={"title": {"text": "n (pelanggan dalam sistem)"}},
            yaxis={"title": {"text": "Pₙ"}},
        ),
    )


def _response(
    model: str,
    m: dict,
    pn: np.ndarray | None,
    steps: list[Step],
    extra_summary: list | None = None,
    warnings: list[str] | None = None,
) -> SolverResponse:
    labels = [
        ("ρ (utilisasi server)", "rho"),
        ("P₀", "p0"),
        ("L (pelanggan dalam sistem)", "l"),
        ("Lq (pelanggan dalam antrian)", "lq"),
        ("W (waktu dalam sistem)", "w"),
        ("Wq (waktu menunggu di antrian)", "wq"),
    ]
    summary = [(label, _r(m[k])) for label, k in labels if k in m] + (extra_summary or [])
    tables = [
        NamedTable(
            title="Ukuran kinerja",
            columns=["Ukuran", "Nilai"],
            rows=[[label, _r(m[k])] for label, k in labels if k in m],
        )
    ]
    charts = []
    if pn is not None:
        tables.append(
            NamedTable(
                title="Distribusi jumlah pelanggan",
                columns=["n", "Pₙ", "P(N ≤ n)"],
                rows=[[n, _r(p), _r(c)] for n, (p, c) in enumerate(zip(pn, np.cumsum(pn), strict=True))],
            )
        )
        charts.append(_pn_chart(pn, f"Distribusi steady-state jumlah pelanggan ({model})"))
    return SolverResponse(
        result=dict(m) | ({"pn": pn.tolist()} if pn is not None else {}),
        steps=steps,
        tables=tables,
        charts=charts,
        summary=summary_items(summary),
        warnings=warnings or [],
        conclusion=f"{model}: L = {m['l']:.4f}, Lq = {m['lq']:.4f}, W = {m['w']:.4f}, Wq = {m['wq']:.4f}.",
    )


_LITTLE = Step(title="Rumus Little", latex=r"L = \lambda W,\qquad L_q = \lambda W_q,\qquad W = W_q + \frac{1}{\mu}")


def mms(lam: float, mu: float, s: int, n_show: int = 15) -> SolverResponse:
    if lam <= 0 or mu <= 0 or s < 1:
        raise SolverError("λ dan μ harus positif dan s ≥ 1.")
    m = mms_metrics(lam, mu, s)
    pn = np.array(
        [
            m["p0"]
            * ((lam / mu) ** n / math.factorial(n) if n <= s else (lam / mu) ** n / (math.factorial(s) * s ** (n - s)))
            for n in range(n_show + 1)
        ]
    )
    steps = [
        Step(
            title="Model M/M/s",
            explanation=f"Kedatangan Poisson (λ = {lam:g}), waktu pelayanan eksponensial (μ = {mu:g}), s = {s} server, antrian tak terbatas.",
            latex=rf"\rho = \frac{{\lambda}}{{s\mu}} = {m['rho']:.4f} < 1",
        ),
        Step(
            title="Peluang sistem kosong",
            latex=r"P_0 = \left[\sum_{n=0}^{s-1}\frac{(\lambda/\mu)^n}{n!} + \frac{(\lambda/\mu)^s}{s!}\frac{1}{1-\rho}\right]^{-1} = "
            + f"{m['p0']:.6f}",
        ),
        Step(
            title="Panjang antrian", latex=r"L_q = \frac{P_0 (\lambda/\mu)^s \rho}{s!(1-\rho)^2} = " + f"{m['lq']:.6f}"
        ),
        _LITTLE,
    ]
    return _response(f"M/M/{s}", m, pn, steps, [("P(pelanggan harus menunggu)", _r(m["p_wait"]))])


def mmsk(lam: float, mu: float, s: int, k: int) -> SolverResponse:
    if lam <= 0 or mu <= 0 or s < 1 or k < s:
        raise SolverError("Syarat: λ, μ > 0, s ≥ 1, dan kapasitas K ≥ s.")
    pn = _bd(lambda n: lam, lambda n: min(n, s) * mu, k)
    n = np.arange(k + 1)
    l_sys = float((n * pn).sum())
    lq = float((np.maximum(n - s, 0) * pn).sum())
    lam_eff = lam * (1 - pn[-1])
    m = {"rho": lam_eff / (s * mu), "p0": float(pn[0]), "l": l_sys, "lq": lq, "w": l_sys / lam_eff, "wq": lq / lam_eff}
    steps = [
        Step(
            title=f"Model M/M/{s}/{k} (kapasitas terbatas)",
            explanation=f"Paling banyak K = {k} pelanggan dalam sistem; pelanggan yang datang saat penuh ditolak (λₙ = 0 untuk n ≥ K).",
        ),
        Step(
            title="Proses kelahiran-kematian",
            latex=r"C_n = \prod_{i=0}^{n-1}\frac{\lambda_i}{\mu_{i+1}},\quad P_n = C_n P_0,\quad P_0 = \Big(\sum_{n=0}^{K} C_n\Big)^{-1}",
        ),
        Step(
            title="Laju kedatangan efektif",
            latex=rf"\bar{{\lambda}} = \lambda (1 - P_K) = {lam:g}(1 - {pn[-1]:.4f}) = {lam_eff:.4f}",
            explanation="Rumus Little memakai laju kedatangan efektif.",
        ),
        _LITTLE,
    ]
    return _response(
        f"M/M/{s}/{k}", m, pn, steps, [("P(sistem penuh) = P_K", _r(float(pn[-1]))), ("λ efektif", _r(lam_eff))]
    )


def finite_source(lam: float, mu: float, s: int, population: int) -> SolverResponse:
    if lam <= 0 or mu <= 0 or s < 1 or population < 1:
        raise SolverError("Syarat: λ, μ > 0, s ≥ 1, populasi N ≥ 1.")
    big_n = population
    pn = _bd(lambda n: (big_n - n) * lam, lambda n: min(n, s) * mu, big_n)
    n = np.arange(big_n + 1)
    l_sys = float((n * pn).sum())
    lq = float((np.maximum(n - s, 0) * pn).sum())
    lam_eff = lam * (big_n - l_sys)
    m = {"rho": lam_eff / (s * mu), "p0": float(pn[0]), "l": l_sys, "lq": lq, "w": l_sys / lam_eff, "wq": lq / lam_eff}
    steps = [
        Step(
            title=f"Model populasi terbatas (N = {big_n})",
            explanation=f"Setiap anggota populasi di luar sistem datang dengan laju λ = {lam:g}, sehingga λₙ = (N − n)λ.",
            latex=r"\lambda_n = (N - n)\lambda,\quad \mu_n = \min(n, s)\mu",
        ),
        Step(title="Laju kedatangan efektif", latex=rf"\bar{{\lambda}} = \lambda(N - L) = {lam_eff:.4f}"),
        _LITTLE,
    ]
    return _response(f"Populasi terbatas M/M/{s}//{big_n}", m, pn, steps, [("λ efektif", _r(lam_eff))])


def mg1(lam: float, mu: float, sigma: float) -> SolverResponse:
    rho = lam / mu
    if rho >= 1:
        raise SolverError(f"Sistem tidak stabil: ρ = {rho:.4f} ≥ 1.")
    lq = (lam**2 * sigma**2 + rho**2) / (2 * (1 - rho))
    m = {"rho": rho, "p0": 1 - rho, "lq": lq, "wq": lq / lam}
    m["w"] = m["wq"] + 1 / mu
    m["l"] = lam * m["w"]
    steps = [
        Step(
            title="Model M/G/1",
            explanation=f"Waktu pelayanan berdistribusi umum dengan rata-rata 1/μ = {1 / mu:g} dan simpangan baku σ = {sigma:g}.",
        ),
        Step(
            title="Rumus Pollaczek-Khintchine",
            latex=r"L_q = \frac{\lambda^2\sigma^2 + \rho^2}{2(1-\rho)} = " + f"{lq:.6f}",
            explanation="Lq bertambah dengan variansi waktu pelayanan: mengurangi variabilitas mengurangi antrian.",
        ),
        _LITTLE,
    ]
    return _response("M/G/1", m, None, steps)


def mgs_approx(lam: float, mu: float, s: int, cs2: float, label: str) -> SolverResponse:
    base = mms_metrics(lam, mu, s)
    if s == 1:
        res = mg1(lam, mu, math.sqrt(cs2) / mu)
        res.steps[0] = Step(
            title=f"Model {label}", explanation=f"Untuk s = 1, rumus Pollaczek-Khintchine eksak dengan σ² = {cs2:g}/μ²."
        )
        res.conclusion = res.conclusion.replace("M/G/1", label)
        return res
    lq = base["lq"] * (1 + cs2) / 2
    m = {"rho": base["rho"], "p0": base["p0"], "lq": lq, "wq": lq / lam}
    m["w"] = m["wq"] + 1 / mu
    m["l"] = lam * m["w"]
    steps = [
        Step(
            title=f"Model {label}",
            explanation=f"Koefisien variasi kuadrat waktu pelayanan C²ₛ = {cs2:g} (konstan: 0; Erlang-k: 1/k).",
        ),
        Step(
            title="Aproksimasi Allen-Cunneen",
            latex=r"L_q(M/G/s) \approx L_q(M/M/s)\cdot\frac{1 + C_s^2}{2} = "
            + f"{base['lq']:.6f} \\cdot {(1 + cs2) / 2:g} = {lq:.6f}",
            explanation="Hillier menyajikan hasil M/D/s dan M/Eₖ/s dalam bentuk grafik; di sini dipakai aproksimasi standar ini (eksak untuk s = 1).",
        ),
        _LITTLE,
    ]
    return _response(label, m, None, steps, warnings=["Nilai untuk s > 1 adalah aproksimasi."])


def priority(lam: list[float], mu: float, s: int, preemptive: bool) -> SolverResponse:
    if not lam or any(x <= 0 for x in lam) or mu <= 0 or s < 1:
        raise SolverError("Isi laju kedatangan tiap kelas (positif), μ > 0, s ≥ 1.")
    total = sum(lam)
    if total >= s * mu:
        raise SolverError("Sistem tidak stabil: Σλ ≥ sμ.")
    rows = []
    ws = []
    if not preemptive:
        r = s * mu
        a_coef = (
            math.factorial(s)
            * (r - total)
            / ((total / mu) ** s)
            * sum((total / mu) ** j / math.factorial(j) for j in range(s))
            + r
        )
        cum = 0.0
        for k, lk in enumerate(lam, start=1):
            b_prev = 1 - cum / r
            cum += lk
            b_k = 1 - cum / r
            wk = 1 / (a_coef * b_prev * b_k) + 1 / mu
            ws.append(wk)
            rows.append([f"Kelas {k}", lk, _r(wk), _r(wk - 1 / mu), _r(lk * wk), _r(lk * (wk - 1 / mu))])
        formula = r"W_k = \frac{1}{A B_{k-1} B_k} + \frac{1}{\mu},\ A = s!\frac{s\mu - \lambda}{r^s}\sum_{j=0}^{s-1}\frac{r^j}{j!} + s\mu,\ B_k = 1 - \frac{\sum_{i \le k}\lambda_i}{s\mu}"
        title = "Prioritas nonpreemptive (M/M/s)"
    else:
        if s != 1:
            raise SolverError("Rumus prioritas preemptive di sini untuk s = 1.")
        cum = 0.0
        for k, lk in enumerate(lam, start=1):
            b_prev = 1 - cum / mu
            cum += lk
            b_k = 1 - cum / mu
            wk = (1 / mu) / (b_prev * b_k)
            ws.append(wk)
            rows.append([f"Kelas {k}", lk, _r(wk), _r(wk - 1 / mu), _r(lk * wk), _r(lk * (wk - 1 / mu))])
        formula = r"W_k = \frac{1/\mu}{B_{k-1}B_k}"
        title = "Prioritas preemptive (M/M/1)"
    table = NamedTable(
        title="Kinerja per kelas prioritas (kelas 1 = prioritas tertinggi)",
        columns=["Kelas", "λₖ", "Wₖ", "Wqₖ", "Lₖ", "Lqₖ"],
        rows=rows,
    )
    return SolverResponse(
        result={"w": ws},
        steps=[
            Step(
                title=title,
                latex=formula,
                explanation="Pelanggan berprioritas lebih tinggi dilayani lebih dulu"
                + (
                    " dan dapat menyela pelayanan kelas yang lebih rendah."
                    if preemptive
                    else "; pelayanan yang sedang berlangsung tidak disela."
                ),
            ),
            Step(title="Hasil", table=table),
        ],
        tables=[table],
        charts=[
            Chart(
                id="priority",
                title="Waktu dalam sistem",
                spec=plotly_figure(
                    [{"type": "bar", "x": [r[0] for r in rows], "y": ws, "name": "Wₖ"}],
                    "Waktu harapan dalam sistem per kelas",
                ),
            )
        ],
        summary=summary_items([(f"W kelas {k + 1}", _r(w)) for k, w in enumerate(ws)]),
        conclusion="Waktu harapan dalam sistem: "
        + ", ".join(f"kelas {k + 1} = {w:.4f}" for k, w in enumerate(ws))
        + ".",
    )


def jackson(
    external: list[float], routing: list[list[float]], servers: list[int], mu: list[float], names: list[str] | None
) -> SolverResponse:
    a = np.array(external, dtype=float)
    p = np.array(routing, dtype=float)
    k = a.size
    if p.shape != (k, k) or len(servers) != k or len(mu) != k:
        raise SolverError(
            f"Jaringan dengan {k} stasiun memerlukan matriks perutean {k}×{k}, {k} jumlah server, dan {k} laju pelayanan."
        )
    if np.any(p.sum(axis=1) > 1 + 1e-9):
        raise SolverError("Jumlah peluang perutean dari setiap stasiun tidak boleh melebihi 1.")
    lam = np.linalg.solve(np.eye(k) - p.T, a)
    labels = names if names and len(names) == k else [f"Stasiun {i + 1}" for i in range(k)]
    rows = []
    total_l = 0.0
    for i in range(k):
        m = mms_metrics(float(lam[i]), mu[i], servers[i])
        total_l += m["l"]
        rows.append([labels[i], _r(lam[i]), servers[i], mu[i], _r(m["rho"]), _r(m["l"]), _r(m["w"])])
    w_total = total_l / a.sum()
    table = NamedTable(
        title="Kinerja tiap stasiun", columns=["Stasiun", "λᵢ (total)", "sᵢ", "μᵢ", "ρᵢ", "Lᵢ", "Wᵢ"], rows=rows
    )
    return SolverResponse(
        result={"lambda": lam.tolist(), "L": total_l, "W": w_total},
        steps=[
            Step(
                title="Persamaan aliran (traffic equations)",
                latex=r"\lambda_j = a_j + \sum_i \lambda_i p_{ij}",
                explanation="Selesaikan laju kedatangan total setiap stasiun.",
                table=table,
            ),
            Step(
                title="Teorema Jackson",
                explanation="Setiap stasiun berperilaku seperti antrian M/M/sᵢ independen dengan laju λⱼ.",
                latex=rf"L = \sum L_i = {total_l:.4f},\quad W = \frac{{L}}{{\sum a_j}} = {w_total:.4f}",
            ),
        ],
        tables=[table],
        summary=summary_items([("L total jaringan", _r(total_l)), ("W rata-rata per pelanggan", _r(w_total))]),
        conclusion=f"Jaringan Jackson: L total = {total_l:.4f}, waktu rata-rata dalam jaringan W = {w_total:.4f}.",
    )


def cost_optimization(
    lam: float, mu: float, server_cost: float, wait_cost: float, max_extra: int = 8
) -> SolverResponse:
    if lam <= 0 or mu <= 0:
        raise SolverError("λ dan μ harus positif.")
    s_min = math.floor(lam / mu) + 1
    rows = []
    best = None
    for s in range(s_min, s_min + max_extra + 1):
        m = mms_metrics(lam, mu, s)
        tc = server_cost * s + wait_cost * m["l"]
        rows.append([s, _r(m["l"]), _r(server_cost * s), _r(wait_cost * m["l"]), _r(tc)])
        if best is None or tc < best[1]:
            best = (s, tc)
    table = NamedTable(
        title="Biaya total per jumlah server",
        columns=["s", "L", "Biaya layanan Cs·s", "Biaya menunggu Cw·L", "Biaya total"],
        rows=rows,
    )
    return SolverResponse(
        result={"best_s": best[0], "best_cost": best[1]},
        steps=[
            Step(
                title="Fungsi biaya total",
                latex=r"E[TC] = C_s\, s + C_w\, L(s)",
                explanation="Biaya layanan naik linier terhadap jumlah server, sedangkan biaya menunggu turun karena antrian memendek.",
            ),
            Step(title="Evaluasi setiap s", table=table),
        ],
        tables=[table],
        charts=[
            Chart(
                id="cost",
                title="Biaya total",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "lines+markers",
                            "x": [r[0] for r in rows],
                            "y": [r[2] for r in rows],
                            "name": "Biaya layanan",
                        },
                        {
                            "type": "scatter",
                            "mode": "lines+markers",
                            "x": [r[0] for r in rows],
                            "y": [r[3] for r in rows],
                            "name": "Biaya menunggu",
                        },
                        {
                            "type": "scatter",
                            "mode": "lines+markers",
                            "x": [r[0] for r in rows],
                            "y": [r[4] for r in rows],
                            "name": "Biaya total",
                            "line": {"width": 4},
                        },
                    ],
                    "Trade-off biaya layanan vs biaya menunggu",
                    xaxis={"title": {"text": "Jumlah server s"}},
                ),
            )
        ],
        summary=summary_items([("Jumlah server optimal", best[0]), ("Biaya total minimum", _r(best[1]))]),
        conclusion=f"Jumlah server optimal s* = {best[0]} dengan biaya total harapan {best[1]:.4f} per satuan waktu.",
    )
