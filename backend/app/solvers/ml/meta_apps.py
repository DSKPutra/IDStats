"""Modul C2–C3: animasi populasi, benchmark + uji statistik, optimasi hyperparameter, seleksi fitur,
metaheuristik untuk masalah OR (TSP, knapsack, penjadwalan), dan reinforcement learning (Q-learning)."""

from __future__ import annotations

import itertools
import math
import time

import numpy as np
from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step
from app.solvers._base import plotly_figure, summary_items
from app.solvers.ml import metaheuristics as MH
from app.solvers.ml.gradient import COLORS, FUNCTIONS, load_dataset

TIME_LIMIT = 45.0


def _r(x: float, d: int = 6) -> float:
    return float(round(x, d)) if math.isfinite(x) else x


def _check_algos(algos: list[str], max_n: int) -> None:
    if not algos or len(algos) > max_n:
        raise SolverError(f"Pilih 1–{max_n} algoritma.")
    bad = [a for a in algos if a not in MH.ALGORITHMS]
    if bad:
        raise SolverError(f"Algoritma tidak dikenal: {', '.join(bad)}.")


# =========================================================================== animasi populasi 2D


def population(function: str, algorithms: list[str], pop: int, iters: int, seed: int) -> SolverResponse:
    tf = FUNCTIONS.get(function)
    if tf is None:
        raise SolverError("Fungsi uji tidak dikenal.")
    _check_algos(algorithms, 6)
    (xlo, xhi), (ylo, yhi) = tf.bounds
    fmin = min(tf.f(*m) for m in tf.minima)
    results = {}
    for a in algorithms:
        results[a] = MH.run(
            a, lambda v: tf.f(v[0], v[1]), [xlo, ylo], [xhi, yhi], pop, iters, seed, record=True, max_frames=40
        )
    xs, ys = np.linspace(xlo, xhi, 100), np.linspace(ylo, yhi, 100)
    xx, yy = np.meshgrid(xs, ys)
    zz = tf.f(xx, yy)
    zp = np.log10(zz - fmin + 1) if tf.log_scale else zz
    base = [
        {
            "type": "contour",
            "x": xs.tolist(),
            "y": ys.tolist(),
            "z": np.round(zp, 5).tolist(),
            "colorscale": "Greys",
            "showscale": False,
            "contours": {"coloring": "heatmap"},
            "hoverinfo": "skip",
            "opacity": 0.6,
        }
    ]
    pts = []
    for k, (a, r) in enumerate(results.items()):
        s0 = r.snapshots[0]
        pts.append(
            {
                "type": "scatter",
                "mode": "markers",
                "x": s0[:, 0].tolist(),
                "y": s0[:, 1].tolist(),
                "marker": {"size": 7, "color": COLORS[k % len(COLORS)], "line": {"color": "#fff", "width": 0.5}},
                "name": MH.ALGORITHMS[a][0],
            }
        )
    n_frames = max(len(r.snapshots) for r in results.values())
    frames = []
    for i in range(n_frames):
        data = []
        for r in results.values():
            s = r.snapshots[min(i, len(r.snapshots) - 1)]
            data.append({"x": s[:, 0].tolist(), "y": s[:, 1].tolist()})
        frames.append({"name": str(i), "data": data, "traces": list(range(1, 1 + len(results)))})
    every = max(1, iters // 40)
    anim = plotly_figure(
        base
        + pts
        + [
            {
                "type": "scatter",
                "mode": "markers",
                "x": [m[0] for m in tf.minima],
                "y": [m[1] for m in tf.minima],
                "marker": {"symbol": "star", "size": 14, "color": "#facc15", "line": {"color": "#000", "width": 1}},
                "name": "Minimum global",
            }
        ],
        f"Pergerakan populasi pada fungsi {tf.title}",
        xaxis={"range": [xlo, xhi], "title": {"text": "x"}},
        yaxis={"range": [ylo, yhi], "title": {"text": "y"}},
        height=540,
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0.02,
                "y": -0.08,
                "xanchor": "left",
                "yanchor": "top",
                "buttons": [
                    {
                        "label": "▶ Putar",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 150, "redraw": False},
                                "fromcurrent": True,
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                    {
                        "label": "⏸ Jeda",
                        "method": "animate",
                        "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "y": -0.08,
                "x": 0.25,
                "len": 0.75,
                "currentvalue": {"prefix": "Iterasi ≈ "},
                "steps": [
                    {
                        "label": str(i * every),
                        "method": "animate",
                        "args": [[str(i)], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                    }
                    for i in range(n_frames)
                ],
            }
        ],
    )
    anim["frames"] = frames
    conv = plotly_figure(
        [
            {
                "type": "scatter",
                "mode": "lines",
                "x": list(range(1, len(r.curve) + 1)),
                "y": [max(v - fmin, 1e-16) for v in r.curve],
                "name": MH.ALGORITHMS[a][0],
                "line": {"color": COLORS[k % len(COLORS)]},
            }
            for k, (a, r) in enumerate(results.items())
        ],
        "Konvergensi: fitness terbaik − f* (log)",
        xaxis={"title": {"text": "Iterasi"}},
        yaxis={"type": "log", "title": {"text": "f − f*"}},
    )
    rows = [
        [MH.ALGORITHMS[a][0], f"({r.best_x[0]:.4f}, {r.best_x[1]:.4f})", _r(r.best_f), r.evals]
        for a, r in results.items()
    ]
    table = NamedTable(title="Hasil", columns=["Algoritma", "x terbaik", "f terbaik", "Evaluasi fungsi"], rows=rows)
    best = min(rows, key=lambda x: x[2])
    return SolverResponse(
        result={a: {"best_f": r.best_f, "best_x": r.best_x.tolist()} for a, r in results.items()},
        steps=[Step(title=MH.ALGORITHMS[a][0], explanation=MH.ALGORITHMS[a][2]) for a in algorithms]
        + [Step(title="Hasil", explanation=f"Populasi {pop}, {iters} iterasi, seed {seed}.", table=table)],
        tables=[table],
        charts=[
            Chart(id="population", title="Animasi populasi", spec=anim),
            Chart(id="convergence", title="Konvergensi", spec=conv),
        ],
        summary=summary_items([(r[0], f"f = {r[2]:.6g}") for r in rows]),
        conclusion=f"Fitness terbaik dicapai {best[0]} (f = {best[2]:.6g}).",
    )


# =========================================================================== benchmark + uji statistik


def friedman(matrix: np.ndarray) -> tuple[float, float, np.ndarray]:
    """matrix: runs × algoritma (lebih kecil lebih baik). Mengembalikan (χ²_F, p, rata-rata peringkat)."""
    n, k = matrix.shape
    ranks = np.apply_along_axis(stats.rankdata, 1, matrix)
    mean_r = ranks.mean(axis=0)
    chi2 = 12 * n / (k * (k + 1)) * float(((mean_r - (k + 1) / 2) ** 2).sum())
    # koreksi ties
    ties = sum(
        float(((np.unique(row, return_counts=True)[1]) ** 3 - np.unique(row, return_counts=True)[1]).sum())
        for row in matrix
    )
    denom = 1 - ties / (n * (k**3 - k))
    if denom > 0:
        chi2 /= denom
    return chi2, float(stats.chi2.sf(chi2, k - 1)), mean_r


def benchmark(
    function: str, dim: int, algorithms: list[str], pop: int, iters: int, runs: int, seed: int
) -> SolverResponse:
    if function not in MH.BENCHMARKS:
        raise SolverError("Fungsi benchmark tidak dikenal.")
    _check_algos(algorithms, 8)
    if not 2 <= dim <= 50 or not 3 <= runs <= 30:
        raise SolverError("Gunakan dimensi 2–50 dan 3–30 run independen.")
    if pop * iters * runs * len(algorithms) * max(1, dim // 10) > 3_000_000:
        raise SolverError(
            "Anggaran evaluasi terlalu besar untuk server; kurangi iterasi, populasi, run, atau algoritma."
        )
    title, f, lo, hi, fstar = MH.BENCHMARKS[function]
    if function == "styblinski-tang":
        fstar *= dim
    finals = np.zeros((runs, len(algorithms)))
    curves = {}
    start = time.monotonic()
    for k, a in enumerate(algorithms):
        cs = []
        for r in range(runs):
            res = MH.run(a, f, [lo] * dim, [hi] * dim, pop, iters, seed + r)
            finals[r, k] = res.best_f - fstar
            cs.append(res.curve)
            if time.monotonic() - start > TIME_LIMIT:
                raise SolverError(f"Benchmark melebihi {TIME_LIMIT:.0f} detik; kurangi ukuran percobaan.")
        curves[a] = np.mean(np.array([c[:iters] for c in cs]), axis=0) - fstar
    names = [MH.ALGORITHMS[a][0] for a in algorithms]
    stat_rows = [
        [
            names[k],
            _r(float(finals[:, k].mean())),
            _r(float(finals[:, k].std(ddof=1))),
            _r(float(finals[:, k].min())),
            _r(float(finals[:, k].max())),
            _r(float(np.median(finals[:, k]))),
        ]
        for k in range(len(algorithms))
    ]
    stat_table = NamedTable(
        title=f"Statistik {runs} run (galat f − f*)",
        columns=["Algoritma", "Rata-rata", "Simpangan baku", "Terbaik", "Terburuk", "Median"],
        rows=stat_rows,
    )
    steps = [
        Step(
            title="Desain eksperimen",
            explanation=f"Fungsi {title} {dim} dimensi pada [{lo}, {hi}]^{dim}, populasi {pop}, {iters} iterasi, {runs} run independen dengan seed {seed}…{seed + runs - 1}. Galat = f(x_terbaik) − f*.",
            table=stat_table,
        )
    ]
    tables = [stat_table]
    summary: list = []
    conclusion = ""
    if len(algorithms) >= 2:
        chi2, p_f, mean_rank = friedman(finals)
        order = np.argsort(mean_rank)
        rank_table = NamedTable(
            title="Uji Friedman: rata-rata peringkat (1 = terbaik)",
            columns=["Algoritma", "Rata-rata peringkat"],
            rows=[[names[k], _r(float(mean_rank[k]))] for k in order],
        )
        steps.append(
            Step(
                title="Uji Friedman",
                explanation="H₀: semua algoritma berkinerja sama. Setiap run diberi peringkat antaralgoritma, lalu rata-rata peringkat dibandingkan.",
                latex=rf"\chi^2_F = \frac{{12n}}{{k(k+1)}}\sum_j\left(\bar R_j - \frac{{k+1}}{{2}}\right)^2 = {chi2:.4f},\quad p = {p_f:.4g}",
                table=rank_table,
            )
        )
        best_k = int(order[0])
        w_rows = []
        for k in range(len(algorithms)):
            if k == best_k:
                continue
            diff = finals[:, k] - finals[:, best_k]
            if np.allclose(diff, 0):
                p_w, verdict = 1.0, "Identik"
            else:
                try:
                    p_w = float(stats.wilcoxon(finals[:, best_k], finals[:, k], zero_method="wilcox").pvalue)
                except ValueError:
                    p_w = 1.0
                verdict = (
                    ("Lebih buruk dari " + names[best_k])
                    if p_w < 0.05 and np.median(diff) > 0
                    else ("Lebih baik dari " + names[best_k])
                    if p_w < 0.05
                    else "Tidak berbeda nyata"
                )
            w_rows.append([f"{names[best_k]} vs {names[k]}", _r(p_w), verdict])
        w_table = NamedTable(
            title=f"Uji Wilcoxon signed-rank berpasangan terhadap {names[best_k]} (α = 0,05)",
            columns=["Perbandingan", "p-value", "Kesimpulan"],
            rows=w_rows,
        )
        steps.append(
            Step(
                title="Uji lanjut Wilcoxon signed-rank",
                explanation="Galat setiap run dipasangkan (seed sama). Lihat juga modul Statistika → Uji Non-parametrik.",
                table=w_table,
            )
        )
        tables += [rank_table, w_table]
        summary = [
            ("Peringkat terbaik (Friedman)", names[best_k]),
            ("χ² Friedman", _r(chi2)),
            ("p-value Friedman", _r(p_f, 8)),
        ]
        conclusion = f"{names[best_k]} memiliki rata-rata peringkat terbaik; uji Friedman p = {p_f:.4g} ({'ada' if p_f < 0.05 else 'tidak ada'} perbedaan signifikan antaralgoritma)."
    else:
        conclusion = f"Galat rata-rata {stat_rows[0][1]}."
    charts = [
        Chart(
            id="box",
            title="Sebaran galat akhir",
            spec=plotly_figure(
                [
                    {
                        "type": "box",
                        "y": np.maximum(finals[:, k], 1e-16).tolist(),
                        "name": names[k],
                        "marker": {"color": COLORS[k % len(COLORS)]},
                    }
                    for k in range(len(algorithms))
                ],
                "Galat akhir per run (log)",
                yaxis={"type": "log"},
                showlegend=False,
            ),
        ),
        Chart(
            id="mean-curve",
            title="Kurva konvergensi rata-rata",
            spec=plotly_figure(
                [
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "x": list(range(1, iters + 1)),
                        "y": np.maximum(curves[a], 1e-16).tolist(),
                        "name": MH.ALGORITHMS[a][0],
                        "line": {"color": COLORS[k % len(COLORS)]},
                    }
                    for k, a in enumerate(algorithms)
                ],
                "Rata-rata galat terbaik per iterasi (log)",
                xaxis={"title": {"text": "Iterasi"}},
                yaxis={"type": "log"},
            ),
        ),
    ]
    return SolverResponse(
        result={"finals": finals.tolist(), "names": names},
        steps=steps,
        tables=tables,
        charts=charts,
        summary=summary_items(summary + [(r[0], f"rata-rata {r[1]:.4g}") for r in stat_rows]),
        conclusion=conclusion,
    )


# =========================================================================== optimasi hyperparameter

SPACES = {
    # nama: [(param, jenis, bawah, atas)] — jenis: log (kontinu skala log), int, cat
    "svm": [("C", "log", 1e-2, 1e3), ("gamma", "log", 1e-4, 1.0)],
    "rf": [("n_estimators", "int", 10, 150), ("max_depth", "int", 1, 15)],
    "knn": [("n_neighbors", "int", 1, 30), ("weights", "cat", 0, 1)],
    "mlp": [("alpha", "log", 1e-5, 1e-1), ("hidden_layer_sizes", "int", 5, 80)],
}
WEIGHTS = ["uniform", "distance"]


def _decode(model: str, u: np.ndarray) -> dict:
    params = {}
    for (name, kind, lo, hi), v in zip(SPACES[model], np.clip(u, 0, 1), strict=True):
        if kind == "log":
            params[name] = float(10 ** (math.log10(lo) + v * (math.log10(hi) - math.log10(lo))))
        elif kind == "int":
            params[name] = int(round(lo + v * (hi - lo)))
        else:
            params[name] = WEIGHTS[int(round(v))]
    return params


def _make_model(model: str, params: dict, seed: int):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC

    if model == "svm":
        est = SVC(**params)
    elif model == "rf":
        est = RandomForestClassifier(random_state=seed, n_jobs=1, **params)
    elif model == "knn":
        est = KNeighborsClassifier(**params)
    else:
        est = MLPClassifier(
            alpha=params["alpha"], hidden_layer_sizes=(params["hidden_layer_sizes"],), max_iter=300, random_state=seed
        )
    return make_pipeline(StandardScaler(), est)


def _gp_ei(xs: np.ndarray, ys: np.ndarray, cand: np.ndarray) -> np.ndarray:
    """Expected improvement dari GP sederhana (kernel RBF, panjang skala tetap 0,3, noise kecil) — memaksimumkan y."""
    mu_y, sd_y = ys.mean(), ys.std() or 1.0
    yn = (ys - mu_y) / sd_y

    def k(a, b):
        d2 = ((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)
        return np.exp(-d2 / (2 * 0.3**2))

    kxx = k(xs, xs) + 1e-6 * np.eye(len(xs))
    l_chol = np.linalg.cholesky(kxx)
    alpha = np.linalg.solve(l_chol.T, np.linalg.solve(l_chol, yn))
    ks = k(cand, xs)
    mu = ks @ alpha
    v = np.linalg.solve(l_chol, ks.T)
    var = np.maximum(1 - (v**2).sum(axis=0), 1e-12)
    sd = np.sqrt(var)
    best = yn.max()
    z = (mu - best - 0.01) / sd
    return (mu - best - 0.01) * stats.norm.cdf(z) + sd * stats.norm.pdf(z)


def hyperparameter(dataset: str, model: str, methods: list[str], budget: int, seed: int) -> SolverResponse:
    from sklearn.model_selection import cross_val_score

    if model not in SPACES:
        raise SolverError("Model harus svm, rf, knn, atau mlp.")
    if not methods or any(m not in ("grid", "random", "bayes", "pso", "de", "hho") for m in methods):
        raise SolverError("Metode: grid, random, bayes, pso, de, hho.")
    if not 4 <= budget <= 40:
        raise SolverError("Anggaran evaluasi 4–40 per metode.")
    x, y, _, classes = load_dataset(dataset, None, None, None, max_rows=600)
    space = SPACES[model]
    d = len(space)
    cache: dict[tuple, float] = {}
    start = time.monotonic()

    def score(u: np.ndarray) -> float:
        params = _decode(model, u)
        key = tuple(sorted(params.items()))
        if key not in cache:
            if time.monotonic() - start > TIME_LIMIT:
                raise SolverError(
                    f"Optimasi hyperparameter melebihi {TIME_LIMIT:.0f} detik; kurangi anggaran atau gunakan dataset lebih kecil."
                )
            cache[key] = float(cross_val_score(_make_model(model, params, seed), x, y, cv=3).mean())
        return cache[key]

    histories: dict[str, list[tuple[dict, float]]] = {}
    rng = np.random.default_rng(seed)
    for m in methods:
        hist: list[tuple[dict, float]] = []
        if m == "grid":
            per = max(2, int(round(budget ** (1 / d))))
            for combo in itertools.product(np.linspace(0, 1, per), repeat=d):
                u = np.array(combo)
                hist.append((_decode(model, u), score(u)))
        elif m == "random":
            for _ in range(budget):
                u = rng.random(d)
                hist.append((_decode(model, u), score(u)))
        elif m == "bayes":
            us = [rng.random(d) for _ in range(min(5, budget))]
            ys = [score(u) for u in us]
            while len(us) < budget:
                cand = rng.random((400, d))
                u = cand[int(np.argmax(_gp_ei(np.array(us), np.array(ys), cand)))]
                us.append(u)
                ys.append(score(u))
            hist = [(_decode(model, u), s) for u, s in zip(us, ys, strict=True)]
        else:
            pop = 5
            iters = max(1, budget // pop - 1)
            evals: list[tuple[dict, float]] = []

            def obj(u, evals=evals):
                s = score(u)
                evals.append((_decode(model, u), s))
                return -s

            MH.run(m, obj, [0.0] * d, [1.0] * d, pop, iters, seed)
            hist = evals[:budget]
        histories[m] = hist
    labels = {
        "grid": "Grid search",
        "random": "Random search",
        "bayes": "Bayesian optimization (GP-EI)",
        "pso": "PSO",
        "de": "DE",
        "hho": "HHO",
    }
    rows = []
    for m, hist in histories.items():
        best_p, best_s = max(hist, key=lambda t: t[1])
        rows.append(
            [
                labels[m],
                len(hist),
                _r(best_s, 4),
                ", ".join(f"{k} = {v:.4g}" if isinstance(v, float) else f"{k} = {v}" for k, v in best_p.items()),
            ]
        )
    table = NamedTable(
        title=f"Hasil optimasi hyperparameter ({model.upper()} pada {dataset}, akurasi CV 3-fold)",
        columns=["Metode", "Evaluasi", "Akurasi CV terbaik", "Hyperparameter terbaik"],
        rows=rows,
    )
    conv = plotly_figure(
        [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": list(range(1, len(h) + 1)),
                "y": np.maximum.accumulate([s for _, s in h]).tolist(),
                "name": labels[m],
                "line": {"color": COLORS[k % len(COLORS)]},
            }
            for k, (m, h) in enumerate(histories.items())
        ],
        "Akurasi terbaik sejauh ini vs jumlah evaluasi",
        xaxis={"title": {"text": "Evaluasi ke-"}},
        yaxis={"title": {"text": "Akurasi CV"}},
    )
    charts = [Chart(id="hpo-conv", title="Konvergensi", spec=conv)]
    if d == 2:
        n0, n1 = space[0][0], space[1][0]
        traces = []
        for k, (m, h) in enumerate(histories.items()):
            traces.append(
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": [p[n0] for p, _ in h],
                    "y": [p[n1] if not isinstance(p[n1], str) else WEIGHTS.index(p[n1]) for p, _ in h],
                    "marker": {
                        "size": 9,
                        "color": [s for _, s in h],
                        "colorscale": "Viridis",
                        "showscale": k == 0,
                        "symbol": ["circle", "square", "diamond", "cross", "triangle-up", "x"][k % 6],
                    },
                    "name": labels[m],
                    "text": [f"{s:.4f}" for _, s in h],
                }
            )
        charts.append(
            Chart(
                id="hpo-space",
                title="Titik yang dievaluasi",
                spec=plotly_figure(
                    traces,
                    "Ruang hyperparameter (warna = akurasi)",
                    xaxis={"title": {"text": n0}, "type": "log" if space[0][1] == "log" else "linear"},
                    yaxis={"title": {"text": n1}, "type": "log" if space[1][1] == "log" else "linear"},
                ),
            )
        )
    best = max(rows, key=lambda r: r[2])
    return SolverResponse(
        result={m: [{"params": p, "score": s} for p, s in h] for m, h in histories.items()},
        steps=[
            Step(
                title="Masalah",
                explanation=f"Maksimumkan akurasi validasi silang 3-fold model {model.upper()} pada dataset {dataset} ({len(y)} sampel, {len(classes)} kelas). Ruang pencarian: "
                + "; ".join(
                    f"{n} ∈ [{lo:g}, {hi:g}]{' (skala log)' if k == 'log' else ''}"
                    if k != "cat"
                    else f"{n} ∈ {{uniform, distance}}"
                    for n, k, lo, hi in space
                )
                + ".",
            ),
            Step(
                title="Metode",
                explanation="Grid search mengevaluasi kisi seragam; random search mengambil titik acak; Bayesian optimization memodelkan akurasi dengan Gaussian process dan memilih titik dengan expected improvement terbesar; metaheuristik (PSO/DE/HHO) mencari di ruang ternormalisasi [0, 1]^d.",
                latex=r"EI(x) = (\mu(x) - f^+ - \xi)\Phi(z) + \sigma(x)\phi(z),\ z = \frac{\mu(x) - f^+ - \xi}{\sigma(x)}",
            ),
            Step(title="Hasil", table=table),
        ],
        tables=[table],
        charts=charts,
        summary=summary_items([(r[0], r[2]) for r in rows]),
        conclusion=f"Akurasi CV tertinggi {best[2]:.4f} dicapai {best[0]} dengan {best[3]}.",
    )


# =========================================================================== seleksi fitur


def feature_selection(dataset: str, wrapper: list[str], k_filter: int, alpha: float, seed: int) -> SolverResponse:
    from sklearn.feature_selection import chi2, mutual_info_classif
    from sklearn.model_selection import cross_val_score
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import MinMaxScaler, StandardScaler

    x, y, feats, classes = load_dataset(dataset, None, None, None, max_rows=800)
    d = x.shape[1]
    if not 1 <= k_filter <= d:
        raise SolverError(f"Jumlah fitur filter harus 1–{d}.")
    if not 0 < alpha <= 1:
        raise SolverError("Bobot α harus di antara 0 dan 1.")
    start = time.monotonic()
    cache: dict[tuple, float] = {}

    def acc(mask: np.ndarray) -> float:
        key = tuple(np.flatnonzero(mask))
        if not key:
            return 0.0
        if key not in cache:
            if time.monotonic() - start > TIME_LIMIT:
                raise SolverError(f"Seleksi fitur melebihi {TIME_LIMIT:.0f} detik.")
            cache[key] = float(
                cross_val_score(
                    make_pipeline(StandardScaler(), KNeighborsClassifier(5)), x[:, list(key)], y, cv=3
                ).mean()
            )
        return cache[key]

    rows = [["Semua fitur", d, _r(acc(np.ones(d, bool)), 4), "—"]]
    chosen: dict[str, list[str]] = {}
    curves = {}
    for algo in wrapper:
        if algo not in ("pso", "hho", "de", "ga", "avoa"):
            raise SolverError("Wrapper: pso, hho, de, ga, atau avoa (versi biner via fungsi transfer sigmoid).")
        best_mask = [np.ones(d, bool), math.inf]

        def obj(v, best_mask=best_mask):
            mask = 1 / (1 + np.exp(-v)) > 0.5
            f = alpha * (1 - acc(mask)) + (1 - alpha) * mask.sum() / d
            if f < best_mask[1]:
                best_mask[0], best_mask[1] = mask, f
            return f

        res = MH.run(algo, obj, [-6.0] * d, [6.0] * d, 10, 15, seed)
        mask = best_mask[0]
        curves[algo] = res.curve
        chosen[algo] = [feats[i] for i in np.flatnonzero(mask)]
        rows.append(
            [
                f"Wrapper biner {MH.ALGORITHMS[algo][0]}",
                int(mask.sum()),
                _r(acc(mask), 4),
                ", ".join(chosen[algo][:12]) + ("…" if mask.sum() > 12 else ""),
            ]
        )
    mi = mutual_info_classif(x, y, random_state=seed)
    top_mi = np.argsort(mi)[::-1][:k_filter]
    m = np.zeros(d, bool)
    m[top_mi] = True
    rows.append(
        [
            f"Filter mutual information (top {k_filter})",
            k_filter,
            _r(acc(m), 4),
            ", ".join(feats[i] for i in top_mi[:12]),
        ]
    )
    c2, _ = chi2(MinMaxScaler().fit_transform(x), y)
    top_c = np.argsort(np.nan_to_num(c2))[::-1][:k_filter]
    m = np.zeros(d, bool)
    m[top_c] = True
    rows.append(
        [f"Filter chi-square (top {k_filter})", k_filter, _r(acc(m), 4), ", ".join(feats[i] for i in top_c[:12])]
    )
    # PCA dengan SVD (ditulis manual)
    xs = (x - x.mean(axis=0)) / np.where(x.std(axis=0) == 0, 1, x.std(axis=0))
    _, sv, vt = np.linalg.svd(xs, full_matrices=False)
    ev = sv**2 / (sv**2).sum()
    z = xs @ vt[:k_filter].T
    pca_acc = float(cross_val_score(KNeighborsClassifier(5), z, y, cv=3).mean())
    rows.append(
        [
            f"PCA ({k_filter} komponen, {ev[:k_filter].sum() * 100:.1f}% variansi)",
            k_filter,
            _r(pca_acc, 4),
            "kombinasi linier semua fitur",
        ]
    )
    table = NamedTable(
        title=f"Perbandingan seleksi fitur pada {dataset} (kNN k=5, akurasi CV 3-fold)",
        columns=["Metode", "Jumlah fitur", "Akurasi", "Fitur terpilih"],
        rows=rows,
    )
    charts = [
        Chart(
            id="fs-bar",
            title="Akurasi vs jumlah fitur",
            spec=plotly_figure(
                [
                    {
                        "type": "scatter",
                        "mode": "markers+text",
                        "x": [r[1] for r in rows],
                        "y": [r[2] for r in rows],
                        "text": [r[0].split(" (")[0] for r in rows],
                        "textposition": "top center",
                        "marker": {"size": 12, "color": COLORS[: len(rows)]},
                    }
                ],
                "Akurasi vs jumlah fitur",
                xaxis={"title": {"text": "Jumlah fitur"}},
                yaxis={"title": {"text": "Akurasi CV"}},
                showlegend=False,
            ),
        ),
        Chart(
            id="pca",
            title="Variansi PCA",
            spec=plotly_figure(
                [
                    {"type": "bar", "x": list(range(1, len(ev) + 1)), "y": ev.tolist(), "name": "Proporsi variansi"},
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "x": list(range(1, len(ev) + 1)),
                        "y": np.cumsum(ev).tolist(),
                        "name": "Kumulatif",
                    },
                ],
                "Scree plot PCA",
                xaxis={"title": {"text": "Komponen"}},
            ),
        ),
    ]
    if curves:
        charts.append(
            Chart(
                id="fs-conv",
                title="Konvergensi wrapper",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "x": list(range(1, len(c) + 1)),
                            "y": c,
                            "name": MH.ALGORITHMS[a][0],
                        }
                        for a, c in curves.items()
                    ],
                    "Fitness wrapper per iterasi",
                    xaxis={"title": {"text": "Iterasi"}},
                ),
            )
        )
    best = max(rows, key=lambda r: (r[2], -r[1]))
    return SolverResponse(
        result={"rows": rows, "selected": chosen},
        steps=[
            Step(
                title="Wrapper berbasis metaheuristik biner",
                explanation="Posisi kontinu xⱼ diubah ke biner lewat fungsi transfer sigmoid (fitur dipilih bila S(xⱼ) > 0,5). Fitness menyeimbangkan galat dan jumlah fitur.",
                latex=rf"\text{{fitness}} = \alpha\,(1 - \text{{akurasi}}) + (1-\alpha)\frac{{|S|}}{{D}},\quad \alpha = {alpha:g},\quad S(x) = \frac{{1}}{{1 + e^{{-x}}}}",
            ),
            Step(
                title="Filter",
                explanation="Mutual information dan chi-square memberi skor setiap fitur secara independen terhadap target (cepat, tanpa model).",
            ),
            Step(
                title="Reduksi dimensi PCA",
                explanation="PCA memproyeksikan data ke komponen utama (SVD matriks data terstandardisasi); berbeda dengan seleksi, setiap komponen memakai semua fitur.",
                latex=r"\mathbf{X} = \mathbf{U}\boldsymbol{\Sigma}\mathbf{V}^\top,\quad \mathbf{Z} = \mathbf{X}\mathbf{V}_k",
            ),
            Step(title="Perbandingan", table=table),
        ],
        tables=[table],
        charts=charts,
        summary=summary_items([(r[0], f"{r[1]} fitur, akurasi {r[2]}") for r in rows]),
        conclusion=f"Akurasi tertinggi {best[2]:.4f} oleh {best[0]} dengan {best[1]} fitur (semua fitur: {rows[0][2]:.4f}).",
    )


# =========================================================================== metaheuristik untuk OR


def _tour_len(order, dist) -> float:
    return float(sum(dist[order[i], order[(i + 1) % len(order)]] for i in range(len(order))))


def _held_karp(dist: np.ndarray) -> tuple[float, list[int]]:
    n = len(dist)
    best: dict[tuple[int, int], tuple[float, int]] = {(1 << k, k): (dist[0, k], 0) for k in range(1, n)}
    for size in range(2, n):
        for subset in itertools.combinations(range(1, n), size):
            bits = sum(1 << b for b in subset)
            for k in subset:
                prev = bits & ~(1 << k)
                best[(bits, k)] = min((best[(prev, m)][0] + dist[m, k], m) for m in subset if m != k)
    bits = (1 << n) - 2
    opt, parent = min((best[(bits, k)][0] + dist[k, 0], k) for k in range(1, n))
    path, cur = [], parent
    while cur:
        path.append(cur)
        new_bits = bits & ~(1 << cur)
        cur = best[(bits, cur)][1]
        bits = new_bits
    return float(opt), [0] + path[::-1]


def _tsp_ga(dist, rng, pop=60, gens=300):
    n = len(dist)
    popu = [rng.permutation(n) for _ in range(pop)]
    curve = []
    for _ in range(gens):
        fit = np.array([_tour_len(p, dist) for p in popu])
        order = np.argsort(fit)
        curve.append(float(fit[order[0]]))
        new = [popu[i].copy() for i in order[:2]]
        while len(new) < pop:
            a, b = (popu[min(rng.integers(0, pop, 3), key=lambda k: fit[k])] for _ in range(2))
            i, j = sorted(rng.choice(n, 2, replace=False))
            child = -np.ones(n, int)
            child[i:j] = a[i:j]
            fill = [c for c in b if c not in child[i:j]]
            child[[k for k in range(n) if child[k] < 0]] = fill  # order crossover (OX)
            if rng.random() < 0.3:
                s, e = sorted(rng.choice(n, 2, replace=False))
                child[s : e + 1] = child[s : e + 1][::-1]  # mutasi inversi
            new.append(child)
        popu = new
    best = min(popu, key=lambda p: _tour_len(p, dist))
    return list(best), curve


def _tsp_sa(dist, rng, iters=6000):
    n = len(dist)
    cur = rng.permutation(n)
    cur_len = _tour_len(cur, dist)
    best, best_len = cur.copy(), cur_len
    temp = cur_len / n
    curve = []
    for k in range(iters):
        i, j = sorted(rng.choice(n, 2, replace=False))
        cand = cur.copy()
        cand[i : j + 1] = cand[i : j + 1][::-1]  # 2-opt
        cl = _tour_len(cand, dist)
        if cl < cur_len or rng.random() < math.exp(-(cl - cur_len) / max(temp, 1e-12)):
            cur, cur_len = cand, cl
            if cl < best_len:
                best, best_len = cand.copy(), cl
        temp *= 0.999
        if k % 20 == 0:
            curve.append(best_len)
    return list(best), curve


def tsp(coords: list[list[float]] | None, n_random: int, seed: int) -> SolverResponse:
    rng = np.random.default_rng(seed)
    pts = np.array(coords, float) if coords else rng.random((n_random, 2)) * 100
    n = len(pts)
    if pts.ndim != 2 or pts.shape[1] != 2 or not 4 <= n <= 60:
        raise SolverError("Isi 4–60 kota, masing-masing dua koordinat (x y).")
    dist = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1))
    nn = [0]
    while len(nn) < n:
        last = nn[-1]
        nn.append(min((k for k in range(n) if k not in nn), key=lambda k: dist[last, k]))
    results = {"Nearest neighbor (heuristik)": (nn, [])}
    results["Algoritma genetika (OX + inversi)"] = _tsp_ga(dist, rng)
    results["Simulated annealing (2-opt)"] = _tsp_sa(dist, rng)
    exact = None
    if n <= 11:
        exact = _held_karp(dist)
        results["Eksak: Held-Karp (DP)"] = (exact[1], [])
    rows = [
        [name, _r(_tour_len(t, dist), 4), " → ".join(str(c + 1) for c in t[:20]) + (" …" if n > 20 else "")]
        for name, (t, _) in results.items()
    ]
    if exact:
        for r in rows:
            r.append(f"{(r[1] / exact[0] - 1) * 100:.2f}%")
    table = NamedTable(
        title="Perbandingan panjang rute",
        columns=["Metode", "Panjang rute", "Urutan kota"] + (["Selisih dari optimal"] if exact else []),
        rows=rows,
    )
    route_traces = []
    for k, (name, (t, _)) in enumerate(results.items()):
        loop = list(t) + [t[0]]
        route_traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": pts[loop, 0].tolist(),
                "y": pts[loop, 1].tolist(),
                "name": name,
                "visible": True if k == 1 else "legendonly",
                "line": {"color": COLORS[k]},
            }
        )
    route_traces.append(
        {
            "type": "scatter",
            "mode": "text",
            "x": pts[:, 0].tolist(),
            "y": pts[:, 1].tolist(),
            "text": [str(i + 1) for i in range(n)],
            "textposition": "top center",
            "showlegend": False,
        }
    )
    charts = [
        Chart(
            id="tsp-route",
            title="Rute",
            spec=plotly_figure(
                route_traces, "Rute TSP (klik legenda untuk membandingkan)", height=480, yaxis={"scaleanchor": "x"}
            ),
        ),
        Chart(
            id="tsp-conv",
            title="Konvergensi",
            spec=plotly_figure(
                [{"type": "scatter", "mode": "lines", "y": c, "name": name} for name, (_, c) in results.items() if c]
                + (
                    [
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "y": [exact[0]] * 300,
                            "name": "Optimal",
                            "line": {"dash": "dash"},
                        }
                    ]
                    if exact
                    else []
                ),
                "Panjang rute terbaik",
                xaxis={"title": {"text": "Iterasi / generasi"}},
            ),
        ),
    ]
    best = min(rows, key=lambda r: r[1])
    return SolverResponse(
        result={name: _tour_len(t, dist) for name, (t, _) in results.items()}
        | {"optimal": exact[0] if exact else None},
        steps=[
            Step(
                title="Masalah TSP",
                explanation=f"{n} kota dengan jarak Euclid. Cari rute terpendek yang mengunjungi setiap kota tepat sekali lalu kembali.",
            ),
            Step(
                title="Metode",
                explanation="GA dengan order crossover (OX) dan mutasi inversi; SA dengan tetangga 2-opt; heuristik nearest neighbor; dan solusi eksak Held-Karp (DP, O(n²2ⁿ)) bila n ≤ 11.",
            ),
            Step(title="Hasil", table=table),
        ],
        tables=[table],
        charts=charts,
        summary=summary_items([(r[0], r[1]) for r in rows]),
        conclusion=f"Rute terpendek: {best[0]} dengan panjang {best[1]:.4f}"
        + (f" (optimal {exact[0]:.4f})." if exact else "."),
    )


def knapsack_meta(weights: list[float], values: list[float], capacity: float, seed: int) -> SolverResponse:
    from app.solvers import dynamic

    w, v = np.array(weights, float), np.array(values, float)
    n = w.size
    if n == 0 or v.size != n or capacity <= 0 or n > 200:
        raise SolverError("Isi 1–200 barang dengan bobot & nilai, serta kapasitas positif.")
    rng = np.random.default_rng(seed)

    def repair(mask):
        mask = mask.copy()
        while (w * mask).sum() > capacity:
            sel = np.flatnonzero(mask)
            mask[sel[np.argmin(v[sel] / w[sel])]] = False
        return mask

    def fitness(mask):
        return float((v * repair(mask)).sum())

    # GA biner
    pop = [rng.random(n) < 0.3 for _ in range(40)]
    curve_ga = []
    for _ in range(200):
        fit = np.array([fitness(p) for p in pop])
        order = np.argsort(-fit)
        curve_ga.append(float(fit[order[0]]))
        new = [pop[i].copy() for i in order[:2]]
        while len(new) < 40:
            a, b = (pop[max(rng.integers(0, 40, 3), key=lambda k: fit[k])] for _ in range(2))
            cut = rng.integers(1, n) if n > 1 else 0
            child = np.r_[a[:cut], b[cut:]]
            flip = rng.random(n) < 1 / n
            child[flip] = ~child[flip]
            new.append(child)
        pop = new
    ga_best = repair(max(pop, key=fitness))
    # SA biner
    cur = repair(rng.random(n) < 0.3)
    cur_v = fitness(cur)
    best_sa, best_v = cur.copy(), cur_v
    temp = max(v.max(), 1.0)
    curve_sa = []
    for k in range(4000):
        cand = cur.copy()
        j = rng.integers(n)
        cand[j] = ~cand[j]
        cv = fitness(cand)
        if cv > cur_v or rng.random() < math.exp((cv - cur_v) / max(temp, 1e-12)):
            cur, cur_v = repair(cand), cv
            if cv > best_v:
                best_sa, best_v = cur.copy(), cv
        temp *= 0.998
        if k % 20 == 0:
            curve_sa.append(best_v)
    rows = [
        [
            "GA biner (repair rakus)",
            _r(float((v * ga_best).sum()), 4),
            _r(float((w * ga_best).sum()), 4),
            int(ga_best.sum()),
        ],
        ["Simulated annealing", _r(best_v, 4), _r(float((w * best_sa).sum()), 4), int(best_sa.sum())],
    ]
    exact_v = None
    if np.allclose(w, np.round(w)) and capacity <= 5000:
        exact_v = dynamic.knapsack([int(x) for x in w], v.tolist(), int(capacity), None, None).result["value"]
        rows.append(["Eksak: DP (Bab 11)", _r(exact_v, 4), "—", "—"])
    table = NamedTable(
        title="Knapsack 0-1", columns=["Metode", "Nilai total", "Bobot terpakai", "Jumlah barang"], rows=rows
    )
    return SolverResponse(
        result={"ga": float((v * ga_best).sum()), "sa": best_v, "exact": exact_v},
        steps=[
            Step(
                title="Knapsack 0-1",
                explanation=f"{n} barang, kapasitas {capacity:g}. Solusi tidak layak diperbaiki dengan membuang barang berasio nilai/bobot terkecil (repair).",
            ),
            Step(title="Hasil", table=table),
        ],
        tables=[table],
        charts=[
            Chart(
                id="ks-conv",
                title="Konvergensi",
                spec=plotly_figure(
                    [
                        {"type": "scatter", "mode": "lines", "y": curve_ga, "name": "GA"},
                        {"type": "scatter", "mode": "lines", "y": curve_sa, "name": "SA"},
                    ]
                    + (
                        [
                            {
                                "type": "scatter",
                                "mode": "lines",
                                "y": [exact_v] * 200,
                                "name": "Optimal (DP)",
                                "line": {"dash": "dash"},
                            }
                        ]
                        if exact_v is not None
                        else []
                    ),
                    "Nilai terbaik",
                    xaxis={"title": {"text": "Generasi / iterasi"}},
                ),
            )
        ],
        summary=summary_items([(r[0], r[1]) for r in rows]),
        conclusion=f"GA = {rows[0][1]}, SA = {rows[1][1]}"
        + (f", optimal (DP) = {exact_v:g}." if exact_v is not None else "."),
    )


def scheduling(processing: list[float], weights: list[float], due: list[float], seed: int) -> SolverResponse:
    p, w, d = (np.array(a, float) for a in (processing, weights, due))
    n = p.size
    if n < 2 or w.size != n or d.size != n or n > 50:
        raise SolverError("Isi 2–50 pekerjaan dengan waktu proses, bobot, dan tenggat yang sama banyak.")
    rng = np.random.default_rng(seed)

    def cost(order):
        t = np.cumsum(p[order])
        return float((w[order] * np.maximum(t - d[order], 0)).sum())

    edd = list(np.argsort(d))
    wspt = list(np.argsort(-w / p))
    cur = list(edd)
    cur_c = cost(cur)
    best, best_c = cur[:], cur_c
    temp = max(cur_c, 1.0)
    curve = []
    for k in range(5000):
        i, j = rng.choice(n, 2, replace=False)
        cand = cur[:]
        cand[i], cand[j] = cand[j], cand[i]
        cc = cost(cand)
        if cc < cur_c or rng.random() < math.exp(-(cc - cur_c) / max(temp, 1e-12)):
            cur, cur_c = cand, cc
            if cc < best_c:
                best, best_c = cand[:], cc
        temp *= 0.998
        if k % 25 == 0:
            curve.append(best_c)
    rows = [
        ["EDD (earliest due date)", _r(cost(edd), 4), " → ".join(f"J{i + 1}" for i in edd)],
        ["WSPT (rasio bobot/waktu)", _r(cost(wspt), 4), " → ".join(f"J{i + 1}" for i in wspt)],
        ["Simulated annealing (swap)", _r(best_c, 4), " → ".join(f"J{i + 1}" for i in best)],
    ]
    exact = None
    if n <= 12:  # DP subset (Held-Karp-like) untuk total weighted tardiness
        full = (1 << n) - 1
        dp = {0: 0.0}
        par = {}
        tsum = {0: 0.0}
        for mask in range(1, full + 1):
            tm = sum(p[i] for i in range(n) if mask >> i & 1)
            tsum[mask] = tm
            best_v, best_j = math.inf, -1
            for j in range(n):
                if mask >> j & 1:
                    prev = mask & ~(1 << j)
                    val = dp[prev] + w[j] * max(tm - d[j], 0)
                    if val < best_v:
                        best_v, best_j = val, j
            dp[mask], par[mask] = best_v, best_j
        seq, mask = [], full
        while mask:
            j = par[mask]
            seq.append(j)
            mask &= ~(1 << j)
        exact = (dp[full], seq[::-1])
        rows.append(["Eksak: DP subset", _r(exact[0], 4), " → ".join(f"J{i + 1}" for i in exact[1])])
    table = NamedTable(
        title="Penjadwalan satu mesin: total weighted tardiness", columns=["Metode", "Σ wⱼTⱼ", "Urutan"], rows=rows
    )
    best_order = exact[1] if exact else best
    starts = np.r_[0, np.cumsum(p[best_order])[:-1]]
    gantt = plotly_figure(
        [
            {
                "type": "bar",
                "orientation": "h",
                "y": ["Mesin"] * n,
                "x": p[best_order].tolist(),
                "base": starts.tolist(),
                "text": [f"J{i + 1}" for i in best_order],
                "textposition": "inside",
                "marker": {
                    "color": ["#ef4444" if starts[k] + p[i] > d[i] else "#10b981" for k, i in enumerate(best_order)]
                },
                "showlegend": False,
            }
        ],
        "Gantt urutan terbaik (merah = terlambat)",
        barmode="stack",
        height=240,
        xaxis={"title": {"text": "Waktu"}},
    )
    return SolverResponse(
        result={"sa": best_c, "exact": exact[0] if exact else None},
        steps=[
            Step(
                title="Masalah",
                latex=r"\min \sum_j w_j \max(0, C_j - d_j)",
                explanation="Urutkan pekerjaan pada satu mesin untuk meminimumkan total keterlambatan berbobot (NP-hard).",
            ),
            Step(title="Hasil", table=table),
        ],
        tables=[table],
        charts=[
            Chart(id="gantt", title="Gantt", spec=gantt),
            Chart(
                id="sched-conv",
                title="Konvergensi SA",
                spec=plotly_figure(
                    [{"type": "scatter", "mode": "lines", "y": curve, "name": "SA"}],
                    "Konvergensi simulated annealing",
                    xaxis={"title": {"text": "Iterasi (×25)"}},
                ),
            ),
        ],
        summary=summary_items([(r[0], r[1]) for r in rows]),
        conclusion=f"SA memberi Σ wT = {best_c:g}" + (f"; optimal = {exact[0]:g}." if exact else "."),
    )


# =========================================================================== reinforcement learning: gridworld

ACTIONS = [(-1, 0, "↑"), (0, 1, "→"), (1, 0, "↓"), (0, -1, "←")]


def gridworld(
    grid: str,
    goal_reward: float,
    trap_reward: float,
    step_cost: float,
    gamma: float,
    alpha: float,
    epsilon: float,
    episodes: int,
    slip: float,
    seed: int,
) -> SolverResponse:
    rows_txt = [ln.split() for ln in grid.strip().split("\n") if ln.strip()]
    if not rows_txt or len({len(r) for r in rows_txt}) != 1:
        raise SolverError("Peta grid harus persegi panjang; pisahkan sel dengan spasi (S, G, T, #, .).")
    h, w = len(rows_txt), len(rows_txt[0])
    cells = {(i, j): c.upper() for i, r in enumerate(rows_txt) for j, c in enumerate(r)}
    if any(c not in "SGT#." for c in cells.values()):
        raise SolverError("Sel hanya boleh S (start), G (goal), T (jebakan), # (dinding), atau . (kosong).")
    starts = [k for k, c in cells.items() if c == "S"]
    if len(starts) != 1 or not any(c == "G" for c in cells.values()):
        raise SolverError("Peta harus memiliki tepat satu S dan minimal satu G.")
    if not (0 < gamma < 1 and 0 < alpha <= 1 and 0 <= epsilon <= 1 and 0 <= slip < 1 and 1 <= episodes <= 20000):
        raise SolverError("Parameter: 0<γ<1, 0<α≤1, 0≤ε≤1, 0≤slip<1, episode 1–20000.")
    states = [k for k, c in cells.items() if c != "#"]
    terminal = {k for k, c in cells.items() if c in "GT"}

    def move(s, a):
        ni, nj = s[0] + ACTIONS[a][0], s[1] + ACTIONS[a][1]
        return (ni, nj) if 0 <= ni < h and 0 <= nj < w and cells[(ni, nj)] != "#" else s

    def reward(s2):
        c = cells[s2]
        return goal_reward if c == "G" else trap_reward if c == "T" else -step_cost

    def outcomes(s, a):
        res = [(1 - slip, move(s, a))]
        if slip:
            for side in ((a + 1) % 4, (a + 3) % 4):
                res.append((slip / 2, move(s, side)))
        return res

    # value iteration (MDP Bab 21) sebagai acuan optimal
    v = {s: 0.0 for s in states}
    for _ in range(2000):
        delta = 0.0
        for s in states:
            if s in terminal:
                continue
            best = max(
                sum(pr * (reward(s2) + gamma * (0 if s2 in terminal else v[s2])) for pr, s2 in outcomes(s, a))
                for a in range(4)
            )
            delta = max(delta, abs(best - v[s]))
            v[s] = best
        if delta < 1e-9:
            break
    pi_vi = {
        s: max(
            range(4),
            key=lambda a, s=s: sum(
                pr * (reward(s2) + gamma * (0 if s2 in terminal else v[s2])) for pr, s2 in outcomes(s, a)
            ),
        )
        for s in states
        if s not in terminal
    }
    # Q-learning
    rng = np.random.default_rng(seed)
    q = {s: np.zeros(4) for s in states}
    returns = []
    max_steps = 4 * h * w
    for ep in range(episodes):
        s = starts[0]
        total = 0.0
        eps = max(0.01, epsilon * (1 - ep / episodes))
        for _ in range(max_steps):
            a = int(rng.integers(4)) if rng.random() < eps else int(np.argmax(q[s]))
            r_ = rng.random()
            acc = 0.0
            s2 = s
            for pr, nxt in outcomes(s, a):
                acc += pr
                if r_ <= acc:
                    s2 = nxt
                    break
            rwd = reward(s2)
            total += rwd
            target = rwd + (0 if s2 in terminal else gamma * q[s2].max())
            q[s][a] += alpha * (target - q[s][a])
            s = s2
            if s in terminal:
                break
        returns.append(total)
    pi_q = {s: int(np.argmax(q[s])) for s in states if s not in terminal}
    agree = sum(pi_q[s] == pi_vi[s] or abs(q[s][pi_vi[s]] - q[s].max()) < 1e-6 for s in pi_q) / max(1, len(pi_q))

    def heat(values, policy, title):
        z = [[None if cells[(i, j)] == "#" else values.get((i, j), 0.0) for j in range(w)] for i in range(h)]
        ann = []
        for (i, j), c in cells.items():
            if c == "#":
                txt = "█"
            elif c in "GT":
                txt = c
            else:
                txt = ACTIONS[policy[(i, j)]][2] + ("<br>S" if c == "S" else "")
            ann.append({"x": j, "y": i, "text": txt, "showarrow": False, "font": {"size": 16, "color": "#111"}})
        return plotly_figure(
            [{"type": "heatmap", "z": z, "colorscale": "RdYlGn", "reversescale": True, "showscale": True}],
            title,
            yaxis={"autorange": "reversed", "visible": False},
            xaxis={"visible": False},
            annotations=ann,
            height=80 * h + 120,
        )

    v_q = {s: float(q[s].max()) for s in states}
    window = max(1, episodes // 50)
    smooth = np.convolve(returns, np.ones(window) / window, mode="valid")
    table = NamedTable(
        title="Nilai state: Q-learning vs value iteration",
        columns=["Sel (baris, kolom)", "V* (value iteration)", "max Q (Q-learning)", "Aksi VI", "Aksi Q"],
        rows=[
            [
                f"({i + 1}, {j + 1})",
                _r(v[(i, j)], 4),
                _r(v_q[(i, j)], 4),
                ACTIONS[pi_vi[(i, j)]][2],
                ACTIONS[pi_q[(i, j)]][2],
            ]
            for (i, j) in states
            if (i, j) not in terminal
        ],
    )
    return SolverResponse(
        result={"policy_agreement": agree, "returns": returns[-50:]},
        steps=[
            Step(
                title="Gridworld sebagai MDP",
                explanation=f"State = sel, aksi = ↑ → ↓ ←, peluang tergelincir {slip:g} ke samping. Imbalan: goal {goal_reward:g}, jebakan {trap_reward:g}, setiap langkah −{step_cost:g}. Faktor diskon γ = {gamma:g}.",
            ),
            Step(
                title="Acuan: value iteration (Bab 21)",
                latex=r"V(s) \leftarrow \max_a \sum_{s'} p(s' \mid s, a)\,[r(s') + \gamma V(s')]",
                explanation="Model transisi diketahui sehingga nilai optimal dapat dihitung langsung.",
            ),
            Step(
                title="Q-learning (tanpa model)",
                latex=r"Q(s,a) \leftarrow Q(s,a) + \alpha\left[r + \gamma\max_{a'}Q(s',a') - Q(s,a)\right]",
                explanation=f"Agen belajar dari pengalaman dengan kebijakan ε-greedy (ε menurun dari {epsilon:g} ke 0,01), α = {alpha:g}, {episodes} episode.",
            ),
            Step(
                title="Perbandingan",
                explanation=f"Kebijakan Q-learning sama dengan kebijakan optimal pada {agree * 100:.1f}% state nonterminal.",
                table=table,
            ),
        ],
        tables=[table],
        charts=[
            Chart(id="vi", title="Value iteration", spec=heat(v, pi_vi, "Kebijakan & nilai optimal (value iteration)")),
            Chart(id="ql", title="Q-learning", spec=heat(v_q, pi_q, "Kebijakan & nilai hasil Q-learning")),
            Chart(
                id="returns",
                title="Kurva belajar",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "y": smooth.tolist(),
                            "name": f"Rata-rata bergerak {window} episode",
                        }
                    ],
                    "Total imbalan per episode",
                    xaxis={"title": {"text": "Episode"}},
                ),
            ),
        ],
        summary=summary_items(
            [
                ("Kesesuaian kebijakan dengan optimal", f"{agree * 100:.1f}%"),
                ("V*(start)", _r(v[starts[0]], 4)),
                ("max Q(start)", _r(v_q[starts[0]], 4)),
            ]
        ),
        conclusion=f"Q-learning mempelajari kebijakan yang sama dengan kebijakan optimal MDP pada {agree * 100:.1f}% state.",
    )
