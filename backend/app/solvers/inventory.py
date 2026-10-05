"""Teori persediaan (Bab 19): EOQ dasar & backorder, diskon kuantitas, EPQ, Wagner-Whitin (periodik deterministik),
model (R, Q) stokastik, newsvendor (satu periode), dan kebijakan (s, S) peninjauan periodik."""

from __future__ import annotations

import math

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items


def _r(x: float) -> float:
    return float(round(x, 6))


def _pos(**kw: float) -> None:
    for k, v in kw.items():
        if v is None or v <= 0:
            raise SolverError(f"Parameter {k} harus lebih besar dari 0.")


def _cost_chart(q_star: float, cost_fn, title: str) -> Chart:
    qs = np.linspace(max(q_star * 0.2, 1e-6), q_star * 3, 200)
    return Chart(
        id="cost-curve",
        title="Kurva biaya",
        spec=plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": qs.tolist(),
                    "y": [cost_fn(q) for q in qs],
                    "name": "Biaya total per satuan waktu",
                },
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": [q_star],
                    "y": [cost_fn(q_star)],
                    "marker": {"size": 12, "color": "#ef4444"},
                    "name": "Q*",
                },
            ],
            title,
            xaxis={"title": {"text": "Ukuran pesanan Q"}},
            yaxis={"title": {"text": "Biaya"}},
        ),
    )


def eoq(
    demand: float,
    setup: float,
    holding: float,
    unit_cost: float = 0.0,
    lead_time: float = 0.0,
    shortage: float | None = None,
) -> SolverResponse:
    _pos(demand=demand, setup=setup, holding=holding)
    d, k, h, c = demand, setup, holding, unit_cost
    if shortage:
        p = shortage
        q = math.sqrt(2 * d * k / h) * math.sqrt((p + h) / p)
        s_max = math.sqrt(2 * d * k / h) * math.sqrt(p / (p + h))
        cost = lambda qq: (
            d * k / qq + h * (qq * p / (p + h)) ** 2 / (2 * qq) + p * (qq - qq * p / (p + h)) ** 2 / (2 * qq) + d * c
        )  # noqa: E731
        total = cost(q)
        steps = [
            Step(
                title="EOQ dengan backorder terencana",
                explanation=f"Kekurangan diizinkan dengan biaya p = {p:g} per unit per satuan waktu; pesanan yang tertunda dipenuhi saat barang datang.",
            ),
            Step(
                title="Kuantitas optimal",
                latex=rf"Q^* = \sqrt{{\frac{{2dK}}{{h}}}}\sqrt{{\frac{{p+h}}{{p}}}} = {q:.4f},\quad S^* = \sqrt{{\frac{{2dK}}{{h}}}}\sqrt{{\frac{{p}}{{p+h}}}} = {s_max:.4f}",
            ),
            Step(
                title="Kekurangan maksimum & siklus",
                latex=rf"Q^* - S^* = {q - s_max:.4f},\quad t^* = Q^*/d = {q / d:.4f}",
            ),
        ]
        summary = [
            ("Q* (ukuran pesanan)", _r(q)),
            ("S* (persediaan maksimum)", _r(s_max)),
            ("Kekurangan maksimum", _r(q - s_max)),
            ("Panjang siklus", _r(q / d)),
            ("Biaya total per satuan waktu", _r(total)),
        ]
        title = "EOQ dengan backorder"
    else:
        q = math.sqrt(2 * d * k / h)
        cost = lambda qq: d * k / qq + h * qq / 2 + d * c  # noqa: E731
        total = cost(q)
        steps = [
            Step(
                title="Model EOQ dasar",
                explanation="Permintaan kontinu dengan laju konstan d, pesanan datang seketika (atau setelah lead time tetap), tanpa kekurangan.",
            ),
            Step(title="Biaya total per satuan waktu", latex=r"T(Q) = \frac{dK}{Q} + \frac{hQ}{2} + dc"),
            Step(
                title="Kuantitas pesanan ekonomis",
                latex=rf"Q^* = \sqrt{{\frac{{2dK}}{{h}}}} = \sqrt{{\frac{{2 \cdot {d:g} \cdot {k:g}}}{{{h:g}}}}} = {q:.4f}",
                explanation="Pada Q*, biaya pemesanan tahunan sama dengan biaya penyimpanan tahunan.",
            ),
        ]
        summary = [
            ("Q* (EOQ)", _r(q)),
            ("Panjang siklus t* = Q*/d", _r(q / d)),
            ("Frekuensi pemesanan d/Q*", _r(d / q)),
            ("Biaya total per satuan waktu", _r(total)),
        ]
        title = "EOQ dasar"
    if lead_time:
        rp = d * lead_time
        steps.append(
            Step(
                title="Titik pemesanan kembali",
                latex=rf"\text{{Titik pemesanan}} = d \cdot L = {d:g} \cdot {lead_time:g} = {rp:.4f}",
                explanation="Pesan ketika persediaan turun ke tingkat ini.",
            )
        )
        summary.append(("Titik pemesanan kembali", _r(rp)))
    return SolverResponse(
        result={"q": q, "total_cost": total},
        steps=steps,
        charts=[_cost_chart(q, cost, f"Biaya total {title}")],
        summary=summary_items(summary),
        conclusion=f"Pesan Q* = {q:.4f} unit setiap {q / d:.4f} satuan waktu; biaya total ≈ {total:.4f}.",
    )


def quantity_discount(demand: float, setup: float, holding_rate: float, breaks: list[list[float]]) -> SolverResponse:
    """breaks: [[kuantitas minimum, harga per unit], …]; biaya simpan h = holding_rate × harga."""
    _pos(demand=demand, setup=setup, holding_rate=holding_rate)
    if not breaks or any(len(b) != 2 for b in breaks):
        raise SolverError("Setiap tingkat diskon berisi: kuantitas minimum dan harga per unit.")
    tiers = sorted(([float(a), float(b)] for a, b in breaks), key=lambda t: t[0])
    rows = []
    best = None
    for i, (qmin, price) in enumerate(tiers):
        qmax = tiers[i + 1][0] - 1e-9 if i + 1 < len(tiers) else math.inf
        h = holding_rate * price
        q0 = math.sqrt(2 * demand * setup / h)
        q = min(max(q0, qmin), qmax)
        if q < qmin:
            continue
        total = demand * setup / q + h * q / 2 + demand * price
        rows.append([f"≥ {qmin:g}", price, _r(q0), _r(q), _r(demand * price), _r(total)])
        if best is None or total < best[1]:
            best = (q, total, price)
    table = NamedTable(
        title="Evaluasi setiap tingkat harga",
        columns=["Kuantitas", "Harga/unit", "Q* EOQ", "Q layak", "Biaya pembelian", "Biaya total"],
        rows=rows,
    )
    return SolverResponse(
        result={"q": best[0], "total_cost": best[1], "price": best[2]},
        steps=[
            Step(
                title="Prosedur diskon kuantitas",
                explanation="Untuk setiap tingkat harga: hitung EOQ dengan h = i·c, sesuaikan ke rentang kuantitas tingkat itu (bila di bawah minimum, naikkan ke minimum), lalu hitung biaya total termasuk biaya pembelian.",
                latex=r"T(Q) = \frac{dK}{Q} + \frac{icQ}{2} + dc",
            ),
            Step(title="Bandingkan biaya total", table=table),
        ],
        tables=[table],
        summary=summary_items(
            [("Q optimal", _r(best[0])), ("Harga terpilih", best[2]), ("Biaya total minimum", _r(best[1]))]
        ),
        conclusion=f"Pesan {best[0]:.4f} unit dengan harga {best[2]:g}/unit; biaya total ≈ {best[1]:.4f}.",
    )


def epq(demand: float, production_rate: float, setup: float, holding: float) -> SolverResponse:
    _pos(demand=demand, production_rate=production_rate, setup=setup, holding=holding)
    if production_rate <= demand:
        raise SolverError("Laju produksi harus lebih besar dari laju permintaan.")
    d, r, k, h = demand, production_rate, setup, holding
    q = math.sqrt(2 * d * k / (h * (1 - d / r)))
    cost = lambda qq: d * k / qq + h * qq * (1 - d / r) / 2  # noqa: E731
    return SolverResponse(
        result={"q": q, "total_cost": cost(q), "max_inventory": q * (1 - d / r)},
        steps=[
            Step(
                title="Model EPQ (produksi bertahap)",
                explanation=f"Barang diproduksi dengan laju r = {r:g} sambil dikonsumsi dengan laju d = {d:g}; persediaan naik dengan laju r − d selama produksi.",
            ),
            Step(
                title="Kuantitas produksi optimal",
                latex=rf"Q^* = \sqrt{{\frac{{2dK}}{{h(1 - d/r)}}}} = {q:.4f},\quad I_{{max}} = Q^*(1 - d/r) = {q * (1 - d / r):.4f}",
            ),
        ],
        charts=[_cost_chart(q, cost, "Biaya total EPQ")],
        summary=summary_items(
            [
                ("Q* (ukuran lot produksi)", _r(q)),
                ("Persediaan maksimum", _r(q * (1 - d / r))),
                ("Lama produksi per siklus Q*/r", _r(q / r)),
                ("Biaya total per satuan waktu", _r(cost(q))),
            ]
        ),
        conclusion=f"Produksi Q* = {q:.4f} unit per lot; biaya setup + simpan ≈ {cost(q):.4f}.",
    )


def wagner_whitin(demands: list[float], setup: float, holding: float, unit_cost: float = 0.0) -> SolverResponse:
    n = len(demands)
    if n == 0 or n > 52:
        raise SolverError("Isi permintaan 1–52 periode.")
    if setup < 0 or holding < 0 or any(x < 0 for x in demands):
        raise SolverError("Biaya dan permintaan tidak boleh negatif.")
    d = [float(x) for x in demands]
    c = [0.0] * (n + 1)  # c[t] = biaya minimum periode t..n (indeks 0-based), c[n] = 0
    choice = [0] * n
    rows = []
    for t in range(n - 1, -1, -1):
        options = {}
        for j in range(t, n):
            qty = sum(d[t : j + 1])
            hold = sum(holding * d[k] * (k - t) for k in range(t, j + 1))
            options[j] = (setup if qty > 0 else 0) + hold + c[j + 1]
        j_best = min(options, key=lambda j: (options[j], j))
        c[t], choice[t] = options[j_best], j_best
        rows.append(
            [
                t + 1,
                *[_r(options[j]) if j in options else "—" for j in range(n)],
                _r(c[t]),
                f"produksi untuk periode {t + 1}–{j_best + 1}",
            ]
        )
    plan = []
    t = 0
    while t < n:
        j = choice[t]
        qty = sum(d[t : j + 1])
        plan.append([t + 1, _r(qty), f"{t + 1}–{j + 1}"])
        t = j + 1
    total = c[0] + unit_cost * sum(d)
    table = NamedTable(
        title="Rencana produksi optimal", columns=["Periode produksi", "Jumlah", "Memenuhi periode"], rows=plan
    )
    return SolverResponse(
        result={"total_cost": total, "plan": plan},
        steps=[
            Step(
                title="Model periodik deterministik (Wagner-Whitin)",
                explanation="Produksi hanya dilakukan saat persediaan awal periode nol; jadi keputusan = sampai periode berapa produksi saat ini memenuhi permintaan.",
                latex=r"C_t = \min_{j \ge t}\left\{K + h\sum_{k=t}^{j}(k - t)d_k + C_{j+1}\right\}",
            ),
            Step(
                title="Tabel DP (mundur)",
                table=Table(
                    columns=["Periode t", *[f"sampai {j + 1}" for j in range(n)], "Cₜ*", "Keputusan"], rows=rows[::-1]
                ),
            ),
            Step(title="Kebijakan optimal", table=table),
        ],
        tables=[table],
        charts=[
            Chart(
                id="ww",
                title="Rencana",
                spec=plotly_figure(
                    [
                        {"type": "bar", "x": list(range(1, n + 1)), "y": d, "name": "Permintaan"},
                        {"type": "bar", "x": [p[0] for p in plan], "y": [p[1] for p in plan], "name": "Produksi"},
                    ],
                    "Permintaan vs produksi per periode",
                    barmode="group",
                    xaxis={"title": {"text": "Periode"}},
                ),
            )
        ],
        summary=summary_items([("Biaya total minimum", _r(total)), ("Jumlah setup", len(plan))]),
        conclusion=f"Biaya total minimum {total:.4f} dengan {len(plan)} kali produksi.",
    )


def rq_policy(
    demand_rate: float, setup: float, holding: float, lead_mean: float, lead_sd: float, service: float
) -> SolverResponse:
    _pos(demand_rate=demand_rate, setup=setup, holding=holding, lead_mean=lead_mean, lead_sd=lead_sd)
    if not 0 < service < 1:
        raise SolverError("Tingkat layanan harus di antara 0 dan 1.")
    q = math.sqrt(2 * demand_rate * setup / holding)
    z = float(stats.norm.ppf(service))
    r = lead_mean + z * lead_sd
    return SolverResponse(
        result={"q": q, "r": r, "safety_stock": r - lead_mean},
        steps=[
            Step(
                title="Model (R, Q) peninjauan kontinu",
                explanation="Saat posisi persediaan turun ke R, pesan Q unit. Permintaan selama lead time berdistribusi normal.",
            ),
            Step(
                title="Ukuran pesanan",
                latex=rf"Q = \sqrt{{\frac{{2dK}}{{h}}}} = {q:.4f}",
                explanation="Aproksimasi Hillier: gunakan rumus EOQ untuk Q.",
            ),
            Step(
                title="Titik pemesanan kembali",
                latex=rf"R = \mu + z_L\sigma = {lead_mean:g} + {z:.4f}\cdot {lead_sd:g} = {r:.4f}",
                explanation=f"z dipilih agar P(tidak terjadi kekurangan selama lead time) = {service:g}. Stok pengaman = {r - lead_mean:.4f}.",
            ),
        ],
        summary=summary_items(
            [
                ("Q (ukuran pesanan)", _r(q)),
                ("R (titik pemesanan)", _r(r)),
                ("Stok pengaman", _r(r - lead_mean)),
                ("z", _r(z)),
            ]
        ),
        conclusion=f"Pesan {q:.4f} unit setiap kali posisi persediaan turun ke {r:.4f}.",
    )


def newsvendor(
    price: float, cost: float, salvage: float, shortage_penalty: float, dist: str, params: list[float]
) -> SolverResponse:
    cu = price - cost + shortage_penalty
    co = cost - salvage
    if cu <= 0 or co <= 0:
        raise SolverError("Biaya kekurangan (cᵤ) dan biaya kelebihan (cₒ) harus positif.")
    ratio = cu / (cu + co)
    if dist == "normal":
        if len(params) != 2 or params[1] <= 0:
            raise SolverError("Distribusi normal: isi rata-rata dan simpangan baku.")
        q = float(stats.norm.ppf(ratio, params[0], params[1]))
        dist_txt = f"Normal(μ = {params[0]:g}, σ = {params[1]:g})"
    elif dist == "uniform":
        if len(params) != 2 or params[1] <= params[0]:
            raise SolverError("Distribusi seragam: isi batas bawah a dan batas atas b (b > a).")
        q = params[0] + ratio * (params[1] - params[0])
        dist_txt = f"Seragam({params[0]:g}, {params[1]:g})"
    elif dist == "discrete":
        if len(params) < 2 or len(params) % 2:
            raise SolverError("Distribusi diskrit: isi pasangan nilai dan peluang (d1, p1, d2, p2, …).")
        vals = np.array(params[0::2])
        probs = np.array(params[1::2])
        if abs(probs.sum() - 1) > 1e-6:
            raise SolverError("Peluang distribusi diskrit harus berjumlah 1.")
        order = np.argsort(vals)
        cdf = np.cumsum(probs[order])
        q = float(vals[order][np.searchsorted(cdf, ratio - 1e-12)])
        dist_txt = "diskrit"
    else:
        raise SolverError("Distribusi harus normal, uniform, atau discrete.")
    return SolverResponse(
        result={"q": q, "critical_ratio": ratio},
        steps=[
            Step(
                title="Biaya marjinal",
                latex=rf"c_u = \text{{harga}} - c + \text{{penalti}} = {cu:g},\qquad c_o = c - \text{{nilai sisa}} = {co:g}",
                explanation="cᵤ = rugi per unit kekurangan (laba hilang), cₒ = rugi per unit kelebihan.",
            ),
            Step(title="Rasio kritis", latex=rf"P(D \le Q^*) = \frac{{c_u}}{{c_u + c_o}} = {ratio:.4f}"),
            Step(
                title="Kuantitas optimal",
                explanation=f"Permintaan berdistribusi {dist_txt}; Q* adalah kuantil ke-{ratio:.4f}.",
                latex=rf"Q^* = F^{{-1}}({ratio:.4f}) = {q:.4f}",
            ),
        ],
        summary=summary_items([("Rasio kritis", _r(ratio)), ("Q* (jumlah pesanan)", _r(q)), ("cᵤ", cu), ("cₒ", co)]),
        conclusion=f"Pesan Q* ≈ {q:.4f} unit (rasio kritis {ratio:.4f}).",
    )


def periodic_review(
    demand_mean: float, demand_sd: float, review: float, lead: float, setup: float, holding: float, service: float
) -> SolverResponse:
    _pos(demand_mean=demand_mean, demand_sd=demand_sd, review=review, setup=setup, holding=holding)
    if lead < 0 or not 0 < service < 1:
        raise SolverError("Lead time ≥ 0 dan tingkat layanan di antara 0 dan 1.")
    z = float(stats.norm.ppf(service))
    mu_l = demand_mean * lead
    sd_l = demand_sd * math.sqrt(lead) if lead > 0 else 0.0
    small_s = mu_l + z * sd_l
    q = math.sqrt(2 * demand_mean * setup / holding)
    big_s = small_s + q
    mu_rl = demand_mean * (review + lead)
    sd_rl = demand_sd * math.sqrt(review + lead)
    order_up = mu_rl + z * sd_rl
    return SolverResponse(
        result={"s": small_s, "S": big_s, "order_up_to": order_up},
        steps=[
            Step(
                title="Kebijakan (s, S) peninjauan periodik",
                explanation="Setiap R satuan waktu persediaan diperiksa; bila posisi persediaan ≤ s, pesan sampai S.",
            ),
            Step(
                title="Aproksimasi s dan S",
                latex=rf"s = \mu_L + z\sigma_L = {mu_l:.4f} + {z:.4f}\cdot{sd_l:.4f} = {small_s:.4f},\qquad S = s + Q_{{EOQ}} = {small_s:.4f} + {q:.4f} = {big_s:.4f}",
                explanation="Aproksimasi sederhana: s memberi tingkat layanan selama lead time, S − s mengikuti EOQ.",
            ),
            Step(
                title="Pembanding: kebijakan order-up-to",
                latex=rf"S' = \mu_{{R+L}} + z\sigma_{{R+L}} = {mu_rl:.4f} + {z:.4f}\cdot{sd_rl:.4f} = {order_up:.4f}",
                explanation="Bila setiap peninjauan selalu memesan, tingkat order-up-to melindungi selama R + L.",
            ),
        ],
        summary=summary_items(
            [
                ("s (titik pemesanan)", _r(small_s)),
                ("S (tingkat maksimum)", _r(big_s)),
                ("Order-up-to (pesan tiap periode)", _r(order_up)),
            ]
        ),
        warnings=[
            "Nilai (s, S) di sini adalah aproksimasi; optimasi eksak memerlukan DP stokastik atau simulasi (lihat modul Simulasi)."
        ],
        conclusion=f"Kebijakan (s, S) ≈ ({small_s:.4f}, {big_s:.4f}).",
    )
