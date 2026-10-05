"""Simulasi (Bab 22): pembangkit bilangan acak kongruensial (LCG), inverse transform & acceptance-rejection,
simulasi Monte Carlo umum (+ antithetic variates), simulasi antrian dan persediaan dengan analisis output (CI)."""

from __future__ import annotations

import heapq
import math
import re

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items
from app.solvers.expr import Expr
from app.solvers.queueing import mms_metrics


def _r(x: float) -> float:
    return float(round(x, 6))


def _ci(values: np.ndarray, conf: float = 0.95) -> tuple[float, float, float]:
    n = values.size
    mean = float(values.mean())
    if n < 2:
        return mean, mean, mean
    half = float(stats.t.ppf(0.5 + conf / 2, n - 1) * values.std(ddof=1) / math.sqrt(n))
    return mean, mean - half, mean + half


def _hist(values: np.ndarray, title: str, xlab: str) -> Chart:
    return Chart(
        id="hist",
        title="Histogram",
        spec=plotly_figure(
            [{"type": "histogram", "x": values.tolist(), "nbinsx": 30, "name": "Frekuensi"}],
            title,
            xaxis={"title": {"text": xlab}},
            bargap=0.05,
        ),
    )


# --------------------------------------------------------------------------- LCG


def lcg(a: int, c: int, m: int, seed: int, n: int) -> SolverResponse:
    if m <= 1 or not 0 < a < m or not 0 <= c < m or not 0 <= seed < m:
        raise SolverError("Syarat: m > 1, 0 < a < m, 0 ≤ c < m, 0 ≤ x₀ < m.")
    if not 1 <= n <= 5000:
        raise SolverError("Jumlah bilangan 1–5000.")
    xs = [seed]
    for _ in range(n):
        xs.append((a * xs[-1] + c) % m)
    seq = xs[1:]
    u = np.array(seq) / m
    # panjang periode
    seen = {}
    x, period = seed, None
    for k in range(min(m, 200000) + 1):
        if x in seen:
            period = k - seen[x]
            break
        seen[x] = k
        x = (a * x + c) % m
    bins = 10
    obs, _ = np.histogram(u, bins=bins, range=(0, 1))
    chi2 = float(((obs - n / bins) ** 2 / (n / bins)).sum())
    p = float(stats.chi2.sf(chi2, bins - 1))
    rows = [[i + 1, xs[i], f"({a}·{xs[i]} + {c}) mod {m}", seq[i], _r(u[i])] for i in range(min(n, 30))]
    table = NamedTable(
        title="Barisan bilangan acak", columns=["n", "xₙ₋₁", "Perhitungan", "xₙ", "uₙ = xₙ/m"], rows=rows
    )
    return SolverResponse(
        result={"numbers": seq[:1000], "uniform": u[:1000].tolist(), "period": period, "chi2": chi2, "p_value": p},
        steps=[
            Step(
                title="Metode kongruensial",
                latex=rf"x_{{n+1}} = (a x_n + c) \bmod m,\quad a = {a},\ c = {c},\ m = {m},\ x_0 = {seed}",
                explanation="c = 0: kongruensial multiplikatif; c > 0: kongruensial campuran. Bilangan acak seragam u = x/m.",
            ),
            Step(title="Barisan (30 pertama)", table=table),
            Step(
                title="Periode & uji keseragaman",
                explanation=f"Periode barisan = {period if period else 'lebih dari 200.000'}. Uji chi-square 10 kelas: χ² = {chi2:.4f}, p-value = {p:.4f} ({'tidak ada bukti tidak seragam' if p >= 0.05 else 'tidak seragam pada α = 0,05'}).",
            ),
        ],
        tables=[table],
        charts=[_hist(u, "Histogram bilangan acak seragam", "u")],
        summary=summary_items(
            [
                ("Periode", period or ">200000"),
                ("Rata-rata u (harapan 0,5)", _r(float(u.mean()))),
                ("χ² keseragaman", _r(chi2)),
                ("p-value", _r(p)),
            ]
        ),
        conclusion=f"LCG menghasilkan {n} bilangan dengan periode {period or '>200000'}; uji keseragaman p = {p:.4f}.",
    )


# --------------------------------------------------------------------------- inverse transform & acceptance-rejection


def random_variates(
    method: str,
    dist: str,
    params: list[float],
    n: int,
    seed: int,
    pdf: str | None,
    lower: float | None,
    upper: float | None,
) -> SolverResponse:
    if not 1 <= n <= 20000:
        raise SolverError("Jumlah sampel 1–20000.")
    rng = np.random.default_rng(seed)
    u = rng.random(n)
    steps: list[Step] = []
    rows = []
    if method == "inverse":
        if dist == "exponential":
            lam = params[0] if params else 0
            if lam <= 0:
                raise SolverError("Isi laju λ > 0.")
            x = -np.log(1 - u) / lam
            formula = rf"F(x) = 1 - e^{{-\lambda x}} \Rightarrow x = -\frac{{\ln(1-u)}}{{\lambda}},\ \lambda = {lam:g}"
            mean = 1 / lam
        elif dist == "uniform":
            if len(params) != 2 or params[1] <= params[0]:
                raise SolverError("Isi a dan b (b > a).")
            a, b = params
            x = a + (b - a) * u
            formula = rf"x = a + (b-a)u,\ a = {a:g},\ b = {b:g}"
            mean = (a + b) / 2
        elif dist == "discrete":
            if len(params) < 2 or len(params) % 2:
                raise SolverError("Isi pasangan nilai dan peluang: x1, p1, x2, p2, …")
            vals, probs = np.array(params[0::2]), np.array(params[1::2])
            if abs(probs.sum() - 1) > 1e-6:
                raise SolverError("Peluang harus berjumlah 1.")
            cdf = np.cumsum(probs)
            x = vals[np.searchsorted(cdf, u, side="right").clip(max=len(vals) - 1)]
            formula = r"x = x_k \text{ bila } F(x_{k-1}) \le u < F(x_k)"
            mean = float((vals * probs).sum())
            steps.append(
                Step(
                    title="Tabel distribusi kumulatif",
                    table=Table(
                        columns=["x", "p", "F(x)", "Rentang u"],
                        rows=[
                            [_r(v), _r(p), _r(c), f"[{_r(c - p)}, {_r(c)})"]
                            for v, p, c in zip(vals, probs, cdf, strict=True)
                        ],
                    ),
                )
            )
        elif dist == "triangular":
            if len(params) != 3 or not params[0] <= params[1] <= params[2] or params[0] == params[2]:
                raise SolverError("Isi a ≤ mode ≤ b (a < b).")
            a, c, b = params
            fc = (c - a) / (b - a)
            x = np.where(u < fc, a + np.sqrt(u * (b - a) * (c - a)), b - np.sqrt((1 - u) * (b - a) * (b - c)))
            formula = r"x = a + \sqrt{u(b-a)(c-a)}\ (u < F(c)),\ \text{selain itu}\ x = b - \sqrt{(1-u)(b-a)(b-c)}"
            mean = (a + b + c) / 3
        else:
            raise SolverError("Distribusi inverse transform: exponential, uniform, discrete, triangular.")
        steps.insert(
            0,
            Step(
                title="Metode inverse transform",
                latex=r"x = F^{-1}(u),\quad u \sim U(0, 1)",
                explanation="Bangkitkan u seragam lalu cari x dengan F(x) = u.",
            ),
        )
        steps.append(Step(title="Rumus", latex=formula))
        rows = [[i + 1, _r(u[i]), _r(float(x[i]))] for i in range(min(n, 20))]
        accept_rate = 1.0
    elif method == "rejection":
        if not pdf or lower is None or upper is None or upper <= lower:
            raise SolverError("Acceptance-rejection memerlukan f(x) dan batas bawah < batas atas.")
        f = Expr(pdf)
        if len(f.variables) != 1:
            raise SolverError("f(x) harus fungsi satu variabel.")
        grid = np.linspace(lower, upper, 2001)
        fv = np.array([f.safe([g]) for g in grid])
        if np.any(fv < -1e-12) or not np.all(np.isfinite(fv)):
            raise SolverError("f(x) harus nonnegatif dan berhingga pada interval.")
        big_m = float(fv.max()) * 1.0001
        out = []
        tries = 0
        while len(out) < n and tries < 50 * n:
            u1, u2 = rng.random(), rng.random()
            xc = lower + (upper - lower) * u1
            tries += 1
            ok = u2 * big_m <= f.safe([xc])
            if len(rows) < 20:
                rows.append([tries, _r(u1), _r(u2), _r(xc), "Terima" if ok else "Tolak"])
            if ok:
                out.append(xc)
        x = np.array(out)
        area = float(np.trapezoid(fv, grid)) if hasattr(np, "trapezoid") else float(np.trapz(fv, grid))
        mean = (
            float(np.trapezoid(grid * fv, grid) / area)
            if hasattr(np, "trapezoid")
            else float(np.trapz(grid * fv, grid) / area)
        )
        accept_rate = len(out) / tries
        steps = [
            Step(
                title="Metode acceptance-rejection",
                latex=rf"x = a + (b-a)u_1;\ \text{{terima bila}}\ u_2 \le \frac{{f(x)}}{{M}},\quad M = \max f = {big_m:.4f}",
                explanation=f"Peluang diterima = (luas di bawah f) / (M(b − a)) ≈ {accept_rate:.4f}.",
            )
        ]
    else:
        raise SolverError("Metode harus inverse atau rejection.")
    cols = ["i", "u", "x"] if method == "inverse" else ["Percobaan", "u₁", "u₂", "Kandidat x", "Keputusan"]
    table = NamedTable(title="Contoh pembangkitan", columns=cols, rows=rows)
    steps.append(Step(title="Contoh", table=table))
    return SolverResponse(
        result={"sample": x[:2000].tolist(), "mean": float(x.mean()), "acceptance": accept_rate},
        steps=steps,
        tables=[table],
        charts=[_hist(x, "Histogram sampel", "x")],
        summary=summary_items(
            [
                ("Rata-rata sampel", _r(float(x.mean()))),
                ("Rata-rata teoretis", _r(mean)),
                ("Simpangan baku sampel", _r(float(x.std(ddof=1))) if x.size > 1 else "—"),
                ("Tingkat penerimaan", _r(accept_rate)),
            ]
        ),
        conclusion=f"{x.size} sampel dibangkitkan; rata-rata sampel {float(x.mean()):.4f} (teoretis {mean:.4f}).",
    )


# --------------------------------------------------------------------------- Monte Carlo umum

_DIST = re.compile(r"^\s*([A-Za-z_]\w*)\s*~\s*(\w+)\s*\(([^)]*)\)\s*$")


def _sampler(name: str, args: list[float], rng: np.random.Generator):
    table = {
        "normal": (2, lambda n: rng.normal(args[0], args[1], n)),
        "uniform": (2, lambda n: rng.uniform(args[0], args[1], n)),
        "exponential": (1, lambda n: rng.exponential(1 / args[0], n)),
        "poisson": (1, lambda n: rng.poisson(args[0], n).astype(float)),
        "triangular": (3, lambda n: rng.triangular(args[0], args[1], args[2], n)),
        "binomial": (2, lambda n: rng.binomial(int(args[0]), args[1], n).astype(float)),
        "constant": (1, lambda n: np.full(n, args[0])),
    }
    if name not in table:
        raise SolverError(f"Distribusi “{name}” tidak dikenal. Pilihan: {', '.join(table)}.")
    k, fn = table[name]
    if len(args) != k:
        raise SolverError(f"Distribusi {name} memerlukan {k} parameter.")
    return fn


def monte_carlo(variables: str, output: str, n: int, seed: int, antithetic: bool) -> SolverResponse:
    if not 10 <= n <= 200000:
        raise SolverError("Jumlah replikasi 10–200000.")
    rng = np.random.default_rng(seed)
    defs = []
    for raw in variables.replace("\r", "").split("\n"):
        if not raw.strip():
            continue
        m = _DIST.match(raw)
        if not m:
            raise SolverError(f"Baris “{raw.strip()}”: gunakan format “X ~ normal(100, 15)”.")
        try:
            args = [float(a) for a in m.group(3).split(",") if a.strip()]
        except ValueError as exc:
            raise SolverError(f"Parameter distribusi di “{raw.strip()}” harus angka.") from exc
        defs.append((m.group(1), m.group(2).lower(), args))
    if not defs:
        raise SolverError("Definisikan minimal satu variabel acak.")
    names = [d[0] for d in defs]
    f = Expr(output, names)

    def run(count: int, gen: np.random.Generator) -> np.ndarray:
        cols = [_sampler(dist, args, gen)(count) for _, dist, args in defs]
        mat = np.column_stack(cols)
        return np.array([f.safe(row) for row in mat])

    y = run(n, rng)
    if not np.all(np.isfinite(y)):
        raise SolverError("Ekspresi output menghasilkan nilai tak berhingga untuk sebagian sampel.")
    mean, lo, hi = _ci(y)
    steps = [
        Step(
            title="Model",
            explanation="Variabel acak: "
            + "; ".join(f"{nm} ~ {dist}({', '.join(f'{a:g}' for a in args)})" for nm, dist, args in defs)
            + f". Output: {output}.",
        ),
        Step(
            title="Replikasi Monte Carlo",
            explanation=f"{n} replikasi independen; setiap replikasi membangkitkan semua variabel lalu menghitung output.",
            latex=rf"\bar{{y}} = {mean:.6f},\quad s = {float(y.std(ddof=1)):.6f},\quad \text{{CI }} 95\%: [{lo:.6f},\ {hi:.6f}]",
        ),
    ]
    summary = [
        ("Rata-rata output", _r(mean)),
        ("Batas bawah CI 95%", _r(lo)),
        ("Batas atas CI 95%", _r(hi)),
        ("Simpangan baku", _r(float(y.std(ddof=1)))),
        ("P5", _r(float(np.percentile(y, 5)))),
        ("P95", _r(float(np.percentile(y, 95)))),
    ]
    if antithetic:
        if any(dist not in ("uniform", "exponential", "normal", "triangular", "constant") for _, dist, _ in defs):
            raise SolverError(
                "Antithetic variates di sini mendukung distribusi kontinu (uniform, exponential, normal, triangular)."
            )
        half = n // 2
        g = np.random.default_rng(seed + 1)
        uu = g.random((half, len(defs)))
        pairs = []
        for umat in (uu, 1 - uu):
            cols = []
            for k, (_, dist, args) in enumerate(defs):
                uk = umat[:, k]
                if dist == "uniform":
                    cols.append(args[0] + (args[1] - args[0]) * uk)
                elif dist == "exponential":
                    cols.append(-np.log(1 - np.clip(uk, 0, 1 - 1e-12)) / args[0])
                elif dist == "normal":
                    cols.append(stats.norm.ppf(np.clip(uk, 1e-12, 1 - 1e-12), args[0], args[1]))
                elif dist == "constant":
                    cols.append(np.full(half, args[0]))
                else:
                    cols.append(
                        stats.triang.ppf(uk, (args[1] - args[0]) / (args[2] - args[0]), args[0], args[2] - args[0])
                    )
            pairs.append(np.array([f.safe(row) for row in np.column_stack(cols)]))
        anti = (pairs[0] + pairs[1]) / 2
        var_plain = float(y[: 2 * half].reshape(half, 2).mean(axis=1).var(ddof=1))
        var_anti = float(anti.var(ddof=1))
        steps.append(
            Step(
                title="Reduksi variansi: antithetic variates",
                explanation="Untuk setiap u dipakai pasangan 1 − u; rata-rata pasangan berkorelasi negatif sehingga variansi estimator turun.",
                latex=rf"\text{{Var (biasa, per pasangan)}} = {var_plain:.6f},\quad \text{{Var (antithetic)}} = {var_anti:.6f},\quad \text{{reduksi}} = {100 * (1 - var_anti / var_plain) if var_plain else 0:.1f}\%",
            )
        )
        summary += [
            ("Rata-rata (antithetic)", _r(float(anti.mean()))),
            ("Reduksi variansi (%)", _r(100 * (1 - var_anti / var_plain)) if var_plain else 0),
        ]
    return SolverResponse(
        result={"mean": mean, "ci": [lo, hi], "std": float(y.std(ddof=1))},
        steps=steps,
        charts=[_hist(y, "Distribusi output simulasi", output)],
        summary=summary_items(summary),
        conclusion=f"Estimasi E[{output}] = {mean:.6f} dengan CI 95% [{lo:.6f}, {hi:.6f}] dari {n} replikasi.",
    )


# --------------------------------------------------------------------------- simulasi antrian


def _queue_once(
    lam: float, mu: float, s: int, customers: int, rng: np.random.Generator, record: list | None = None
) -> tuple[float, float]:
    t = 0.0
    free_at = [0.0] * s
    heapq.heapify(free_at)
    waits, systems = [], []
    for k in range(customers):
        t += rng.exponential(1 / lam)
        start_server = heapq.heappop(free_at)
        start = max(t, start_server)
        service = rng.exponential(1 / mu)
        end = start + service
        heapq.heappush(free_at, end)
        waits.append(start - t)
        systems.append(end - t)
        if record is not None and k < 15:
            record.append([k + 1, _r(t), _r(start), _r(service), _r(end), _r(start - t)])
    warm = customers // 10
    return float(np.mean(waits[warm:])), float(np.mean(systems[warm:]))


def queue_simulation(lam: float, mu: float, s: int, customers: int, replications: int, seed: int) -> SolverResponse:
    if lam <= 0 or mu <= 0 or s < 1:
        raise SolverError("λ, μ > 0 dan s ≥ 1.")
    if not 50 <= customers <= 20000 or not 2 <= replications <= 100:
        raise SolverError("Gunakan 50–20000 pelanggan dan 2–100 replikasi.")
    rng = np.random.default_rng(seed)
    rec: list = []
    res = np.array([_queue_once(lam, mu, s, customers, rng, rec if r == 0 else None) for r in range(replications)])
    wq = _ci(res[:, 0])
    w = _ci(res[:, 1])
    trace = NamedTable(
        title="Jejak kejadian (replikasi 1, 15 pelanggan pertama)",
        columns=["Pelanggan", "Tiba", "Mulai dilayani", "Durasi layanan", "Selesai", "Waktu tunggu"],
        rows=rec,
    )
    analytic = None
    try:
        analytic = mms_metrics(lam, mu, s)
    except SolverError:
        pass
    rows = [
        ["Wq (menunggu)", _r(wq[0]), f"[{_r(wq[1])}, {_r(wq[2])}]", _r(analytic["wq"]) if analytic else "tidak stabil"],
        ["W (dalam sistem)", _r(w[0]), f"[{_r(w[1])}, {_r(w[2])}]", _r(analytic["w"]) if analytic else "tidak stabil"],
    ]
    table = NamedTable(
        title="Hasil simulasi vs teori M/M/s",
        columns=["Ukuran", "Rata-rata simulasi", "CI 95%", "Nilai teoretis"],
        rows=rows,
    )
    return SolverResponse(
        result={"wq": wq[0], "w": w[0], "wq_ci": [wq[1], wq[2]], "analytic_wq": analytic["wq"] if analytic else None},
        steps=[
            Step(
                title="Simulasi kejadian diskret",
                explanation="Setiap pelanggan: waktu antarkedatangan ~ Exp(λ), waktu layanan ~ Exp(μ); pelanggan dilayani server yang paling cepat bebas (FCFS). 10% pelanggan awal dibuang (warm-up).",
                table=trace,
            ),
            Step(
                title="Analisis output",
                explanation=f"{replications} replikasi independen; interval kepercayaan 95% memakai distribusi t.",
                table=table,
            ),
        ],
        tables=[table, trace],
        charts=[_hist(res[:, 0], "Rata-rata waktu tunggu per replikasi", "Wq")],
        summary=summary_items(
            [
                ("Wq simulasi", _r(wq[0])),
                ("CI 95% Wq", f"[{_r(wq[1])}, {_r(wq[2])}]"),
                ("Wq teoretis", _r(analytic["wq"]) if analytic else "—"),
            ]
        ),
        conclusion=f"Waktu tunggu rata-rata hasil simulasi {wq[0]:.4f} (CI 95% [{wq[1]:.4f}, {wq[2]:.4f}])"
        + (f"; nilai teoretis {analytic['wq']:.4f}." if analytic else "."),
    )


# --------------------------------------------------------------------------- simulasi persediaan (s, S)


def inventory_simulation(
    small_s: float,
    big_s: float,
    demand_values: list[float],
    demand_probs: list[float],
    periods: int,
    replications: int,
    order_cost: float,
    unit_cost: float,
    holding: float,
    shortage: float,
    seed: int,
    initial: float | None,
) -> SolverResponse:
    if big_s <= small_s:
        raise SolverError("S harus lebih besar dari s.")
    vals, probs = np.array(demand_values, float), np.array(demand_probs, float)
    if vals.size == 0 or vals.size != probs.size or abs(probs.sum() - 1) > 1e-6:
        raise SolverError("Isi nilai permintaan dan peluangnya (berjumlah 1).")
    if not 1 <= periods <= 2000 or not 2 <= replications <= 200:
        raise SolverError("Gunakan 1–2000 periode dan 2–200 replikasi.")
    rng = np.random.default_rng(seed)
    costs = []
    trace = []
    for r in range(replications):
        inv = big_s if initial is None else initial
        total = 0.0
        for t in range(periods):
            order = 0.0
            if inv <= small_s:
                order = big_s - inv
                total += order_cost + unit_cost * order
                inv += order
            d = float(rng.choice(vals, p=probs))
            end = inv - d
            total += holding * max(end, 0) + shortage * max(-end, 0)
            if r == 0 and t < 15:
                trace.append([t + 1, _r(inv - order), _r(order), _r(d), _r(end)])
            inv = max(end, 0)  # kekurangan hilang (lost sales)
        costs.append(total / periods)
    mean, lo, hi = _ci(np.array(costs))
    table = NamedTable(
        title="Jejak simulasi (replikasi 1)",
        columns=["Periode", "Persediaan awal", "Pesanan", "Permintaan", "Persediaan akhir"],
        rows=trace,
    )
    return SolverResponse(
        result={"mean_cost": mean, "ci": [lo, hi]},
        steps=[
            Step(
                title="Kebijakan (s, S)",
                explanation=f"Awal setiap periode: bila persediaan ≤ s = {small_s:g}, pesan sampai S = {big_s:g} (datang seketika). Permintaan acak diskrit; kekurangan hilang dengan penalti.",
            ),
            Step(title="Jejak simulasi", table=table),
            Step(
                title="Analisis output",
                latex=rf"\bar{{C}} = {mean:.4f},\quad \text{{CI 95\%}} = [{lo:.4f},\ {hi:.4f}]",
                explanation=f"{replications} replikasi × {periods} periode.",
            ),
        ],
        tables=[table],
        charts=[_hist(np.array(costs), "Biaya rata-rata per periode tiap replikasi", "Biaya")],
        summary=summary_items([("Biaya rata-rata per periode", _r(mean)), ("CI 95%", f"[{_r(lo)}, {_r(hi)}]")]),
        conclusion=f"Biaya rata-rata per periode untuk kebijakan (s, S) = ({small_s:g}, {big_s:g}) ≈ {mean:.4f} (CI 95% [{lo:.4f}, {hi:.4f}]).",
    )
