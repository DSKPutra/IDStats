"""Modul C1: verifikasi rumus optimizer terhadap perhitungan tangan & referensi."""

import math

import numpy as np
import pytest

from app.core.errors import SolverError
from app.solvers.ml import gradient
from app.solvers.ml.optimizers import SPECS, Optimizer


def _run(oid, params, grads, x0=1.0):
    p = np.array([x0])
    opt = Optimizer(oid, params)
    for g in grads:
        opt.step([p], [np.array([g])])
    return float(p[0])


def test_sgd_and_momentum_by_hand():
    assert _run("sgd", {"lr": 0.1}, [2.0, 2.0]) == pytest.approx(1 - 0.2 - 0.2)
    # v1 = 2, v2 = 0.9·2 + 2 = 3.8 → θ = 1 − 0.1·2 − 0.1·3.8
    assert _run("momentum", {"lr": 0.1, "momentum": 0.9}, [2.0, 2.0]) == pytest.approx(1 - 0.2 - 0.38)


def test_adam_family_first_step():
    # Langkah pertama Adam = −lr·sign(g) (bias-correction) bila ε kecil
    for oid in ("adamw", "amsgrad", "adamax"):
        assert _run(oid, {"lr": 0.1, "weight_decay": 0.0} if oid != "adamax" else {"lr": 0.1}, [3.0]) == pytest.approx(
            0.9, abs=1e-6
        ), oid
    # NAdam: β₁m̂ + (1 − β₁)g/(1 − β₁) = 1,9g → langkah 1,9·lr
    assert _run("nadam", {"lr": 0.1}, [3.0]) == pytest.approx(1 - 0.19, abs=1e-6)
    assert _run("lion", {"lr": 0.1}, [-5.0]) == pytest.approx(1.1)
    # RAdam: pada langkah awal ρₜ ≤ 4 → pembaruan momentum biasa (−lr·m̂ = −lr·g)
    assert _run("radam", {"lr": 0.1}, [3.0]) == pytest.approx(1 - 0.3)


def test_adamw_matches_reference_loop():
    rng = np.random.default_rng(0)
    gs = rng.normal(size=20)
    lr, b1, b2, eps, wd = 0.05, 0.9, 0.999, 1e-8, 0.01
    th, m, v = 1.0, 0.0, 0.0
    for t, g in enumerate(gs, start=1):
        m = b1 * m + (1 - b1) * g
        v = b2 * v + (1 - b2) * g * g
        th -= lr * ((m / (1 - b1**t)) / (math.sqrt(v / (1 - b2**t)) + eps) + wd * th)
    assert _run("adamw", {"lr": lr, "weight_decay": wd}, gs) == pytest.approx(th)


def test_every_optimizer_minimizes_quadratic():
    for oid in SPECS:
        p = np.array([3.0, -2.0])
        opt = Optimizer(oid, {"lr": 0.05} if oid not in ("lion",) else {"lr": 0.01})
        for _ in range(1500):
            opt.step([p], [2 * p])
        assert np.linalg.norm(p) < 0.2, oid


def test_playground_and_validation():
    r = gradient.playground("sphere", [{"id": "adamw", "params": {"lr": 0.1, "weight_decay": 0}}], None, 300).result
    assert r["final"]["AdamW"] < 1e-3
    with pytest.raises(SolverError):
        gradient.playground("tidak-ada", [{"id": "sgd"}], None, 10)
    with pytest.raises(SolverError):
        Optimizer("adamw", {"lr": -1})


def test_training_learns_iris():
    r = gradient.train("iris", "logreg", 0, [{"id": "adamw", "params": {"lr": 0.05}}], 60, 16, 0).result
    assert r["curves"]["AdamW"]["test_acc"][-1] >= 0.85
    m = gradient.train("breast_cancer", "mlp", 16, [{"id": "sgd", "params": {"lr": 0.1}}], 20, 32, 0).result
    assert m["curves"]["SGD"]["test_acc"][-1] >= 0.9


def test_training_csv_dataset():
    rng = np.random.default_rng(1)
    rows = [[float(a), float(b), "A" if a + b > 0 else "B"] for a, b in rng.normal(size=(80, 2))]
    r = gradient.train(
        "csv", "logreg", 0, [{"id": "adamw", "params": {"lr": 0.05}}], 40, 16, 0, ["x1", "x2", "kelas"], rows, "kelas"
    ).result
    assert r["curves"]["AdamW"]["test_acc"][-1] >= 0.85
