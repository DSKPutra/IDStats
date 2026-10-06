"""Modul C1: playground permukaan loss 2D/3D dan pelatihan model nyata (regresi logistik & MLP) untuk
membandingkan optimizer berbasis gradien."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step
from app.solvers._base import plotly_figure, summary_items
from app.solvers.ml.optimizers import SPECS, Optimizer

COLORS = [
    "#6366f1",
    "#ef4444",
    "#10b981",
    "#f59e0b",
    "#06b6d4",
    "#a855f7",
    "#ec4899",
    "#84cc16",
    "#64748b",
    "#f97316",
    "#14b8a6",
    "#8b5cf6",
    "#0ea5e9",
    "#d946ef",
]


@dataclass
class TestFunction:
    id: str
    title: str
    f: Callable[[float, float], float]
    bounds: tuple[tuple[float, float], tuple[float, float]]
    start: tuple[float, float]
    minima: list[tuple[float, float]]
    latex: str
    log_scale: bool = False


def _ackley(x, y):
    return (
        -20 * np.exp(-0.2 * np.sqrt(0.5 * (x * x + y * y)))
        - np.exp(0.5 * (np.cos(2 * np.pi * x) + np.cos(2 * np.pi * y)))
        + np.e
        + 20
    )


FUNCTIONS: dict[str, TestFunction] = {
    t.id: t
    for t in [
        TestFunction(
            "sphere", "Sphere", lambda x, y: x * x + y * y, ((-5, 5), (-5, 5)), (-4.0, 3.0), [(0, 0)], r"f = x^2 + y^2"
        ),
        TestFunction(
            "rosenbrock",
            "Rosenbrock",
            lambda x, y: (1 - x) ** 2 + 100 * (y - x * x) ** 2,
            ((-2, 2), (-1, 3)),
            (-1.5, 2.0),
            [(1, 1)],
            r"f = (1-x)^2 + 100(y - x^2)^2",
            True,
        ),
        TestFunction(
            "rastrigin",
            "Rastrigin",
            lambda x, y: 20 + x * x - 10 * np.cos(2 * np.pi * x) + y * y - 10 * np.cos(2 * np.pi * y),
            ((-5.12, 5.12), (-5.12, 5.12)),
            (-4.2, 3.7),
            [(0, 0)],
            r"f = 20 + \sum (x_i^2 - 10\cos 2\pi x_i)",
        ),
        TestFunction(
            "ackley",
            "Ackley",
            _ackley,
            ((-5, 5), (-5, 5)),
            (-3.5, 3.0),
            [(0, 0)],
            r"f = -20e^{-0.2\sqrt{0.5(x^2+y^2)}} - e^{0.5(\cos 2\pi x + \cos 2\pi y)} + e + 20",
        ),
        TestFunction(
            "beale",
            "Beale",
            lambda x, y: (1.5 - x + x * y) ** 2 + (2.25 - x + x * y * y) ** 2 + (2.625 - x + x * y**3) ** 2,
            ((-4.5, 4.5), (-4.5, 4.5)),
            (1.0, 1.5),
            [(3, 0.5)],
            r"f = (1.5 - x + xy)^2 + (2.25 - x + xy^2)^2 + (2.625 - x + xy^3)^2",
            True,
        ),
        TestFunction(
            "himmelblau",
            "Himmelblau",
            lambda x, y: (x * x + y - 11) ** 2 + (x + y * y - 7) ** 2,
            ((-5, 5), (-5, 5)),
            (-0.5, -0.5),
            [(3, 2), (-2.805118, 3.131312), (-3.779310, -3.283186), (3.584428, -1.848126)],
            r"f = (x^2 + y - 11)^2 + (x + y^2 - 7)^2",
            True,
        ),
        TestFunction(
            "booth",
            "Booth",
            lambda x, y: (x + 2 * y - 7) ** 2 + (2 * x + y - 5) ** 2,
            ((-10, 10), (-10, 10)),
            (-8.0, -8.0),
            [(1, 3)],
            r"f = (x + 2y - 7)^2 + (2x + y - 5)^2",
            True,
        ),
        TestFunction(
            "styblinski-tang",
            "Styblinski-Tang",
            lambda x, y: 0.5 * (x**4 - 16 * x * x + 5 * x + y**4 - 16 * y * y + 5 * y),
            ((-5, 5), (-5, 5)),
            (0.5, 4.5),
            [(-2.903534, -2.903534)],
            r"f = \tfrac12\sum (x_i^4 - 16x_i^2 + 5x_i)",
        ),
    ]
}


def _grad(tf: TestFunction, p: np.ndarray) -> np.ndarray:
    h = 1e-6
    x, y = p
    return np.array([(tf.f(x + h, y) - tf.f(x - h, y)) / (2 * h), (tf.f(x, y + h) - tf.f(x, y - h)) / (2 * h)])


def playground(function: str, optimizers: list[dict], start: list[float] | None, iterations: int) -> SolverResponse:
    tf = FUNCTIONS.get(function)
    if tf is None:
        raise SolverError("Fungsi uji tidak dikenal.")
    if not optimizers or len(optimizers) > 8:
        raise SolverError("Pilih 1–8 optimizer.")
    if not 1 <= iterations <= 2000:
        raise SolverError("Jumlah iterasi 1–2000.")
    x0 = np.array(start if start else tf.start, dtype=float)
    if x0.size != 2:
        raise SolverError("Titik awal harus 2 nilai (x, y).")
    fmin = min(tf.f(*m) for m in tf.minima)
    paths: dict[str, np.ndarray] = {}
    rows = []
    labels = []
    for k, cfg in enumerate(optimizers):
        oid = cfg.get("id")
        opt = Optimizer(oid, {kk: float(v) for kk, v in (cfg.get("params") or {}).items()})
        label = f"{SPECS[oid].title}" + (f" #{k + 1}" if [c.get("id") for c in optimizers].count(oid) > 1 else "")
        labels.append(label)
        p = x0.copy()
        traj = [p.copy()]
        hit = None
        for t in range(iterations):
            g = _grad(tf, p)
            if not np.all(np.isfinite(g)):
                break
            opt.step([p], [g])
            if not np.all(np.isfinite(p)) or np.max(np.abs(p)) > 1e6:
                break
            traj.append(p.copy())
            if hit is None and tf.f(*p) - fmin < 1e-4:
                hit = t + 1
        arr = np.array(traj)
        paths[label] = arr
        final = arr[-1]
        dist = min(math.dist(final, m) for m in tf.minima)
        rows.append(
            [
                label,
                f"({final[0]:.4f}, {final[1]:.4f})",
                float(tf.f(*final)),
                float(dist),
                hit if hit is not None else "—",
                "divergen" if len(arr) < iterations + 1 else "selesai",
            ]
        )
    (xlo, xhi), (ylo, yhi) = tf.bounds
    xs, ys = np.linspace(xlo, xhi, 120), np.linspace(ylo, yhi, 120)
    xx, yy = np.meshgrid(xs, ys)
    zz = tf.f(xx, yy)
    zplot = np.log10(zz - fmin + 1) if tf.log_scale else zz
    contour = {
        "type": "contour",
        "x": xs.tolist(),
        "y": ys.tolist(),
        "z": np.round(zplot, 5).tolist(),
        "colorscale": "Viridis",
        "showscale": False,
        "contours": {"coloring": "heatmap"},
        "name": "f",
        "hoverinfo": "skip",
    }
    stride = max(1, iterations // 120)
    traces = [contour]
    for k, (label, arr) in enumerate(paths.items()):
        sub = arr[::stride]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "x": sub[:, 0].tolist(),
                "y": sub[:, 1].tolist(),
                "line": {"color": COLORS[k % len(COLORS)], "width": 2},
                "name": label,
            }
        )
    traces.append(
        {
            "type": "scatter",
            "mode": "markers",
            "x": [m[0] for m in tf.minima],
            "y": [m[1] for m in tf.minima],
            "marker": {"symbol": "star", "size": 14, "color": "#ffffff", "line": {"color": "#000", "width": 1}},
            "name": "Minimum global",
        }
    )
    # animasi: titik bergerak di setiap frame
    n_frames = min(60, max(len(a) for a in paths.values()))
    frame_idx = np.linspace(0, max(len(a) for a in paths.values()) - 1, n_frames).astype(int)
    point_traces = [
        {
            "type": "scatter",
            "mode": "markers",
            "x": [float(arr[0, 0])],
            "y": [float(arr[0, 1])],
            "marker": {"size": 12, "color": COLORS[k % len(COLORS)], "line": {"color": "#fff", "width": 1}},
            "name": f"{label} (posisi)",
            "showlegend": False,
        }
        for k, (label, arr) in enumerate(paths.items())
    ]
    base = len(traces)
    frames = [
        {
            "name": str(int(i)),
            "data": [
                {"x": [float(arr[min(i, len(arr) - 1), 0])], "y": [float(arr[min(i, len(arr) - 1), 1])]}
                for arr in paths.values()
            ],
            "traces": list(range(base, base + len(paths))),
        }
        for i in frame_idx
    ]
    anim = plotly_figure(
        traces + point_traces,
        f"Lintasan optimizer pada fungsi {tf.title}" + (" (kontur log)" if tf.log_scale else ""),
        xaxis={"title": {"text": "x"}, "range": [xlo, xhi]},
        yaxis={"title": {"text": "y"}, "range": [ylo, yhi]},
        height=520,
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
                                "frame": {"duration": 80, "redraw": False},
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
                "currentvalue": {"prefix": "Iterasi: "},
                "steps": [
                    {
                        "label": str(int(i)),
                        "method": "animate",
                        "args": [[str(int(i))], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                    }
                    for i in frame_idx
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
                "x": list(range(len(arr))),
                "y": [max(float(tf.f(*q) - fmin), 1e-12) for q in arr],
                "name": label,
                "line": {"color": COLORS[k % len(COLORS)]},
            }
            for k, (label, arr) in enumerate(paths.items())
        ],
        "Konvergensi: f(x) − f* (skala log)",
        xaxis={"title": {"text": "Iterasi"}},
        yaxis={"title": {"text": "f − f*"}, "type": "log"},
    )
    surface = plotly_figure(
        [
            {
                "type": "surface",
                "x": xs[::2].tolist(),
                "y": ys[::2].tolist(),
                "z": np.round(zplot[::2, ::2], 4).tolist(),
                "colorscale": "Viridis",
                "opacity": 0.85,
                "showscale": False,
            }
        ]
        + [
            {
                "type": "scatter3d",
                "mode": "lines",
                "x": arr[::stride, 0].tolist(),
                "y": arr[::stride, 1].tolist(),
                "z": [float(np.log10(tf.f(*q) - fmin + 1) if tf.log_scale else tf.f(*q)) for q in arr[::stride]],
                "line": {"color": COLORS[k % len(COLORS)], "width": 6},
                "name": label,
            }
            for k, (label, arr) in enumerate(paths.items())
        ],
        f"Permukaan 3D {tf.title}",
        height=520,
        scene={
            "xaxis": {"title": {"text": "x"}},
            "yaxis": {"title": {"text": "y"}},
            "zaxis": {"title": {"text": "log(f − f* + 1)" if tf.log_scale else "f"}},
        },
    )
    table = NamedTable(
        title="Hasil akhir",
        columns=["Optimizer", "x akhir", "f(x)", "Jarak ke minimum terdekat", "Iterasi sampai f − f* < 10⁻⁴", "Status"],
        rows=rows,
    )
    best = min(rows, key=lambda r: r[2])
    steps = [
        Step(
            title=f"Fungsi uji: {tf.title}",
            latex=tf.latex,
            explanation=f"Minimum global f* = {fmin:.6g} di "
            + ", ".join(f"({a:g}, {b:g})" for a, b in tf.minima)
            + f". Titik awal ({x0[0]:g}, {x0[1]:g}), {iterations} iterasi; gradien dihitung numerik.",
        )
    ]
    for cfg in optimizers:
        s = SPECS[cfg["id"]]
        hp = {**s.defaults, **(cfg.get("params") or {})}
        steps.append(
            Step(
                title=s.title,
                explanation=s.notes + " Hiperparameter: " + ", ".join(f"{k} = {v:g}" for k, v in hp.items()) + ".",
                latex=s.formula,
            )
        )
    steps.append(Step(title="Perbandingan", table=table))
    return SolverResponse(
        result={"paths": {k: v.tolist() for k, v in paths.items()}, "final": {r[0]: r[2] for r in rows}},
        steps=steps,
        tables=[table],
        charts=[
            Chart(id="trajectories", title="Lintasan (animasi)", spec=anim),
            Chart(id="convergence", title="Konvergensi", spec=conv),
            Chart(id="surface", title="Permukaan 3D", spec=surface),
        ],
        summary=summary_items([(r[0], f"f = {r[2]:.6g}") for r in rows] + [("Terbaik", best[0])]),
        conclusion=f"Pada fungsi {tf.title}, nilai akhir terkecil dicapai {best[0]} (f = {best[2]:.6g}).",
    )


# =========================================================================== pelatihan model nyata


def load_dataset(
    name: str, columns: list[str] | None, rows: list[list] | None, target: str | None, max_rows: int = 2000
):
    from sklearn import datasets

    if name == "csv":
        if not columns or not rows or not target:
            raise SolverError("Dataset CSV memerlukan kolom, baris, dan nama kolom target.")
        if target not in columns:
            raise SolverError(f"Kolom target “{target}” tidak ada.")
        ti = columns.index(target)
        feats = [j for j in range(len(columns)) if j != ti]
        x, y_raw = [], []
        for r in rows[:max_rows]:
            try:
                vals = [float(r[j]) for j in feats]
            except (TypeError, ValueError):
                continue
            if r[ti] is None or any(math.isnan(v) for v in vals):
                continue
            x.append(vals)
            y_raw.append(str(r[ti]))
        if len(x) < 10:
            raise SolverError("Dataset CSV terlalu kecil atau fitur tidak numerik (minimal 10 baris lengkap).")
        classes = sorted(set(y_raw))
        if len(classes) < 2 or len(classes) > 20:
            raise SolverError("Target harus memiliki 2–20 kelas.")
        return np.array(x), np.array([classes.index(v) for v in y_raw]), [columns[j] for j in feats], classes
    loaders = {
        "iris": datasets.load_iris,
        "breast_cancer": datasets.load_breast_cancer,
        "wine": datasets.load_wine,
        "digits": datasets.load_digits,
    }
    if name not in loaders:
        raise SolverError("Dataset harus iris, breast_cancer, wine, digits (subset MNIST 8×8), atau csv.")
    d = loaders[name]()
    return d.data[:max_rows], d.target[:max_rows], list(map(str, d.feature_names)), [str(c) for c in d.target_names]


def _split(x, y, test_frac: float, seed: int):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(y))
    n_test = max(1, int(round(len(y) * test_frac)))
    te, tr = idx[:n_test], idx[n_test:]
    mu, sd = x[tr].mean(axis=0), x[tr].std(axis=0)
    sd[sd == 0] = 1
    return (x[tr] - mu) / sd, y[tr], (x[te] - mu) / sd, y[te]


class Model:
    """Regresi logistik softmax (hidden = 0) atau MLP satu lapisan tersembunyi ReLU."""

    def __init__(self, n_in: int, n_out: int, hidden: int, seed: int):
        rng = np.random.default_rng(seed)
        if hidden:
            self.params = [
                rng.normal(0, math.sqrt(2 / n_in), (n_in, hidden)),
                np.zeros(hidden),
                rng.normal(0, math.sqrt(1 / hidden), (hidden, n_out)),
                np.zeros(n_out),
            ]
        else:
            self.params = [rng.normal(0, 0.01, (n_in, n_out)), np.zeros(n_out)]
        self.hidden = hidden

    def forward(self, x):
        if self.hidden:
            w1, b1, w2, b2 = self.params
            h = np.maximum(x @ w1 + b1, 0)
            return h @ w2 + b2, h
        w, b = self.params
        return x @ w + b, None

    def loss_grad(self, x, y, n_out):
        logits, h = self.forward(x)
        logits = logits - logits.max(axis=1, keepdims=True)
        p = np.exp(logits)
        p /= p.sum(axis=1, keepdims=True)
        n = len(y)
        loss = float(-np.log(p[np.arange(n), y] + 1e-12).mean())
        d = p.copy()
        d[np.arange(n), y] -= 1
        d /= n
        if self.hidden:
            w1, b1, w2, b2 = self.params
            gw2, gb2 = h.T @ d, d.sum(axis=0)
            dh = (d @ w2.T) * (h > 0)
            return loss, [x.T @ dh, dh.sum(axis=0), gw2, gb2]
        return loss, [x.T @ d, d.sum(axis=0)]

    def evaluate(self, x, y, n_out):
        loss, _ = self.loss_grad(x, y, n_out)
        logits, _ = self.forward(x)
        return loss, float((logits.argmax(axis=1) == y).mean())


def train(
    dataset: str,
    model: str,
    hidden: int,
    optimizers: list[dict],
    epochs: int,
    batch_size: int,
    seed: int,
    columns=None,
    rows=None,
    target=None,
) -> SolverResponse:
    if not optimizers or len(optimizers) > 6:
        raise SolverError("Pilih 1–6 optimizer.")
    if not 1 <= epochs <= 300 or not 1 <= batch_size <= 2048:
        raise SolverError("Gunakan 1–300 epoch dan batch size 1–2048.")
    x, y, feats, classes = load_dataset(dataset, columns, rows, target)
    xtr, ytr, xte, yte = _split(x, y, 0.2, seed)
    n_out = len(classes)
    h = hidden if model == "mlp" else 0
    if model == "mlp" and not 2 <= hidden <= 256:
        raise SolverError("Jumlah neuron tersembunyi 2–256.")
    curves = {}
    rows_out = []
    budget = epochs * max(1, len(ytr) // batch_size) * len(optimizers) * (xtr.shape[1] * (h or n_out))
    if budget > 4e9:
        raise SolverError(
            "Konfigurasi terlalu berat untuk dijalankan di server; kurangi epoch, optimizer, atau neuron."
        )
    for k, cfg in enumerate(optimizers):
        oid = cfg.get("id")
        opt = Optimizer(oid, {kk: float(v) for kk, v in (cfg.get("params") or {}).items()})
        net = Model(xtr.shape[1], n_out, h, seed)
        rng = np.random.default_rng(seed + 1)
        tr_loss, te_loss, te_acc = [], [], []
        for _ in range(epochs):
            perm = rng.permutation(len(ytr))
            for s in range(0, len(ytr), batch_size):
                b = perm[s : s + batch_size]
                _, grads = net.loss_grad(xtr[b], ytr[b], n_out)
                opt.step(net.params, grads)
            if not all(np.all(np.isfinite(p)) for p in net.params):
                break
            l1, _ = net.evaluate(xtr, ytr, n_out)
            l2, acc = net.evaluate(xte, yte, n_out)
            tr_loss.append(l1)
            te_loss.append(l2)
            te_acc.append(acc)
        label = SPECS[oid].title + (f" #{k + 1}" if [c.get("id") for c in optimizers].count(oid) > 1 else "")
        curves[label] = (tr_loss, te_loss, te_acc)
        rows_out.append(
            [
                label,
                round(tr_loss[-1], 6) if tr_loss else "divergen",
                round(te_loss[-1], 6) if te_loss else "—",
                round(te_acc[-1], 4) if te_acc else "—",
                (int(np.argmax(te_acc)) + 1) if te_acc else "—",
            ]
        )
    table = NamedTable(
        title="Ringkasan pelatihan",
        columns=["Optimizer", "Loss latih akhir", "Loss uji akhir", "Akurasi uji akhir", "Epoch akurasi terbaik"],
        rows=rows_out,
    )

    def fig(idx: int, title: str, ylab: str, log: bool = False) -> dict:
        return plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": list(range(1, len(c[idx]) + 1)),
                    "y": c[idx],
                    "name": label,
                    "line": {"color": COLORS[k % len(COLORS)]},
                }
                for k, (label, c) in enumerate(curves.items())
            ],
            title,
            xaxis={"title": {"text": "Epoch"}},
            yaxis={"title": {"text": ylab}, **({"type": "log"} if log else {})},
        )

    valid = [r for r in rows_out if isinstance(r[3], float)]
    best = max(valid, key=lambda r: r[3]) if valid else None
    model_txt = f"MLP (1 lapisan tersembunyi, {h} neuron ReLU)" if h else "regresi logistik softmax"
    return SolverResponse(
        result={"curves": {k: {"train_loss": v[0], "test_loss": v[1], "test_acc": v[2]} for k, v in curves.items()}},
        steps=[
            Step(
                title="Data",
                explanation=f"Dataset {dataset}: {len(y)} sampel, {x.shape[1]} fitur, {n_out} kelas. Dibagi 80% latih / 20% uji, fitur distandardisasi dengan statistik data latih.",
            ),
            Step(
                title="Model & loss",
                explanation=f"Model {model_txt}; loss cross-entropy. Mini-batch {batch_size}, {epochs} epoch, inisialisasi bobot sama untuk semua optimizer (seed {seed}).",
                latex=r"\mathcal{L} = -\frac{1}{n}\sum_i \log \mathrm{softmax}(f_\theta(x_i))_{y_i}",
            ),
            Step(title="Hasil", table=table),
        ],
        tables=[table],
        charts=[
            Chart(id="train-loss", title="Loss latih", spec=fig(0, "Loss latih per epoch", "Loss", True)),
            Chart(id="test-acc", title="Akurasi uji", spec=fig(2, "Akurasi data uji per epoch", "Akurasi")),
            Chart(id="test-loss", title="Loss uji", spec=fig(1, "Loss uji per epoch", "Loss", True)),
        ],
        summary=summary_items([(r[0], f"akurasi {r[3]}") for r in rows_out] + ([("Terbaik", best[0])] if best else [])),
        conclusion=(
            f"Akurasi uji tertinggi dicapai {best[0]} ({best[3]:.4f})."
            if best
            else "Semua optimizer divergen; turunkan learning rate."
        ),
    )
