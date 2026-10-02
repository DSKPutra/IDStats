"""Bilangan eksak untuk tabel simpleks: pecahan (Fraction) dan bentuk a + bM untuk metode Big-M."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

Num = Fraction


def frac(x: float | int | str | Fraction) -> Fraction:
    """Ubah input menjadi pecahan eksak (0.3 → 3/10, bukan 5404319552844595/18014398509481984)."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, float):
        return Fraction(repr(x)).limit_denominator(10**9)
    return Fraction(x)


def fmt_frac(x: Fraction) -> str:
    """Tampilan tabel: 3/2, -4, 0."""
    if x.denominator == 1:
        return str(x.numerator)
    return f"{x.numerator}/{x.denominator}"


def latex_frac(x: Fraction) -> str:
    if x.denominator == 1:
        return str(x.numerator)
    sign = "-" if x < 0 else ""
    return rf"{sign}\tfrac{{{abs(x.numerator)}}}{{{x.denominator}}}"


@dataclass(frozen=True)
class MNum:
    """Nilai a + m·M dengan M bilangan sangat besar (metode Big-M). Perbandingan: suku M didahulukan."""

    a: Fraction = Fraction(0)
    m: Fraction = Fraction(0)

    def __add__(self, other: MNum | Fraction | int) -> MNum:
        o = _as_m(other)
        return MNum(self.a + o.a, self.m + o.m)

    __radd__ = __add__

    def __sub__(self, other: MNum | Fraction | int) -> MNum:
        o = _as_m(other)
        return MNum(self.a - o.a, self.m - o.m)

    def __neg__(self) -> MNum:
        return MNum(-self.a, -self.m)

    def __mul__(self, k: Fraction | int) -> MNum:
        if isinstance(k, MNum):
            if k.m:
                raise ValueError("Perkalian dua bilangan yang memuat M tidak didukung.")
            k = k.a
        return MNum(self.a * k, self.m * k)

    __rmul__ = __mul__

    def __truediv__(self, k: Fraction | int) -> MNum:
        return MNum(self.a / k, self.m / k)

    def key(self) -> tuple[Fraction, Fraction]:
        return (self.m, self.a)

    def __lt__(self, other: MNum | Fraction | int) -> bool:
        return self.key() < _as_m(other).key()

    def __le__(self, other: MNum | Fraction | int) -> bool:
        return self.key() <= _as_m(other).key()

    def __gt__(self, other: MNum | Fraction | int) -> bool:
        return self.key() > _as_m(other).key()

    def __ge__(self, other: MNum | Fraction | int) -> bool:
        return self.key() >= _as_m(other).key()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, int | Fraction | MNum):
            return self.key() == _as_m(other).key()
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.key())

    def is_zero(self) -> bool:
        return self.a == 0 and self.m == 0

    def __str__(self) -> str:
        return fmt_m(self)


def _as_m(x: MNum | Fraction | int) -> MNum:
    return x if isinstance(x, MNum) else MNum(Fraction(x), Fraction(0))


def fmt_m(x: MNum) -> str:
    if x.m == 0:
        return fmt_frac(x.a)
    if x.m == 1:
        m_part = "M"
    elif x.m == -1:
        m_part = "-M"
    else:
        m_part = f"{fmt_frac(x.m)}M"
    if x.a == 0:
        return m_part
    return f"{m_part}{'+' if x.a > 0 else '-'}{fmt_frac(abs(x.a))}"


def fmt_any(x: MNum | Fraction) -> str:
    return fmt_m(x) if isinstance(x, MNum) else fmt_frac(x)
