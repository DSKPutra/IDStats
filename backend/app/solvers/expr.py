"""Parser ekspresi matematika yang aman (tanpa eval bebas) untuk fungsi tujuan/kendala nonlinear.

Mendukung + − × / ^ (atau **), fungsi ln, log, log10, exp, sqrt, abs, sin, cos, tan, dan konstanta pi, e.
Perkalian implisit sederhana seperti ``2x1`` atau ``3x^2`` diterima.
"""

from __future__ import annotations

import ast
import math
import re
from collections.abc import Callable

import numpy as np

from app.core.errors import SolverError

_FUNCS: dict[str, Callable] = {
    "ln": np.log,
    "log": np.log,
    "log10": np.log10,
    "exp": np.exp,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
}
_CONSTS = {"pi": math.pi, "e": math.e}
_ALLOWED = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Call,
)


class Expr:
    def __init__(self, text: str, variables: list[str] | None = None):
        src = text.strip().replace("^", "**").replace("−", "-").replace("×", "*").replace("·", "*")
        # perkalian implisit: 2x1 → 2*x1, 3( → 3*(, )( → )*(, )x → )*x (angka yang bukan bagian nama)
        src = re.sub(r"(?<![A-Za-z_\d.])(\d+(?:\.\d+)?)\s*([A-Za-z_(])", r"\1*\2", src)
        src = re.sub(r"\)\s*([A-Za-z_\d(])", r")*\1", src)
        if not src:
            raise SolverError("Ekspresi fungsi kosong.")
        try:
            tree = ast.parse(src, mode="eval")
        except SyntaxError as exc:
            raise SolverError(f"Ekspresi “{text}” tidak valid: periksa tanda kurung dan operator.") from exc
        names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED):
                raise SolverError(f"Ekspresi “{text}” memuat bagian yang tidak diizinkan.")
            if isinstance(node, ast.Call):
                if (
                    not isinstance(node.func, ast.Name)
                    or node.func.id not in _FUNCS
                    or len(node.args) != 1
                    or node.keywords
                ):
                    raise SolverError(
                        f"Fungsi tidak dikenal di “{text}”. Gunakan ln, exp, sqrt, abs, sin, cos, tan, log10."
                    )
            elif isinstance(node, ast.Name) and node.id not in _FUNCS and node.id not in _CONSTS:
                names.add(node.id)
        if variables is None:
            variables = sorted(names, key=lambda s: (re.sub(r"\d", "", s), int(re.sub(r"\D", "", s) or 0)))
        unknown = names - set(variables)
        if unknown:
            raise SolverError(f"Variabel {', '.join(sorted(unknown))} tidak dikenal di “{text}”.")
        self.text = text.strip()
        self.variables = variables
        self._code = compile(tree, "<expr>", "eval")

    def __call__(self, x) -> float:
        env = {"__builtins__": {}, **_FUNCS, **_CONSTS}
        env.update({v: x[i] for i, v in enumerate(self.variables)})
        with np.errstate(all="ignore"):
            val = eval(self._code, env)  # noqa: S307 - AST sudah dibatasi pada operasi aritmetika
        return float(val)

    def safe(self, x) -> float:
        try:
            v = self(x)
        except (ZeroDivisionError, OverflowError, ValueError):
            return math.nan
        return v

    def grad(self, x, h: float = 1e-6) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        g = np.zeros_like(x)
        for i in range(x.size):
            step = h * max(1.0, abs(x[i]))
            e = np.zeros_like(x)
            e[i] = step
            g[i] = (self(x + e) - self(x - e)) / (2 * step)
        return g

    def hessian(self, x, h: float = 1e-4) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        n = x.size
        hm = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                ei = np.zeros(n)
                ej = np.zeros(n)
                ei[i] = h
                ej[j] = h
                hm[i, j] = (self(x + ei + ej) - self(x + ei - ej) - self(x - ei + ej) + self(x - ei - ej)) / (4 * h * h)
        return (hm + hm.T) / 2


def latexify(text: str) -> str:
    s = text.replace("**", "^").replace("*", r" \cdot ")
    s = re.sub(r"\^(\d+(?:\.\d+)?)", r"^{\1}", s)
    s = re.sub(r"\b([A-Za-z])(\d+)\b", r"\1_{\2}", s)
    s = (
        re.sub(r"\b(ln|exp|sqrt|sin|cos|tan|log10|abs)\b", r"\\\1", s)
        .replace(r"\log10", r"\log_{10}")
        .replace(r"\abs", r"\operatorname{abs}")
    )
    return s
