"""Helper bersama untuk solver: format angka dan pembuat grafik Plotly."""

from collections.abc import Sequence
from typing import Any

import numpy as np

from app.core.errors import SolverError


def fmt(x: float, digits: int = 4) -> str:
    """Format angka untuk teks/LaTeX: bulat tanpa desimal, lainnya dibulatkan."""
    if x is None or not np.isfinite(x):
        return "—"
    if float(x).is_integer():
        return str(int(x))
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
