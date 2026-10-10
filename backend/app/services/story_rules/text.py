"""Utilitas teks soal cerita berbahasa Indonesia: normalisasi, angka, kalimat, deret data, dan tabel."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")

WORD_NUMBERS = {
    "satu": 1,
    "dua": 2,
    "tiga": 3,
    "empat": 4,
    "lima": 5,
    "enam": 6,
    "tujuh": 7,
    "delapan": 8,
    "sembilan": 9,
    "sepuluh": 10,
    "sebelas": 11,
    "seorang": 1,
    "sebuah": 1,
}

UNITS = {
    "jam",
    "menit",
    "detik",
    "hari",
    "minggu",
    "bulan",
    "tahun",
    "kg",
    "kilogram",
    "gram",
    "gr",
    "ons",
    "ton",
    "liter",
    "ml",
    "meter",
    "m",
    "cm",
    "m2",
    "m3",
    "unit",
    "buah",
    "potong",
    "lembar",
    "orang",
    "pcs",
    "lusin",
    "kodi",
    "pasang",
    "bungkus",
    "botol",
    "karung",
    "sak",
    "batang",
    "rp",
    "rupiah",
    "satuan",
    "porsi",
    "km",
    "box",
    "dus",
    "kaleng",
    "ekor",
    "hektar",
    "ha",
}


def normalize(text: str) -> str:
    t = text.translate(SUBSCRIPTS).replace("\r", "")
    for a, b in (
        ("≤", "<="),
        ("≥", ">="),
        ("≦", "<="),
        ("≧", ">="),
        ("−", "-"),
        ("–", "-"),
        ("—", "-"),
        ("×", "*"),
        ("·", "*"),
    ):
        t = t.replace(a, b)
    t = re.sub(r"\b(Rp)\.\s*", r"\1", t, flags=re.IGNORECASE)
    t = re.sub(r"\bRp\s+(?=\d)", "Rp", t, flags=re.IGNORECASE)
    return t


@dataclass
class Num:
    value: float
    start: int
    end: int
    raw: str
    pct: bool = False
    money: bool = False

    @property
    def fraction(self) -> float:
        """Nilai sebagai pecahan: 5% → 0,05; 0,05 → 0,05; 95 (tanpa %) → 0,95 bila > 1."""
        if self.pct:
            return self.value / 100
        return self.value / 100 if self.value > 1 else self.value


_NUM_RE = re.compile(
    r"(?<![A-Za-z_\d.,])(?P<rp>rp\s*)?(?P<sign>-\s?)?(?P<num>\d+(?:[.,]\d+)*)(?P<frac>/\d+)?"
    r"(?:\s*(?P<mult>ribu|rb|juta|jt|miliar|milyar)\b)?(?P<pct>\s*(?:%|persen\b))?",
    re.IGNORECASE,
)
_CLEAR_DOT_DECIMAL = re.compile(r"(?<![\d.,])\d+\.(?:\d{1,2}|\d{4,})(?![\d.,])")


def dot_is_thousands(text: str) -> bool:
    """Titik dianggap pemisah ribuan kecuali teks jelas memakai titik desimal (mis. 0.25, 3.5)."""
    return not _CLEAR_DOT_DECIMAL.search(text)


def parse_number(s: str, dot_thousands: bool = True, money: bool = False) -> float:
    s = s.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") >= 2:
        s = s.replace(".", "")
    elif "." in s:
        a, b = s.split(".")
        if len(b) == 3 and (dot_thousands or money) and a not in ("0", "-0"):
            s = a + b
    return float(s)


_MULT = {"ribu": 1e3, "rb": 1e3, "juta": 1e6, "jt": 1e6, "miliar": 1e9, "milyar": 1e9}


def find_numbers(text: str) -> list[Num]:
    dots = dot_is_thousands(text)
    out: list[Num] = []
    for m in _NUM_RE.finditer(text):
        raw = m.group("num")
        sign = -1 if m.group("sign") else 1
        money = bool(m.group("rp")) or bool(m.group("mult"))
        if raw.count(",") >= 2 and "." not in raw:
            # “70,80,90” tanpa spasi = daftar angka
            pos = m.start("num")
            for part in raw.split(","):
                out.append(Num(float(part), pos, pos + len(part), part))
                pos += len(part) + 1
            continue
        try:
            value = parse_number(raw, dots, money)
        except ValueError:
            continue
        if m.group("frac"):
            den = float(m.group("frac")[1:])
            value = value / den if den else value
        if m.group("mult"):
            value *= _MULT[m.group("mult").lower()]
        out.append(Num(sign * value, m.start(), m.end(), m.group(0), pct=bool(m.group("pct")), money=money))
    return out


def word_number(word: str) -> int | None:
    return WORD_NUMBERS.get(word.lower())


@dataclass
class Span:
    start: int
    end: int
    text: str


_SENT_SPLIT = re.compile(r"(?<=[.!?;:])\s+(?=\S)|\n+")


def sentences(text: str) -> list[Span]:
    spans: list[Span] = []
    pos = 0
    for m in _SENT_SPLIT.finditer(text):
        if m.start() > pos:
            spans.append(Span(pos, m.start(), text[pos : m.start()]))
        pos = m.end()
    if pos < len(text):
        spans.append(Span(pos, len(text), text[pos:]))
    return [s for s in spans if s.text.strip()]


_CLAUSE_SPLIT = re.compile(
    r",\s*(?=(?:sedangkan|sementara|serta|adapun|kemudian|lalu|dan\s+(?:untuk|setiap|tiap|produk|jenis))\b)"
    r"|\s+(?=(?:sedangkan|sementara itu|adapun)\b)|;\s*",
    re.IGNORECASE,
)


def clauses(span: Span) -> list[Span]:
    out: list[Span] = []
    pos = 0
    for m in _CLAUSE_SPLIT.finditer(span.text):
        if m.start() > pos:
            out.append(Span(span.start + pos, span.start + m.start(), span.text[pos : m.start()]))
        pos = m.end()
    if pos < len(span.text):
        out.append(Span(span.start + pos, span.end, span.text[pos:]))
    return [c for c in out if c.text.strip()]


def all_clauses(text: str) -> list[Span]:
    return [c for s in sentences(text) for c in clauses(s)]


@dataclass
class Sequence:
    label: str
    values: list[float]
    start: int
    end: int
    nums: list[Num] = field(default_factory=list)


_SEQ_GAP = re.compile(r"^[\s,;/|]*(?:(?:dan|and|serta)\s*)?[\s,;/|]*$", re.IGNORECASE)
_LABEL_STOP = re.compile(
    r"\b(?:adalah|yaitu|yakni|sebagai berikut|berikut|sebagai|ialah|diperoleh|didapat|tercatat|hasilnya|data|nilai|"
    r"berturut-turut|masing-masing|sebesar|sbb)\b",
    re.IGNORECASE,
)


def _seq_label(text: str, start: int, lower_bound: int = 0) -> str:
    line_start = max(text.rfind("\n", 0, start), text.rfind(". ", 0, start - 1) if start > 1 else -1) + 1
    prefix = text[max(line_start, lower_bound) : start]
    prefix = re.sub(r"\([^)]*\)", " ", prefix)
    if ":" in prefix:
        prefix = prefix[: prefix.rfind(":")]
        if ":" in prefix:
            prefix = prefix[prefix.rfind(":") + 1 :]
    prefix = re.sub(r"[=:(\[]\s*$", "", prefix.strip())
    prefix = _LABEL_STOP.sub(" ", prefix)
    words = re.findall(r"[A-Za-zÀ-ÿ0-9][\w\-]*", prefix)
    while words and words[0].lower() in ("dan", "serta", "sedangkan", "lalu", "kemudian", "untuk", "pada", "di"):
        words = words[1:]
    return " ".join(words[-4:]).strip()


def sequences(text: str, min_len: int = 3) -> list[Sequence]:
    nums = find_numbers(text)
    runs: list[list[Num]] = []
    cur: list[Num] = []
    for n in nums:
        if cur and _SEQ_GAP.match(text[cur[-1].end : n.start]) and "\n\n" not in text[cur[-1].end : n.start]:
            cur.append(n)
        else:
            if cur:
                runs.append(cur)
            cur = [n]
    if cur:
        runs.append(cur)
    out = []
    prev_end = 0
    for run in runs:
        if len(run) >= min_len:
            out.append(
                Sequence(
                    _seq_label(text, run[0].start, prev_end), [n.value for n in run], run[0].start, run[-1].end, run
                )
            )
        prev_end = run[-1].end
    return out


# ---------------------------------------------------------------- tabel


@dataclass
class TableRow:
    label: str
    values: list[float]
    line: str


@dataclass
class Table:
    header: list[str]
    rows: list[TableRow]


_CELL_SPLIT = re.compile(r"\t+|\s*\|\s*|\s{2,}|\s*;\s*")


def _cells(line: str) -> list[str]:
    parts = [p.strip() for p in _CELL_SPLIT.split(line.strip().strip("|"))]
    return [p for p in parts if p]


def tables(text: str) -> list[Table]:
    """Blok baris berisi ≥2 angka (dengan label baris opsional) + baris judul kolom di atasnya."""
    lines = text.split("\n")
    blocks: list[Table] = []
    header: list[str] = []
    rows: list[TableRow] = []

    def flush():
        nonlocal rows, header
        if len(rows) >= 2 or (len(rows) == 1 and len(rows[0].values) >= 3 and header):
            blocks.append(Table(header, rows))
        rows, header = [], []

    for line in lines:
        if not line.strip() or set(line.strip()) <= set("-|+=: "):
            continue
        nums = find_numbers(line)
        first = nums[0].start if nums else len(line)
        label = re.sub(r"[|:\t]+", " ", line[:first]).strip(" -")
        rest = line[nums[-1].end :] if nums else ""
        if len(nums) >= 2 and not re.search(r"[A-Za-z]{3,}", re.sub(r"\b(?:rp|unit|jam|kg)\b", "", rest, flags=re.I)):
            if len(label.split()) > 6:  # kalimat biasa, bukan baris tabel
                flush()
                continue
            rows.append(TableRow(label, [n.value for n in nums], line))
        else:
            if rows:
                flush()
            cells = _cells(line)
            if len(cells) >= 2 and not nums:
                header = cells
            elif len(cells) < 2:
                header = []
    flush()
    return blocks


def table_matrix(t: Table) -> tuple[list[list[float]], list[str], list[str]]:
    """Matriks persegi panjang dari tabel: baris dengan jumlah nilai terbanyak yang sama."""
    from collections import Counter

    width = Counter(len(r.values) for r in t.rows).most_common(1)[0][0]
    body = [r for r in t.rows if len(r.values) == width]
    cols = t.header[-width:] if len(t.header) >= width else []
    return [r.values for r in body], [r.label for r in body], cols


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def near_number(text: str, pattern: str, after: int = 60, before: int = 0, pct_ok: bool = True) -> Num | None:
    """Angka pertama setelah kata kunci (dalam ``after`` karakter); bila tidak ada, angka terdekat sebelumnya."""
    for m in re.finditer(pattern, text, re.IGNORECASE):
        window = text[m.end() : m.end() + after]
        cut = re.search(r"[.;\n](?!\d)", window)
        if cut:
            window = window[: cut.start()]
        nums = find_numbers(window)
        if nums and (pct_ok or not nums[0].pct):
            n = nums[0]
            return Num(n.value, m.end() + n.start, m.end() + n.end, n.raw, n.pct, n.money)
        if before:
            prev = find_numbers(text[max(0, m.start() - before) : m.start()])
            if prev:
                n = prev[-1]
                off = max(0, m.start() - before)
                return Num(n.value, off + n.start, off + n.end, n.raw, n.pct, n.money)
    return None
