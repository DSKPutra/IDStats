"""Aljabar matriks pecahan kecil (invers Gauss-Jordan) untuk simpleks direvisi & analisis sensitivitas."""

from fractions import Fraction

from app.core.errors import SolverError

Matrix = list[list[Fraction]]


def identity(n: int) -> Matrix:
    return [[Fraction(int(i == j)) for j in range(n)] for i in range(n)]


def inverse(m: Matrix) -> Matrix:
    n = len(m)
    a = [list(row) + e for row, e in zip(m, identity(n), strict=True)]
    for col in range(n):
        piv = next((r for r in range(col, n) if a[r][col] != 0), None)
        if piv is None:
            raise SolverError("Matriks basis B singular sehingga tidak memiliki invers.")
        a[col], a[piv] = a[piv], a[col]
        p = a[col][col]
        a[col] = [x / p for x in a[col]]
        for r in range(n):
            if r != col and a[r][col] != 0:
                f = a[r][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col], strict=True)]
    return [row[n:] for row in a]


def matmul(a: Matrix, b: Matrix) -> Matrix:
    return [
        [sum((a[i][k] * b[k][j] for k in range(len(b))), Fraction(0)) for j in range(len(b[0]))] for i in range(len(a))
    ]


def matvec(a: Matrix, v: list[Fraction]) -> list[Fraction]:
    return [sum((x * y for x, y in zip(row, v, strict=True)), Fraction(0)) for row in a]


def vecmat(v: list[Fraction], a: Matrix) -> list[Fraction]:
    return [sum((v[i] * a[i][j] for i in range(len(v))), Fraction(0)) for j in range(len(a[0]))]


def column(a: Matrix, j: int) -> list[Fraction]:
    return [row[j] for row in a]


def as_float(m: Matrix) -> list[list[float]]:
    return [[float(x) for x in row] for row in m]
