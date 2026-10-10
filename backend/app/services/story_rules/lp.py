"""Soal cerita → model program linear (sintaks solver IDStats: ``max Z = 3x1 + 5x2`` + satu kendala per baris).

Tiga bentuk masukan dikenali, berurutan:
1. Model eksplisit — “Maksimumkan Z = 3x + 5y dengan kendala x + y ≤ 4 …”.
2. Tabel — baris sumber daya × kolom produk, kolom terakhir kapasitas, baris laba/biaya.
3. Prosa — “Setiap meja memerlukan 4 jam perakitan … Waktu perakitan tersedia 240 jam … Keuntungan meja Rp70.000 …”.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.story_rules.text import (
    UNITS,
    Num,
    Span,
    all_clauses,
    find_numbers,
    has,
    normalize,
    tables,
    word_number,
)

# ------------------------------------------------------------------ util


def fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.6g}"


def term_str(coefs: list[float], names: list[str]) -> str:
    parts: list[str] = []
    for c, n in zip(coefs, names, strict=True):
        if abs(c) < 1e-12:
            continue
        sign = "-" if c < 0 else "+"
        mag = abs(c)
        body = n if abs(mag - 1) < 1e-12 else f"{fmt(mag)}{n}"
        parts.append(f"{sign} {body}" if parts else (f"-{body}" if c < 0 else body))
    return " ".join(parts) if parts else "0"


@dataclass
class LPResult:
    model: str
    formulation: str
    assumptions: list[str] = field(default_factory=list)
    n_vars: int = 0
    found_constraints: int = 0
    found_objective: bool = False


def _sense(text: str) -> str:
    t = text.lower()
    if re.search(
        r"\bmin(?:imum|imal(?:kan)?|imumkan|imize)?\b|\bminimalkan\b|seminimal|sekecil|termurah|terendah|menekan biaya|meminimumkan|meminimalkan",
        t,
    ) and not re.search(r"maksim|\bmax\b|sebesar[- ]besar|terbesar|keuntungan maksimum|laba maksimum", t):
        return "min"
    if re.search(r"maksim|\bmax\b|sebesar[- ]besar|terbesar|setinggi|tertinggi|memaksimalkan|memaksimumkan", t):
        return "max"
    if re.search(r"biaya|ongkos|harga", t) and not re.search(r"keuntungan|laba|untung|profit|pendapatan", t):
        return "min"
    return "max"


def _integer_decl(text: str, names: list[str], allow_int: bool, assumptions: list[str]) -> str:
    t = text.lower()
    binary = re.search(r"\bbiner\b|\b0\s*(?:atau|/|-)\s*1\b|ya\s*(?:atau|/)\s*tidak", t)
    integer = re.search(r"bilangan bulat|\binteger\b|\bbulat\b|tidak (?:boleh|dapat) (?:pecahan|dipecah)|\butuh\b", t)
    if not (binary or integer):
        return ""
    if not allow_int:
        assumptions.append(
            "Soal menyebut bilangan bulat/biner; di halaman ini diselesaikan sebagai LP biasa — gunakan halaman "
            "Integer Programming (Bab 12) untuk syarat bulat."
        )
        return ""
    return f"\n{'bin' if binary else 'int'} {', '.join(names)}"


# ------------------------------------------------------------------ 1. model eksplisit

_OBJ_RE = re.compile(
    r"(?P<sense>maks\w*|max\w*|min\w*|optimal\w*)\s*:?\s*(?:(?:[a-zA-Z]\w*)\s*(?:\([^)]*\))?\s*=)\s*(?P<expr>[^\n;]+)",
    re.IGNORECASE,
)
_MATH_TOKEN = re.compile(r"\s*(\d+(?:[.,]\d+)?(?:/\d+(?:[.,]\d+)?)?|[a-zA-Z]{1,2}\d*|[+\-*/()])")
_VAR = re.compile(r"^[a-zA-Z]{1,2}\d*$")
_OPS = re.compile(r"(<=|>=|=<|=>|<|>|=)")


def _parse_linear(expr: str) -> tuple[dict[str, float], float] | None:
    """Ekspresi linear sederhana → (koefisien per variabel, konstanta)."""
    tokens: list[str] = []
    pos = 0
    expr = expr.strip()
    while pos < len(expr):
        m = _MATH_TOKEN.match(expr, pos)
        if not m or m.end() == pos:
            return None
        tokens.append(m.group(1))
        pos = m.end()
    coefs: dict[str, float] = {}
    const = 0.0
    sign = 1.0
    num: float | None = None
    i = 0

    def flush_number():
        nonlocal num, const
        if num is not None:
            const += sign * num
            num = None

    while i < len(tokens):
        tk = tokens[i]
        if tk in "+-":
            flush_number()
            sign = 1.0 if tk == "+" else -1.0
        elif tk in "*()":
            pass
        elif tk == "/":
            if num is not None and i + 1 < len(tokens) and re.match(r"\d", tokens[i + 1]):
                num /= float(tokens[i + 1].replace(",", "."))
                i += 1
        elif re.match(r"\d", tk):
            val = float(tk.replace(",", ".")) if "/" not in tk else _frac(tk)
            num = val if num is None else num * val
        elif _VAR.match(tk):
            if tk.lower() in ("rp",):
                return None
            coefs[tk] = coefs.get(tk, 0.0) + sign * (num if num is not None else 1.0)
            num = None
            sign = 1.0
        i += 1
        if tk not in "+-" and re.match(r"[a-zA-Z]", tk):
            sign = 1.0
    flush_number()
    return coefs, const


def _frac(tk: str) -> float:
    a, b = tk.split("/")
    return float(a.replace(",", ".")) / float(b.replace(",", "."))


def _math_suffix(s: str) -> str:
    """Bagian paling kanan dari ``s`` yang hanya berisi token matematika (berhenti di kata ≥3 huruf)."""
    tokens = re.findall(r"\d+(?:[.,]\d+)?|[a-zA-Z]+\d*|[+\-*/()]|\s+|.", s)
    out: list[str] = []
    for tk in reversed(tokens):
        if tk.isspace() or re.fullmatch(r"\d+(?:[.,]\d+)?|[+\-*/()]", tk) or _VAR.match(tk):
            out.append(tk)
        else:
            break
    return "".join(reversed(out)).strip()


def _math_prefix(s: str) -> str:
    tokens = re.findall(r"\d+(?:[.,]\d+)?|[a-zA-Z]+\d*|[+\-*/()]|\s+|.", s)
    out: list[str] = []
    for tk in tokens:
        if tk.isspace() or re.fullmatch(r"\d+(?:[.,]\d+)?|[+\-*/()]", tk) or _VAR.match(tk):
            out.append(tk)
        else:
            break
    return "".join(out).strip()


def parse_explicit(text: str, allow_int: bool) -> LPResult | None:
    t = normalize(text)
    obj = None
    rest_start = 0
    for m in _OBJ_RE.finditer(t):
        full = m.group("expr")
        cut = re.search(
            r"\b(?:dengan|terhadap|s\.?\s?t\.?|subject|kendala|syarat|dimana|di mana)\b|,\s", full, flags=re.I
        )
        expr = full[: cut.start()] if cut else full
        parsed = _parse_linear(_math_prefix(expr))
        if parsed and parsed[0]:
            obj = (m, parsed[0])
            rest_start = m.start("expr") + len(_math_prefix(expr))
            break
    if not obj:
        return None
    m, obj_coefs = obj
    sense = "min" if m.group("sense").lower().startswith("min") else "max"
    rest = t[rest_start:]
    segments = re.split(
        r"\n|;|,\s+(?=[-+]?\s*\d*\s*[a-zA-Z]{1,2}\d*\s*[-+<>=])|\s+dan\s+(?=[-+]?\s*\d*\s*[a-zA-Z]{1,2}\d*\s*[-+<>=])",
        rest,
    )
    cons: list[tuple[dict[str, float], str, float]] = []
    for seg in segments:
        parts = _OPS.split(seg)
        if len(parts) < 3:
            continue
        # rantai “0 <= x <= 4” → dua kendala
        for k in range(1, len(parts) - 1, 2):
            lhs = _math_suffix(parts[k - 1]) if k == 1 else parts[k - 1]
            rhs = _math_prefix(parts[k + 1])
            op = {"=<": "<=", "=>": ">=", "<": "<=", ">": ">="}.get(parts[k], parts[k])
            pl, pr = _parse_linear(lhs), _parse_linear(rhs)
            if not pl or not pr:
                continue
            coefs = dict(pl[0])
            for v, c in pr[0].items():
                coefs[v] = coefs.get(v, 0.0) - c
            const = pr[1] - pl[1]
            coefs = {v: c for v, c in coefs.items() if abs(c) > 1e-12}
            if not coefs:
                continue
            # nonnegatif “x, y >= 0” atau “x >= 0” diabaikan (sudah default)
            if op == ">=" and abs(const) < 1e-12 and len(coefs) == 1 and next(iter(coefs.values())) == 1:
                continue
            cons.append((coefs, op, const))
    if re.search(r"[a-zA-Z]{1,2}\d*\s*,\s*[a-zA-Z]{1,2}\d*\s*>=\s*0", rest):
        pass
    order: list[str] = []
    for v in list(obj_coefs) + [v for c in cons for v in c[0]]:
        if v not in order:
            order.append(v)
    if all(re.fullmatch(r"x\d+", v) for v in order):
        mapping = {v: v for v in order}
        names = sorted(order, key=lambda s: int(s[1:]))
    else:
        mapping = {v: f"x{i + 1}" for i, v in enumerate(order)}
        names = [mapping[v] for v in order]
    assumptions: list[str] = []

    def row(coefs: dict[str, float]) -> list[float]:
        return [sum(c for v, c in coefs.items() if mapping[v] == n) for n in names]

    lines = [f"{sense} Z = {term_str(row(obj_coefs), names)}"]
    for coefs, op, const in cons:
        lines.append(f"{term_str(row(coefs), names)} {op} {fmt(const)}")
    model = "\n".join(lines) + _integer_decl(t, names, allow_int, assumptions)
    renamed = [f"{n} = {v}" for v, n in mapping.items() if v != n]
    formulation = "Model dibaca langsung dari soal."
    if renamed:
        formulation += "\nPenamaan ulang variabel: " + ", ".join(renamed) + "."
    formulation += "\n" + _pretty(model)
    return LPResult(model, formulation, assumptions, len(names), len(cons), True)


def _pretty(model: str) -> str:
    lines = model.split("\n")
    head = lines[0].replace("max Z", "Maksimumkan Z").replace("min Z", "Minimumkan Z")
    body = [ln for ln in lines[1:] if not ln.startswith(("int ", "bin "))]
    decl = [ln for ln in lines[1:] if ln.startswith(("int ", "bin "))]
    names = sorted(set(re.findall(r"x\d+", model)), key=lambda s: int(s[1:]))
    out = [f"Fungsi tujuan: {head}", "Kendala:"] + [f"  {ln.replace('<=', '≤').replace('>=', '≥')}" for ln in body]
    out.append(f"  {', '.join(names)} ≥ 0")
    for d in decl:
        out.append(f"  {', '.join(names)} {'biner (0/1)' if d.startswith('bin') else 'bilangan bulat'}")
    return "\n".join(out)


# ------------------------------------------------------------------ 2. tabel

_OBJ_ROW = re.compile(r"keuntungan|laba|untung|profit|pendapatan|kontribusi|harga|biaya|ongkos|nilai", re.I)
_CAP_COL = re.compile(r"kapasitas|tersedia|persediaan|maks|batas|jumlah|total|kebutuhan|minimal|min\b|sumber", re.I)
_GE_WORDS = re.compile(r"minimal|minimum|min\b|paling sedikit|sekurang|setidaknya|kebutuhan|kurang dari tidak", re.I)


def parse_table(text: str, allow_int: bool) -> LPResult | None:
    t = normalize(text)
    for tb in tables(t):
        rows = tb.rows
        widths = [len(r.values) for r in rows]
        n = min(widths)
        obj_rows = [r for r in rows if _OBJ_ROW.search(r.label)]
        cons_rows = [r for r in rows if r not in obj_rows]
        if not obj_rows or not cons_rows:
            continue
        # jumlah produk = jumlah nilai baris tujuan
        n = len(obj_rows[0].values)
        if any(len(r.values) != n + 1 for r in cons_rows):
            continue
        header = tb.header
        products = header[-(n + 1) : -1] if len(header) >= n + 1 else [f"produk {i + 1}" for i in range(n)]
        names = [f"x{i + 1}" for i in range(n)]
        sense = _sense(t + " " + obj_rows[0].label)
        lines = [f"{sense} Z = {term_str(obj_rows[0].values, names)}"]
        desc = []
        for r in cons_rows:
            op = ">=" if _GE_WORDS.search(r.label + " " + (header[-1] if header else "")) else "<="
            lines.append(f"{term_str(r.values[:n], names)} {op} {fmt(r.values[n])}")
            desc.append(r.label or f"kendala {len(desc) + 1}")
        assumptions: list[str] = []
        model = "\n".join(lines) + _integer_decl(t, names, allow_int, assumptions)
        varline = "\n".join(f"  {nm} = jumlah {p}" for nm, p in zip(names, products, strict=True))
        formulation = f"Model disusun dari tabel.\nVariabel keputusan:\n{varline}\n" + _pretty(model)
        return LPResult(model, formulation, assumptions, n, len(cons_rows), True)
    return None


# ------------------------------------------------------------------ 3. prosa

_TYPE_NOUNS = (
    r"produk|jenis|tipe|model|merek|merk|barang|makanan|minuman|pakan|pupuk|menu|paket|kue|roti|obat|tanaman|bahan makanan|"
    r"mainan|sepatu|tas|baju|kemeja|kaos|celana|lampu|kursi|meja|lemari"
)
_RESOURCE_NOUNS = r"mesin|departemen|bagian|divisi|stasiun|proses|gudang|pabrik|bengkel|lini"
_PROFIT = re.compile(r"keuntungan|laba|untung|profit|kontribusi|margin|pendapatan|penerimaan", re.I)
_SELL = re.compile(r"harga jual|dijual|terjual|menjual seharga|harga per", re.I)
_COST = re.compile(r"\bbiaya\b|\bongkos\b|\bharga\b|\bmodal\b|\bharga beli\b", re.I)
_CAP = re.compile(
    r"tersedia|kapasitas|maksimal|maksimum|paling banyak|tidak lebih|tidak melebihi|hanya|persediaan|"
    r"dimiliki|memiliki|mempunyai|punya|batas|dibatasi|terbatas|anggaran|sebanyak-banyaknya|kebutuhan|"
    r"minimal|minimum|paling sedikit|sekurang|setidaknya|tidak kurang|harus dipenuhi|diperlukan paling|jam kerja",
    re.I,
)
_GE = re.compile(
    r"minimal|minimum|paling sedikit|sekurang[- ]kurangnya|setidaknya|tidak kurang|harus (?:dipenuhi|terpenuhi)|"
    r"kebutuhan|dibutuhkan paling sedikit|lebih dari",
    re.I,
)
_LE = re.compile(r"maksimal|maksimum|paling banyak|tidak lebih|tidak melebihi|sebanyak-banyaknya|hanya|batas", re.I)
_EQ = re.compile(r"\btepat\b|harus sama dengan|persis", re.I)
_TOTAL = re.compile(
    r"\btotal\b|\bjumlah (?:produksi|seluruh|keseluruhan|total|semua|kedua|ketiga)|seluruh produk|keseluruhan|gabungan|kedua produk|ketiga produk|semua produk",
    re.I,
)
_DEMAND = re.compile(r"permintaan|pesanan|terjual|dipasarkan|pasar", re.I)
_RESPECTIVE = re.compile(r"berturut[- ]turut|masing[- ]masing", re.I)
_STOP = {
    "di",
    "pada",
    "untuk",
    "dan",
    "dengan",
    "yang",
    "adalah",
    "ialah",
    "sebesar",
    "sebanyak",
    "selama",
    "setiap",
    "tiap",
    "per",
    "memerlukan",
    "membutuhkan",
    "butuh",
    "perlu",
    "diperlukan",
    "dibutuhkan",
    "menggunakan",
    "memakai",
    "mengandung",
    "berisi",
    "waktu",
    "tersedia",
    "kapasitas",
    "maksimal",
    "maksimum",
    "minimal",
    "minimum",
    "hanya",
    "paling",
    "banyak",
    "sedikit",
    "tidak",
    "lebih",
    "dari",
    "kurang",
    "total",
    "jumlah",
    "serta",
    "sedangkan",
    "sementara",
    "itu",
    "ada",
    "masing-masing",
    "berturut-turut",
    "proses",
    "diproses",
    "dikerjakan",
    "membuat",
    "memproduksi",
    "produksi",
    "pembuatan",
    "satu",
    "sebuah",
    "buah",
    "unit",
    "atau",
    "juga",
    "tenaga",
    "kerja",
    "bahan",
    "baku",
    "sumber",
    "daya",
    "kebutuhan",
    "perusahaan",
    "pabrik",
    "dimiliki",
    "memiliki",
    "mempunyai",
    "batas",
    "dibatasi",
    "terbatas",
    "persediaan",
    "anggaran",
    "sehari",
    "seminggu",
    "sebulan",
    "hari",
    "minggu",
    "bulan",
    "dalam",
    "harus",
    "dipenuhi",
    "dapat",
    "bisa",
    "akan",
    "rp",
    "rupiah",
    "sekurang-kurangnya",
    "setidaknya",
    "melebihi",
    "kg",
    "jam",
    "menit",
}
_VERBS = {
    "beroperasi",
    "bekerja",
    "berjalan",
    "digunakan",
    "dipakai",
    "dialokasikan",
    "disediakan",
    "produk",
    "permintaan",
    "pesanan",
    "pasar",
    "penjualan",
    "terjual",
    "laku",
    "dijual",
    "keuntungan",
    "laba",
    "harga",
    "biaya",
    "masing",
    "setiap",
    "perusahaan",
    "pabrikan",
    "toko",
    "usaha",
    "industri",
    "home",
    "rumah",
}
# kata majemuk sumber daya yang dipertahankan utuh
_KEEP_PHRASES = re.compile(
    r"tenaga kerja|bahan baku|jam kerja|jam mesin|modal|dana|lahan|luas tanah|air|pupuk|listrik", re.I
)


@dataclass
class Product:
    name: str
    aliases: list[str]


def _clean_item(s: str) -> str:
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.split(r"\b(?:dengan|yang|untuk|setiap|tiap|masing|dimana|di mana|berupa|seharga)\b|[,:]", s, flags=re.I)[0]
    s = re.sub(r"^\s*(?:sebuah|satu|dua|tiga|empat|jenis|macam|tipe|buah)\s+", "", s.strip(), flags=re.I)
    words = s.split()
    return " ".join(words[:3]).strip(" .")


_GENERIC_HEADS = {
    "produk",
    "jenis",
    "tipe",
    "model",
    "merek",
    "merk",
    "barang",
    "makanan",
    "minuman",
    "pakan",
    "pupuk",
    "menu",
    "paket",
    "bahan",
}


def _aliases(name: str, all_names: list[str]) -> list[str]:
    """Nama lengkap + kata inti (kata pertama, “pintu kaca” → “pintu”) + label huruf (“produk A” → “A”)."""
    al = {name}
    words = name.split()
    if len(words) >= 2:
        head = words[0].lower()
        shared = sum(1 for n in all_names if n.split()[0].lower() == head) > 1
        if head not in _GENERIC_HEADS and not shared:
            al.add(words[0])
        if re.fullmatch(r"[A-Z0-9]|I{1,3}|IV|V", words[-1]):
            al.add(words[-1])
    return sorted(al, key=len, reverse=True)


def find_products(text: str) -> list[Product]:
    t = normalize(text)
    found: list[str] = []
    # “… yaitu meja dan kursi”, “… jenis produk: A, B, dan C”
    for m in re.finditer(
        r"(?:memproduksi|membuat|menghasilkan|memasarkan|menjual|merakit|mengolah|menanam|menyediakan|memiliki|"
        r"mencampur|terdiri (?:atas|dari)|produk(?:nya)?|jenis|macam|tipe|model)\b[^.;\n]{0,60}?(?:yaitu|yakni|berupa|adalah|:)\s*"
        r"(?P<list>[^.;\n]+)",
        t,
        re.I,
    ):
        items = re.split(r",\s*(?:dan\s+|serta\s+)?|\s+dan\s+|\s+serta\s+|\s*&\s*|\s+atau\s+", m.group("list"))
        items = [_clean_item(i) for i in items]
        items = [i for i in items if i and not find_numbers(i) and len(i) <= 30]
        if 2 <= len(items) <= 8:
            found = items
            break
    if not found:
        # “memproduksi pintu kaca (…) dan jendela (…)”
        m = re.search(
            r"\b(?:memproduksi|membuat|menghasilkan|memasarkan|menjual|merakit|mengolah|menanam|menyediakan|mencampur)\s+"
            r"(?:(?:dua|tiga|empat)\s+(?:jenis|macam)\s+(?:produk\s+|barang\s+)?)?(?P<list>[^.;\n]+?\s+(?:dan|serta)\s+[^.;\n]+?)"
            r"(?=[.;\n]|,\s*(?:dengan|yang|setiap|tiap|masing)|$)",
            t,
            re.I,
        )
        if m:
            lst = re.sub(r"\([^)]*\)", "", m.group("list"))
            items = [_clean_item(i) for i in re.split(r",\s*(?:dan\s+|serta\s+)?|\s+dan\s+|\s+serta\s+", lst)]
            items = [i for i in items if i and not find_numbers(i) and len(i.split()) <= 3]
            if 2 <= len(items) <= 6:
                found = items
    if not found:
        # “produk A dan produk B”, “makanan I … makanan II”
        pairs = re.findall(rf"\b((?:{_TYPE_NOUNS}))\s+([A-Z]|I{{1,3}}|IV|V|\d)\b", t, re.I)
        groups: dict[str, list[str]] = {}
        for noun, tag in pairs:
            groups.setdefault(noun.lower(), [])
            if tag not in groups[noun.lower()]:
                groups[noun.lower()].append(tag)
        best = max(groups.items(), key=lambda kv: len(kv[1]), default=None)
        if best and len(best[1]) >= 2:
            found = [f"{best[0]} {tag}" for tag in best[1]]
    if not found:
        # “dua jenis/macam … , X dan Y”
        m = re.search(
            r"\b(?:dua|tiga|empat|2|3|4)\s+(?:jenis|macam|tipe|produk|model)\b[^.;\n]*?,\s*(?P<list>[^.;\n]+)", t, re.I
        )
        if m:
            items = [_clean_item(i) for i in re.split(r",\s*(?:dan\s+)?|\s+dan\s+", m.group("list"))]
            items = [i for i in items if i and not find_numbers(i)]
            if len(items) >= 2:
                found = items
    if not found:
        # kata setelah “setiap/tiap/per/sebuah” yang muncul berulang
        cands: dict[str, int] = {}
        for m in re.finditer(
            r"\b(?:setiap|tiap|per|sebuah|satu|1)\s+(?:unit\s+|buah\s+|potong\s+|bungkus\s+|lusin\s+|kodi\s+|pasang\s+)?([a-zA-Z][\w-]+)",
            t,
            re.I,
        ):
            w = m.group(1).lower()
            if w in UNITS or w in _STOP or re.fullmatch(_RESOURCE_NOUNS, w) or w in ("produk", "jenis", "barang"):
                continue
            cands[w] = cands.get(w, 0) + 1
        ranked = [
            w for w, c in sorted(cands.items(), key=lambda kv: -kv[1]) if re.search(rf"\b{re.escape(w)}\b", t, re.I)
        ]
        if len(ranked) >= 2:
            found = ranked[:4]
    seen: list[str] = []
    for f in found:
        if f.lower() not in [s.lower() for s in seen]:
            seen.append(f)
    return [Product(p, _aliases(p, seen)) for p in seen]


@dataclass
class Mention:
    product: int
    start: int
    end: int


def _mentions(text: str, products: list[Product]) -> list[Mention]:
    out: list[Mention] = []
    taken: list[tuple[int, int]] = []
    for idx, p in enumerate(products):
        for al in p.aliases:
            single = re.fullmatch(r"[A-Z0-9]|I{1,3}|IV|V", al)
            pat = rf"(?<![\w-]){re.escape(al)}(?![\w-])"
            for m in re.finditer(pat, text, 0 if single else re.I):
                if any(a <= m.start() < b for a, b in taken):
                    continue
                if single:
                    # huruf tunggal hanya bila didahului kata jenis/produk atau berdiri sebagai subjek daftar
                    before = text[max(0, m.start() - 25) : m.start()].lower()
                    if re.search(rf"(?:{_RESOURCE_NOUNS})\s*$", before):
                        continue
                out.append(Mention(idx, m.start(), m.end()))
                taken.append((m.start(), m.end()))
    return sorted(out, key=lambda x: x.start)


def _resource_label(text: str, num: Num, lo: int, hi: int, product_spans: list[tuple[int, int]]) -> tuple[str, str]:
    """(label sumber daya, satuan) untuk sebuah angka: kata setelah angka, atau sebelum bila kosong."""
    after = text[num.end : hi]
    unit = ""
    words_after = re.findall(r"[A-Za-z][\w-]*|\d+", after)[:5]
    label: list[str] = []
    for w in words_after:
        lw = w.lower()
        if not unit and lw in UNITS:
            unit = lw
            continue
        if lw in (
            "per",
            "setiap",
            "tiap",
            "untuk",
            "dan",
            "serta",
            "sedangkan",
            "atau",
            "dengan",
            "yang",
            "dari",
            "pada",
            "di",
        ):
            break
        if lw in _STOP or lw.isdigit():
            if label:
                break
            continue
        if any(a <= num.end + after.find(w) < b for a, b in product_spans):
            break
        label.append(lw)
        if len(label) == 2:
            break
    if label and re.fullmatch(r"[a-z]", label[-1]) and len(label) == 1:
        label = []
    phrase = _KEEP_PHRASES.search(after[:40])
    if (
        not label
        and phrase
        and phrase.start() < 20
        and not re.search(r"\b(?:dan|serta|sedangkan|atau)\b|,", after[: phrase.start()])
    ):
        label = [phrase.group(0).lower()]
    if not label:
        before = text[lo : num.start]
        # kandidat terdekat ke angka: “mesin A”, frasa baku (“bahan baku”), atau kata isi terakhir
        strong: list[tuple[int, str]] = []  # “mesin A”, frasa baku
        weak: list[tuple[int, str]] = []  # kata isi biasa
        for m in re.finditer(rf"\b({_RESOURCE_NOUNS})(?:\s+([A-Z]|\d+|I{{1,3}}|IV|[a-z]+))?\b", before, re.I):
            second = (m.group(2) or "").lower()
            name = m.group(1).lower() + (f" {second}" if second and second not in _STOP and second not in UNITS else "")
            strong.append((m.start(), name))
        for m in _KEEP_PHRASES.finditer(before):
            strong.append((m.start(), m.group(0).lower()))
        for m in re.finditer(r"[A-Za-z][\w-]*", before):
            lw = m.group(0).lower()
            if lw in _STOP or lw in UNITS or lw in _VERBS or any(lw == a.lower() for a in _product_words):
                continue
            weak.append((m.start(), lw))
        # cari di potongan setelah kata sambung terakhir (“… 100 jam dan bahan baku 80”) lebih dulu
        conn = list(re.finditer(r"\b(?:dan|serta|sedangkan|atau)\b|,", before))
        seg_start = conn[-1].end() if conn else 0
        for pool in ([c for c in strong if c[0] >= seg_start], [c for c in weak if c[0] >= seg_start], strong, weak):
            if pool:
                label = [max(pool, key=lambda c: c[0])[1]]
                break
    return " ".join(label), unit


_product_words: list[str] = []


@dataclass
class Draft:
    coef: dict[str, dict[int, float]] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    cap: dict[str, tuple[str, float]] = field(default_factory=dict)
    profit: dict[int, float] = field(default_factory=dict)
    price: dict[int, float] = field(default_factory=dict)
    cost: dict[int, float] = field(default_factory=dict)
    bounds: list[tuple[int, str, float]] = field(default_factory=list)
    totals: list[tuple[str, float]] = field(default_factory=list)
    order: list[str] = field(default_factory=list)


_NAME_NOUNS = r"produk|jenis|tipe|model|merek|merk|barang|kelompok|tahun|nomor|no\.|ke-"


def _skip_number(text: str, n: Num) -> bool:
    """Angka yang merupakan bagian nama (“mesin 2”, “produk 1”), bukan nilai."""
    if n.money or n.pct or n.value != int(n.value) or n.value > 20:
        return False
    before = text[max(0, n.start - 14) : n.start].lower()
    return bool(re.search(rf"\b(?:{_RESOURCE_NOUNS}|{_NAME_NOUNS})\s*$", before))


def _direction(clause: str) -> str:
    if _EQ.search(clause):
        return "="
    if _GE.search(clause) and not re.search(r"paling banyak|tidak lebih|maksimal|maksimum", clause, re.I):
        return ">="
    return "<="


def parse_prose(text: str, allow_int: bool) -> LPResult | None:
    t = normalize(text)
    products = find_products(t)
    if len(products) < 2:
        return None
    global _product_words
    _product_words = [a for p in products for a in p.aliases]
    sense = _sense(t)
    d = Draft()
    ment_all = _mentions(t, products)
    spans = [(m.start, m.end) for m in ment_all]

    for cl in all_clauses(t):
        _analyse_clause(t, cl, products, ment_all, spans, d, sense)

    return _assemble(t, products, d, sense, allow_int)


def _analyse_clause(t: str, cl: Span, products, ment_all, spans, d: Draft, sense: str) -> None:
    text = cl.text
    nums = [n for n in find_numbers(text) if not _skip_number(text, n)]
    if not nums:
        return
    nums = [Num(n.value, n.start + cl.start, n.end + cl.start, n.raw, n.pct, n.money) for n in nums]
    ments = [m for m in ment_all if cl.start <= m.start < cl.end]
    is_profit = bool(_PROFIT.search(text))
    is_sell = bool(_SELL.search(text))
    is_cost = bool(_COST.search(text)) and not is_profit
    is_cap = bool(_CAP.search(text))
    respective = bool(_RESPECTIVE.search(text))

    def owner(n: Num) -> int | None:
        prev = [m for m in ments if m.end <= n.start]
        if prev:
            return prev[-1].product
        nxt = [m for m in ments if m.start >= n.end]
        return nxt[0].product if nxt else None

    if respective and len(ments) >= 2:
        uniq: list[int] = []
        for m in ments:
            if m.product not in uniq:
                uniq.append(m.product)
        money_or_plain = [n for n in nums]
        if len(money_or_plain) == len(uniq):
            label, unit = _resource_label(t, money_or_plain[-1], cl.start, cl.end, spans)
            for p, n in zip(uniq, money_or_plain, strict=True):
                _assign_value(d, p, n, label, unit, is_profit, is_sell, is_cost, sense, text)
            return

    # nilai tujuan (laba/harga/biaya per produk)
    if (is_profit or is_sell or (is_cost and not is_cap)) and ments:
        resource_like = []
        for n in nums:
            label, unit = _resource_label(t, n, cl.start, cl.end, spans)
            p = owner(n)
            if p is None:
                continue
            if (
                is_cost
                and label
                and unit not in ("rp", "rupiah")
                and not n.money
                and label not in ("biaya", "harga", "ongkos")
            ):
                resource_like.append((p, n, label, unit))
                continue
            if is_profit:
                d.profit.setdefault(p, n.value)
            elif is_sell:
                d.price.setdefault(p, n.value)
            else:
                d.cost.setdefault(p, n.value)
        for p, n, label, unit in resource_like:
            _add_coef(d, label, unit, p, n.value)
        return

    # kendala total produksi
    if _TOTAL.search(text) and (is_cap or _DEMAND.search(text)) and len(nums) == 1:
        d.totals.append((_direction(text), nums[0].value))
        return

    # batas permintaan per produk (“permintaan meja paling banyak 30 unit”)
    if ments and (is_cap or _DEMAND.search(text)):
        handled = False
        for n in nums:
            label, unit = _resource_label(t, n, cl.start, cl.end, spans)
            p = owner(n)
            if (
                p is not None
                and (not label or label in ("unit", "buah", "permintaan", "pesanan", "produksi"))
                and (
                    not unit
                    or unit
                    in (
                        "unit",
                        "buah",
                        "potong",
                        "pasang",
                        "lusin",
                        "kodi",
                        "bungkus",
                        "porsi",
                        "botol",
                        "batang",
                        "lembar",
                    )
                )
            ):
                d.bounds.append((p, _direction(text), n.value))
                handled = True
        if handled:
            return

    # kapasitas sumber daya
    if is_cap and not ments:
        for n in nums:
            label, unit = _resource_label(t, n, cl.start, cl.end, spans)
            key = label or unit or f"sumber daya {len(d.cap) + 1}"
            d.cap.setdefault(key, (_direction(text), n.value))
            if unit:
                d.units.setdefault(key, unit)
            if key not in d.order:
                d.order.append(key)
        return

    # koefisien penggunaan sumber daya per produk
    cap_kw = _CAP.search(text)
    for n in nums:
        prev = [m for m in ments if m.end <= n.start]
        if prev:
            p = prev[-1].product
        elif is_cap and cap_kw and cl.start + cap_kw.start() < n.start:
            p = None  # “Pabrik 1 tersedia 4 jam, pintu …” → kapasitas
        else:
            p = owner(n)
        label, unit = _resource_label(t, n, cl.start, cl.end, spans)
        if p is None:
            if is_cap:
                key = label or unit or f"sumber daya {len(d.cap) + 1}"
                d.cap.setdefault(key, (_direction(text), n.value))
                if unit:
                    d.units.setdefault(key, unit)
                if key not in d.order:
                    d.order.append(key)
            continue
        _add_coef(d, label or unit or "sumber daya", unit, p, n.value)


def _assign_value(d: Draft, p: int, n: Num, label: str, unit: str, is_profit, is_sell, is_cost, sense, text) -> None:
    if is_profit:
        d.profit.setdefault(p, n.value)
    elif is_sell:
        d.price.setdefault(p, n.value)
    elif is_cost and (n.money or not label):
        d.cost.setdefault(p, n.value)
    else:
        _add_coef(d, label or unit or "sumber daya", unit, p, n.value)


def _add_coef(d: Draft, label: str, unit: str, p: int, value: float) -> None:
    d.coef.setdefault(label, {})
    d.coef[label].setdefault(p, value)
    if unit:
        d.units.setdefault(label, unit)
    if label not in d.order:
        d.order.append(label)


def _match_capacity(d: Draft, assumptions: list[str]) -> dict[str, tuple[str, float]]:
    caps = dict(d.cap)
    out: dict[str, tuple[str, float]] = {}
    for res in list(d.coef):
        if res in caps:
            out[res] = caps.pop(res)
            continue
        # cocokkan sebagian kata (“perakitan” ~ “waktu perakitan”, “mesin a” ~ “a”)
        hit = next((k for k in caps if k and (k in res or res in k or set(k.split()) & set(res.split()))), None)
        if hit is None:
            same_unit = [k for k in caps if d.units.get(k) and d.units.get(k) == d.units.get(res)]
            unmatched = [k for k in d.coef if k not in out and k not in caps]
            if len(same_unit) == 1 and len([k for k in unmatched if d.units.get(k) == d.units.get(res)]) == 1:
                hit = same_unit[0]
        if hit is not None:
            out[res] = caps.pop(hit)
    for k in caps:
        assumptions.append(
            f"Kapasitas “{k}” ({fmt(caps[k][1])}) tidak dapat dipasangkan dengan penggunaan per produk; diabaikan."
        )
    return out


def _assemble(t: str, products: list[Product], d: Draft, sense: str, allow_int: bool) -> LPResult | None:
    n = len(products)
    names = [f"x{i + 1}" for i in range(n)]
    assumptions: list[str] = []
    obj_label = "keuntungan"
    if sense == "max":
        if d.profit:
            obj = d.profit
        elif d.price and d.cost:
            obj = {p: d.price.get(p, 0) - d.cost.get(p, 0) for p in range(n)}
            obj_label = "keuntungan (harga jual − biaya)"
            assumptions.append("Keuntungan per unit dihitung sebagai harga jual dikurangi biaya.")
        elif d.price:
            obj, obj_label = d.price, "pendapatan"
        else:
            obj = d.cost
            obj_label = "nilai"
    else:
        obj, obj_label = (d.cost or d.price or d.profit), "biaya"
    caps = _match_capacity(d, assumptions)
    lines = []
    desc = []
    if obj and len(obj) == n:
        coefs = [obj.get(p, 0.0) for p in range(n)]
        lines.append(f"{sense} Z = {term_str(coefs, names)}")
        found_obj = True
    else:
        missing = [products[p].name for p in range(n) if p not in obj]
        assumptions.append(
            "Koefisien fungsi tujuan untuk " + ", ".join(missing) + " tidak ditemukan; diisi 1 — periksa kembali."
        )
        coefs = [obj.get(p, 1.0) if obj else 1.0 for p in range(n)]
        lines.append(f"{sense} Z = {term_str(coefs, names)}")
        found_obj = False
    for res in d.order:
        if res not in d.coef:
            continue
        if res not in caps:
            assumptions.append(f"Penggunaan “{res}” per produk ditemukan tetapi kapasitasnya tidak; kendala dilewati.")
            continue
        op, rhs = caps[res]
        row = [d.coef[res].get(p, 0.0) for p in range(n)]
        lines.append(f"{term_str(row, names)} {op} {fmt(rhs)}")
        unit = d.units.get(res, "")
        desc.append(f"{res}{f' ({unit})' if unit and unit != res else ''}")
    for p, op, v in d.bounds:
        row = [1.0 if i == p else 0.0 for i in range(n)]
        lines.append(f"{term_str(row, names)} {op} {fmt(v)}")
        desc.append(f"batas {products[p].name}")
    for op, v in d.totals:
        lines.append(f"{term_str([1.0] * n, names)} {op} {fmt(v)}")
        desc.append("total produksi")
    if len(lines) < 2:
        return None
    model = "\n".join(lines) + _integer_decl(t, names, allow_int, assumptions)
    varline = "\n".join(f"  {nm} = jumlah {p.name}" for nm, p in zip(names, products, strict=True))
    pretty = _pretty(model).split("\n")
    # beri nama setiap kendala
    out = []
    ci = 0
    for ln in pretty:
        if (
            ln.startswith("  ")
            and ("≤" in ln or "≥" in ln or " = " in ln)
            and not ln.strip().endswith("≥ 0")
            and ci < len(desc)
        ):
            out.append(f"{ln}   ({desc[ci]})")
            ci += 1
        else:
            out.append(ln)
    formulation = f"Variabel keputusan:\n{varline}\n" + "\n".join(out).replace(
        "Fungsi tujuan:", f"Fungsi tujuan ({obj_label}):"
    )
    return LPResult(model, formulation, assumptions, n, len(lines) - 1, found_obj)


def build_lp(text: str, allow_int: bool = False) -> LPResult | None:
    for fn in (parse_explicit, parse_table, parse_prose):
        res = fn(text, allow_int)
        if res and res.found_constraints >= 1:
            return res
    return None


def looks_like_lp(text: str) -> bool:
    t = text.lower()
    return bool(
        _OBJ_RE.search(normalize(text))
        or (
            re.search(r"maksim|minim|optimal|sebesar-besar|seminimal", t)
            and re.search(r"memerlukan|membutuhkan|tersedia|kapasitas|kendala|mengandung", t)
        )
    )


__all__ = ["LPResult", "build_lp", "find_products", "looks_like_lp", "word_number", "has"]
