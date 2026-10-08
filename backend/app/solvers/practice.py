"""Mode latihan: soal acak per topik (deterministik dari seed) dan pemeriksaan jawaban.

Pembahasan memakai solver yang sama dengan modul utama, sehingga langkah penyelesaiannya identik.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import SolverResponse, Table
from app.solvers import descriptive, distributions, inferential, inventory, markov, project, queueing, transport
from app.solvers.lp.graphical import solve_graphical
from app.solvers.lp.model import parse_model


@dataclass
class Generated:
    prompt: str
    fields: list[tuple[str, str]]  # (kunci, label)
    answers: dict[str, float]
    solve: Callable[[], SolverResponse]
    latex: str | None = None
    table: Table | None = None


def _statistik(rng) -> Generated:
    data = rng.integers(50, 100, 8).tolist()
    x = np.array(data, float)
    return Generated(
        f"Data nilai kuis delapan mahasiswa: {', '.join(map(str, data))}. Hitung rata-rata dan simpangan baku sampel.",
        [("mean", "Rata-rata x̄"), ("sd", "Simpangan baku sampel s")],
        {"mean": float(x.mean()), "sd": float(x.std(ddof=1))},
        lambda: descriptive.summary(data),
    )


def _uji_t(rng) -> Generated:
    mu0 = int(rng.integers(40, 60))
    data = np.round(rng.normal(mu0 + rng.normal(0, 3), 5, 10), 1).tolist()
    x = np.array(data)
    t = (x.mean() - mu0) / (x.std(ddof=1) / math.sqrt(x.size))
    return Generated(
        f"Sampel 10 pengukuran: {', '.join(f'{v:g}' for v in data)}. Uji H₀: μ = {mu0} vs H₁: μ ≠ {mu0}. Hitung statistik uji t.",
        [("t", "Statistik t")],
        {"t": float(t)},
        lambda: inferential.t_one_sample(mu0, "two-sided", 0.05, data=data),
    )


def _normal(rng) -> Generated:
    mu, sigma = int(rng.integers(50, 150)), int(rng.integers(5, 25))
    x = mu + int(rng.integers(-2 * sigma, 2 * sigma))
    from scipy import stats

    return Generated(
        f"Waktu proses berdistribusi normal dengan μ = {mu} dan σ = {sigma}. Berapa P(X ≤ {x})?",
        [("p", "P(X ≤ x)")],
        {"p": float(stats.norm.cdf(x, mu, sigma))},
        lambda: distributions.compute("normal", {"mu": mu, "sigma": sigma}, "cdf", x=x),
    )


def _lp(rng) -> Generated:
    while True:
        c1, c2 = rng.integers(1, 8, 2)
        rows = [(int(rng.integers(1, 5)), int(rng.integers(1, 5)), int(rng.integers(8, 30))) for _ in range(3)]
        text = f"max Z = {c1}x1 + {c2}x2\n" + "\n".join(f"{a}x1 + {b}x2 <= {r}" for a, b, r in rows)
        res = solve_graphical(parse_model(text))
        if res.result.get("status") == "optimal":
            break
    return Generated(
        "Selesaikan LP berikut dengan metode grafik. Berapa nilai Z optimal?",
        [("z", "Z*")],
        {"z": float(res.result["z"])},
        lambda: solve_graphical(parse_model(text)),
        latex=parse_model(text).latex(),
    )


def _eoq(rng) -> Generated:
    d, k, h = int(rng.integers(500, 5000)), int(rng.integers(20, 200)), round(float(rng.uniform(0.5, 5)), 1)
    return Generated(
        f"Permintaan tahunan {d} unit, biaya pesan {k} per pesanan, biaya simpan {h:g} per unit per tahun. Hitung EOQ.",
        [("q", "Q*")],
        {"q": math.sqrt(2 * d * k / h)},
        lambda: inventory.eoq(d, k, h),
    )


def _mm1(rng) -> Generated:
    mu = int(rng.integers(5, 15))
    lam = int(rng.integers(1, mu))
    return Generated(
        f"Pelanggan datang rata-rata {lam} per jam (Poisson) dan dilayani satu server dengan laju {mu} per jam (eksponensial). Hitung L dan Wq.",
        [("l", "L (pelanggan dalam sistem)"), ("wq", "Wq (jam)")],
        {"l": lam / (mu - lam), "wq": lam / (mu * (mu - lam))},
        lambda: queueing.mms(lam, mu, 1),
    )


def _cpm(rng) -> Generated:
    codes = list("ABCDEF")
    lines = []
    for i, c in enumerate(codes):
        preds = (
            []
            if i == 0
            else sorted(set(rng.choice(codes[:i], size=int(rng.integers(1, min(i, 2) + 1)), replace=False).tolist()))
        )
        lines.append(f"{c} | {', '.join(preds) or '-'} | {int(rng.integers(1, 9))}")
    text = "\n".join(lines)
    res = project.cpm(text)
    tbl = Table(columns=["Aktivitas", "Pendahulu", "Durasi"], rows=[[p.strip() for p in ln.split("|")] for ln in lines])
    return Generated(
        "Tentukan waktu penyelesaian proyek (panjang jalur kritis).",
        [("t", "Waktu penyelesaian")],
        {"t": res.result["duration"]},
        lambda: project.cpm(text),
        table=tbl,
    )


def _markov(rng) -> Generated:
    a, b = round(float(rng.uniform(0.1, 0.9)), 2), round(float(rng.uniform(0.1, 0.9)), 2)
    p = [[1 - a, a], [b, 1 - b]]
    return Generated(
        "Rantai Markov dua state memiliki matriks transisi di bawah. Hitung peluang steady-state π₀.",
        [("pi0", "π₀")],
        {"pi0": b / (a + b)},
        lambda: markov.analyze(p, ["0", "1"], 4, None),
        table=Table(columns=["", "ke 0", "ke 1"], rows=[["dari 0", 1 - a, a], ["dari 1", b, 1 - b]]),
    )


def _transport(rng) -> Generated:
    costs = rng.integers(2, 15, (2, 3)).tolist()
    supply = rng.integers(20, 60, 2).tolist()
    demand = rng.multinomial(sum(supply), [1 / 3] * 3).tolist()
    res = transport.solve_transportation(costs, supply, demand, "vam", True)
    tbl = Table(
        columns=["", "T1", "T2", "T3", "Penawaran"],
        rows=[[f"S{i + 1}", *costs[i], supply[i]] for i in range(2)] + [["Permintaan", *demand, ""]],
    )
    return Generated(
        "Tentukan biaya transportasi minimum.",
        [("cost", "Biaya total minimum")],
        {"cost": res.result["total_cost"]},
        lambda: transport.solve_transportation(costs, supply, demand, "vam", True),
        table=tbl,
    )


TOPICS: dict[str, tuple[str, Callable]] = {
    "statistik-deskriptif": ("Statistik deskriptif", _statistik),
    "uji-t": ("Uji-t satu sampel", _uji_t),
    "distribusi-normal": ("Distribusi normal", _normal),
    "lp-grafik": ("LP metode grafik", _lp),
    "transportasi": ("Masalah transportasi", _transport),
    "cpm": ("PERT/CPM", _cpm),
    "eoq": ("EOQ persediaan", _eoq),
    "antrian": ("Antrian M/M/1", _mm1),
    "markov": ("Rantai Markov", _markov),
}


def _gen(topic: str, seed: int) -> Generated:
    if topic not in TOPICS:
        raise SolverError("Topik latihan tidak dikenal.")
    return TOPICS[topic][1](np.random.default_rng(seed))


def topics() -> list[dict[str, str]]:
    return [{"id": k, "title": v[0]} for k, v in TOPICS.items()]


def question(topic: str, seed: int) -> dict:
    g = _gen(topic, seed)
    return {
        "topic": topic,
        "title": TOPICS[topic][0],
        "seed": seed,
        "prompt": g.prompt,
        "latex": g.latex,
        "table": g.table.model_dump() if g.table else None,
        "fields": [{"key": k, "label": label} for k, label in g.fields],
    }


def check(topic: str, seed: int, answers: dict[str, float | None]) -> dict:
    g = _gen(topic, seed)
    results = []
    for key, label in g.fields:
        exp = g.answers[key]
        given = answers.get(key)
        tol = max(0.01, abs(exp) * 0.01)
        ok = given is not None and math.isfinite(given) and abs(given - exp) <= tol
        results.append({"key": key, "label": label, "given": given, "expected": exp, "correct": ok, "tolerance": tol})
    return {"correct": all(r["correct"] for r in results), "results": results, "solution": g.solve().model_dump()}
