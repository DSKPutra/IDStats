"""Pengisi field per jenis/kunci: mengubah soal cerita menjadi body input solver (struktur sama dengan contoh soal)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.services.story_rules.text import (
    Num,
    Sequence,
    Table,
    find_numbers,
    near_number,
    normalize,
    sentences,
    sequences,
    table_matrix,
    tables,
    word_number,
)

TIME_IN_HOURS = {
    "detik": 1 / 3600,
    "menit": 1 / 60,
    "jam": 1.0,
    "hari": 24.0,
    "minggu": 168.0,
    "bulan": 730.0,
    "tahun": 8760.0,
}


@dataclass
class Ctx:
    raw: str
    text: str
    lower: str
    seqs: list[Sequence]
    tables: list[Table]
    notes: list[str] = field(default_factory=list)
    described: list[str] = field(default_factory=list)

    @classmethod
    def of(cls, raw: str) -> Ctx:
        t = normalize(raw)
        return cls(raw, t, t.lower(), sequences(t), tables(t))

    def note(self, s: str) -> None:
        if s not in self.notes:
            self.notes.append(s)

    def describe(self, label: str, value: Any) -> None:
        self.described.append(f"{label}: {value}")


def _first(pattern: str, ctx: Ctx, after: int = 60, before: int = 0) -> Num | None:
    return near_number(ctx.text, pattern, after=after, before=before)


def _num_or_word(s: str) -> int | None:
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    return word_number(s)


# ---------------------------------------------------------------- statistik

_ALPHA_RE = (
    r"(?:taraf|tingkat|level)\s+(?:nyata|signifikansi|signifikan|keberartian|kesalahan|uji)|\bα\b|\balpha\b|\balfa\b"
)


def alpha(ctx: Ctx) -> float | None:
    n = _first(_ALPHA_RE, ctx, after=25)
    if n:
        return round(n.fraction, 6)
    c = _first(r"(?:tingkat|taraf|selang|derajat)\s+kepercayaan|kepercayaan", ctx, after=25)
    if c:
        return round(1 - c.fraction, 6)
    return None


def confidence(ctx: Ctx) -> float | None:
    c = _first(r"(?:tingkat|taraf|selang|derajat|interval)\s+kepercayaan|kepercayaan", ctx, after=25)
    if c:
        return round(c.fraction, 6)
    a = alpha(ctx)
    return round(1 - a, 6) if a is not None else None


def _question(ctx: Ctx) -> str:
    qs = [
        s.text
        for s in sentences(ctx.text)
        if re.search(
            r"apakah|benarkah|uji(?:lah)?|buktikan|klaim|diklaim|hipotesis|dapatkah|bisakah|cukup bukti|\?",
            s.text,
            re.I,
        )
    ]
    return " ".join(qs) if qs else ctx.text


def alternative(ctx: Ctx) -> str | None:
    q = _question(ctx).lower()
    if re.search(r"berbeda|perbedaan|tidak sama|≠|!=|sama dengan|berubah|menyimpang", q):
        return "two-sided"
    if re.search(
        r"lebih (?:besar|tinggi|banyak|lama|berat|baik|efektif|mahal)|melebihi|meningkat|naik|di atas|bertambah|lebih dari|>",
        q,
    ):
        return "greater"
    if re.search(
        r"kurang dari|lebih (?:kecil|rendah|sedikit|cepat|singkat|murah|ringan|pendek)|menurun|turun|di bawah|berkurang|<",
        q,
    ):
        return "less"
    return None


_SAMPLE_UNITS = (
    r"orang|mahasiswa|siswa|responden|sampel|pelanggan|karyawan|pegawai|pasien|keluarga|rumah tangga|petani|"
    r"botol|kemasan|kaleng|bungkus|lampu|bola lampu|ban|baterai|unit|buah|produk|barang|kotak|karung|toko|data|pengamatan|kali|hari"
)


def sample_n(ctx: Ctx) -> int | None:
    m = re.search(r"\bn\s*=\s*(\d+)", ctx.text)
    if m:
        return int(m.group(1))
    m = re.search(
        r"(?:sampel|contoh)\s+(?:acak\s+)?(?:sebanyak|berukuran|terdiri (?:atas|dari)|dari|berisi)?\s*(\d+)", ctx.lower
    )
    if m:
        return int(m.group(1))
    m = re.search(
        rf"(?:diambil|dipilih|diteliti|diamati|diperiksa|diuji|disurvei|mengambil|memilih|meneliti|memeriksa|menguji|survei terhadap)\s+(?:secara acak\s+)?(\d+)\s+(?:{_SAMPLE_UNITS})",
        ctx.lower,
    )
    if m:
        return int(m.group(1))
    m = re.search(
        rf"(\d+)\s+(?:{_SAMPLE_UNITS})\b[^.]*?(?:diambil|dipilih|sebagai sampel|secara acak|diteliti|diperiksa)",
        ctx.lower,
    )
    if m:
        return int(m.group(1))
    return None


def _not_in_seq(ctx: Ctx, n: Num | None) -> Num | None:
    if n is None:
        return None
    for s in ctx.seqs:
        if s.start <= n.start < s.end:
            return None
    return n


def mu0(ctx: Ctx) -> float | None:
    claim = r"diklaim|klaim|menyatakan|dinyatakan|menurut|mengatakan|standar|seharusnya|tertera|tercantum|dijanjikan|spesifikasi|target|hipotesis|apakah|benarkah|biasanya|selama ini|sebelumnya|rata-rata populasi|ketentuan"
    for s in sentences(ctx.text):
        if re.search(claim, s.text, re.I):
            m = re.search(r"(?:rata-rata|rerata|mean|μ\s*0?|mu0?)\b", s.text, re.I)
            if m:
                n = _not_in_seq(ctx, near_number(s.text[m.end() :], r"^", after=80))
                if n and not n.pct:
                    return n.value
    n = _first(r"μ\s*0|μ₀|mu0|\bh0\s*:\s*μ\s*=", ctx, after=10)
    return n.value if n else None


def sample_mean(ctx: Ctx) -> float | None:
    for s in sentences(ctx.text):
        if re.search(
            r"sampel|diperoleh|didapat|ternyata|hasil|menunjukkan|tercatat|x̄|xbar", s.text, re.I
        ) and not re.search(r"diklaim|klaim|menyatakan|standar|seharusnya|tertera", s.text, re.I):
            m = re.search(r"rata-rata(?:nya)?|rerata|x̄|xbar|mean", s.text, re.I)
            if m:
                n = near_number(s.text[m.end() :], r"^", after=60)
                if n and not n.pct:
                    return n.value
    return None


def sample_sd(ctx: Ctx, population: bool) -> float | None:
    for s in sentences(ctx.text):
        m = re.search(r"simpangan baku|standar deviasi|deviasi standar|standard deviation|σ|\bs\s*=", s.text, re.I)
        if not m:
            continue
        is_pop = bool(re.search(r"populasi|σ|diketahui", s.text, re.I))
        if is_pop == population:
            n = near_number(s.text[m.end() :], r"^", after=50)
            if n:
                return n.value
    return None


def proportion_pairs(ctx: Ctx) -> list[tuple[int, int]]:
    out = []
    for m in re.finditer(
        r"(\d+)\s+(?:orang\s+|buah\s+|unit\s+)?(?:di\s?antaranya\s+)?(?:dari|di antara)\s+(\d+)", ctx.lower
    ):
        a, b = int(m.group(1)), int(m.group(2))
        if a <= b:
            out.append((a, b))
    if not out:
        for m in re.finditer(
            r"(?:dari|di antara)\s+(\d+)\s+[^.]{0,60}?,?\s*(?:sebanyak\s+)?(\d+)\s+(?:orang|buah|unit|di antaranya|diantaranya)?",
            ctx.lower,
        ):
            b, a = int(m.group(1)), int(m.group(2))
            if a <= b:
                out.append((a, b))
    return out


def p0(ctx: Ctx) -> float | None:
    for s in sentences(ctx.text):
        if re.search(
            r"diklaim|klaim|menyatakan|dinyatakan|menurut|standar|seharusnya|tidak lebih|paling banyak|lebih dari|kurang dari|proporsi|persentase|apakah",
            s.text,
            re.I,
        ):
            for n in find_numbers(s.text):
                if n.pct:
                    return round(n.value / 100, 6)
    m = re.search(r"\bp0?\s*=\s*(\d+(?:[.,]\d+)?)", ctx.text)
    return float(m.group(1).replace(",", ".")) if m else None


# ---------------------------------------------------------------- distribusi


def distribution(ctx: Ctx) -> dict[str, Any] | None:
    t = ctx.lower
    if (
        "binomial" in t
        or re.search(r"\b(?:berhasil|sukses|cacat|rusak|lulus)\b[^.]*\bdari\b\s*\d+|peluang (?:setiap|tiap|masing)", t)
        or (
            re.search(r"(?:diambil|dipilih|diperiksa|dilempar|dilakukan|sebanyak)\s+\d+", t)
            and re.search(r"cacat|rusak|berhasil|sukses|lulus|setuju|sembuh|gagal|muncul", t)
            and not re.search(r"simpangan baku|rata-rata", t)
        )
    ):
        dist = "binomial"
    elif (
        "poisson" in t
        or re.search(r"rata-rata\s+\d+[^.]*\b(?:per|setiap|tiap)\b", t)
        and re.search(r"tepat|paling banyak|paling sedikit|lebih dari|kurang dari", t)
        and not re.search(r"simpangan baku|standar deviasi|normal", t)
    ):
        dist = "poisson"
    elif re.search(r"eksponensial|exponential", t):
        dist = "exponential"
    elif re.search(r"seragam|uniform", t):
        dist = "uniform"
    elif re.search(r"normal|simpangan baku|standar deviasi", t):
        dist = "normal"
    else:
        return None
    params: dict[str, float] = {}
    if dist == "normal":
        mu = _first(r"rata-rata|rerata|mean|μ|ekspektasi", ctx, after=40)
        sd = _first(r"simpangan baku|standar deviasi|deviasi standar|σ", ctx, after=40)
        var = _first(r"varians|ragam|σ\^?2|σ²", ctx, after=30)
        if mu:
            params["mu"] = mu.value
        if sd:
            params["sigma"] = sd.value
        elif var:
            params["sigma"] = round(var.value**0.5, 6)
    elif dist == "binomial":
        n = _first(r"\bn\s*=|sebanyak|dari|diambil|dilempar|dilakukan|percobaan|diperiksa", ctx, after=25)
        p = _first(r"peluang|probabilitas|kemungkinan|\bp\s*=|persentase|sebesar", ctx, after=30)
        if n:
            params["n"] = int(n.value)
        if p:
            params["p"] = round(p.fraction, 6)
    elif dist == "poisson":
        lam = _first(r"rata-rata|rerata|λ|lambda", ctx, after=30)
        if lam:
            params["lam"] = lam.value
    elif dist == "exponential":
        lam = _first(r"laju|λ|lambda", ctx, after=30)
        mean = _first(r"rata-rata|rerata", ctx, after=30)
        if lam:
            params["lam"] = lam.value
        elif mean and mean.value:
            params["lam"] = round(1 / mean.value, 6)
    elif dist == "uniform":
        m = re.search(r"antara\s+(\d+(?:[.,]\d+)?)\s+(?:dan|hingga|sampai|-)\s+(\d+(?:[.,]\d+)?)", ctx.text)
        if m:
            params["a"], params["b"] = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
    out: dict[str, Any] = {"dist": dist, "params": params}
    q = _question(ctx)
    discrete = dist in ("binomial", "poisson")
    between = re.search(r"antara\s+(\d+(?:[.,]\d+)?)\s+(?:dan|hingga|sampai|-)\s+(\d+(?:[.,]\d+)?)", q)
    if dist != "uniform" and between:
        out["mode"], out["a"], out["b"] = (
            "between",
            float(between.group(1).replace(",", ".")),
            float(between.group(2).replace(",", ".")),
        )
        return out

    def val(pattern: str) -> float | None:
        n = near_number(q, pattern, after=25)
        return n.value if n else None

    for pattern, mode, shift in (
        (r"paling sedikit|sekurang-kurangnya|minimal|setidaknya|tidak kurang dari|≥|>=", "sf", -1),
        (r"lebih dari|melebihi|di atas|lebih besar dari|>", "sf", 0),
        (r"paling banyak|maksimal|tidak lebih dari|≤|<=", "cdf", 0),
        (r"kurang dari|di bawah|lebih kecil dari|<", "cdf", -1),
        (r"tepat|sama dengan|persis", "pdf", 0),
    ):
        v = val(pattern)
        if v is not None:
            out["mode"] = mode
            out["x"] = v + (shift if discrete else 0)
            return out
    pp = _first(r"persentil|kuantil|nilai x sehingga|batas", ctx, after=30)
    if pp:
        out["mode"], out["p"] = "ppf", round(pp.fraction, 6)
    return out


# ---------------------------------------------------------------- antrian


_ARR = r"datang|kedatangan|tiba|masuk|mengantre|mengantri|arrival|berdatangan"
_SVC = r"dilayani|melayani|pelayanan|layanan|service|menyelesaikan|memproses|diproses|kecepatan|memperbaiki|diperbaiki"


def _rate_in(sentence: str) -> tuple[float, str] | None:
    for n in find_numbers(sentence):
        if n.pct:
            continue
        after = sentence[n.end : n.end + 40].lower()
        m = re.match(
            r"\s*(?:[a-z]+\s+){0,3}?(?:per|/|setiap|tiap|dalam\s+(?:1|satu|se))\s*(?:\d+\s*)?(detik|menit|jam|hari|minggu)",
            after,
        )
        if m:
            return n.value, m.group(1)
        before = sentence[max(0, n.start - 45) : n.start].lower()
        m2 = re.match(r"\s*(detik|menit|jam|hari)", after)
        if m2 and re.search(r"setiap|tiap|selang|waktu|rata-rata|lama|membutuhkan|memerlukan|selama", before):
            return 1 / n.value if n.value else 0.0, m2.group(1)
    return None


def queue_rates(ctx: Ctx) -> tuple[float | None, float | None, str | None]:
    lam = mu = None
    lam_u = mu_u = None
    for s in sentences(ctx.text):
        st = s.text
        if lam is None and re.search(_ARR, st, re.I):
            # potong bagian layanan bila satu kalimat memuat keduanya
            part = (
                re.split(_SVC, st, flags=re.I)[0]
                if re.search(_SVC, st, re.I) and re.search(_ARR, st, re.I).start() < re.search(_SVC, st, re.I).start()
                else st
            )
            r = _rate_in(part)
            if r:
                lam, lam_u = r
        if mu is None and re.search(_SVC, st, re.I):
            m = re.search(_SVC, st, re.I)
            r = _rate_in(st[m.start() - 60 if m.start() > 60 else 0 :]) if m else None
            if r:
                mu, mu_u = r
    unit = lam_u or mu_u
    if lam is not None and mu is not None and lam_u and mu_u and lam_u != mu_u:
        mu = mu * TIME_IN_HOURS[lam_u] / TIME_IN_HOURS[mu_u]
        ctx.note(f"Laju pelayanan dikonversi ke satuan per {lam_u}.")
    return (round(lam, 6) if lam is not None else None), (round(mu, 6) if mu is not None else None), unit


_SERVER_WORDS = r"server|pelayan|kasir|loket|teller|petugas|saluran|mekanik|montir|dokter|operator|pompa(?: bensin)?|counter|jalur|dermaga|tempat cuci|pegawai|karyawan|fasilitas|meja layanan|gerbang|pintu tol"


def servers(ctx: Ctx) -> int | None:
    m = re.search(
        rf"\b(\d+|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|seorang|sebuah)\s+(?:orang\s+|buah\s+|unit\s+)?(?:{_SERVER_WORDS})\b",
        ctx.lower,
    )
    if m:
        return _num_or_word(m.group(1))
    m = re.search(rf"(?:{_SERVER_WORDS})\s+(?:sebanyak|berjumlah|ada)\s+(\d+|satu|dua|tiga|empat|lima)", ctx.lower)
    if m:
        return _num_or_word(m.group(1))
    if re.search(r"satu-satunya|tunggal|single", ctx.lower):
        return 1
    return None


# ---------------------------------------------------------------- persediaan


def _value(ctx: Ctx, pattern: str, after: int = 50) -> Num | None:
    return _first(pattern, ctx, after=after)


def inventory(ctx: Ctx) -> dict[str, float]:
    out: dict[str, float] = {}
    d = _value(ctx, r"permintaan|kebutuhan|penjualan|pemakaian|penggunaan|demand")
    if d:
        val = d.value
        tail = ctx.lower[d.end : d.end + 30]
        if re.match(r"\s*\w*\s*(?:per|setiap|tiap)\s*bulan|\s*\w*\s*/\s*bulan", tail) and re.search(
            r"per tahun|/tahun|setahun|tahunan", ctx.lower
        ):
            val *= 12
            ctx.note("Permintaan bulanan dikonversi ke tahunan (×12) agar sesuai dengan biaya simpan per tahun.")
        elif re.match(r"\s*\w*\s*(?:per|setiap|tiap)\s*minggu", tail) and re.search(
            r"per tahun|/tahun|setahun|tahunan", ctx.lower
        ):
            val *= 52
            ctx.note("Permintaan mingguan dikonversi ke tahunan (×52).")
        out["demand"] = val
    k = _value(
        ctx, r"biaya (?:setiap kali |sekali |per )?(?:pesan|pemesanan|order|setup|persiapan|penyiapan)|ongkos pesan"
    )
    if k:
        out["setup"] = k.value
    c = _value(
        ctx, r"harga (?:per unit|beli|barang|pembelian|satuan)|biaya (?:per unit|pembelian|produksi per unit)|harga"
    )
    if c:
        out["unit_cost"] = c.value
    h = _value(ctx, r"biaya (?:simpan|penyimpanan|menyimpan|pemeliharaan|holding)")
    if h:
        if h.pct:
            out["holding_rate"] = round(h.value / 100, 6)
            if "unit_cost" in out:
                out["holding"] = round(out["unit_cost"] * h.value / 100, 6)
                ctx.note(f"Biaya simpan = {h.raw.strip()} × harga per unit.")
        else:
            out["holding"] = h.value
    s = _value(ctx, r"biaya (?:kekurangan|kehabisan|backorder|stockout)|penalti")
    if s:
        out["shortage"] = s.value
    p = _value(ctx, r"laju produksi|kapasitas produksi|tingkat produksi|mampu memproduksi|produksi (?:per|sebesar)")
    if p:
        out["production_rate"] = p.value
    lt = _value(ctx, r"waktu tunggu|lead time|waktu pengiriman|tenggang waktu|waktu ancang")
    if lt:
        out["lead_time"] = lt.value
    return out


# ---------------------------------------------------------------- transportasi & penugasan

_SUPPLY = re.compile(r"kapasitas|penawaran|supply|persediaan|tersedia|produksi|sumber|pasokan|stok", re.I)
_DEMAND = re.compile(r"permintaan|kebutuhan|demand|tujuan|pesanan", re.I)


def transport(ctx: Ctx) -> dict[str, Any] | None:
    for tb in ctx.tables:
        rows = [r for r in tb.rows if not _DEMAND.search(r.label)]
        demand_rows = [r for r in tb.rows if _DEMAND.search(r.label)]
        if len(rows) < 1:
            continue
        widths = {len(r.values) for r in rows}
        if len(widths) != 1:
            continue
        w = widths.pop()
        if not demand_rows or len(demand_rows[0].values) != w - 1:
            continue
        costs = [r.values[:-1] for r in rows]
        header = tb.header
        dests = header[-w:-1] if len(header) >= w else [f"T{j + 1}" for j in range(w - 1)]
        return {
            "costs": costs,
            "supply": [r.values[-1] for r in rows],
            "demand": demand_rows[0].values,
            "sources": [r.label or f"S{i + 1}" for i, r in enumerate(rows)],
            "destinations": dests,
        }
    # prosa: “biaya dari A ke X Rp5”, “A berkapasitas 100”, “X membutuhkan 80”
    cost: dict[tuple[str, str], float] = {}
    for m in re.finditer(
        r"(?:dari\s+)?(?:pabrik|gudang|sumber|kota|depot)?\s*([A-Z][\w]*)\s+ke\s+(?:pabrik|gudang|kota|toko|tujuan|pasar|agen)?\s*([A-Z][\w]*)[^.;\n\d]{0,30}?(?:rp\s*)?(\d+(?:[.,]\d+)*)",
        ctx.text,
        re.I,
    ):
        a, b = m.group(1), m.group(2)
        if a.lower() in ("dari", "ke", "biaya") or b.lower() in ("dari", "ke"):
            continue
        cost[(a, b)] = find_numbers(m.group(3))[0].value if find_numbers(m.group(3)) else float(m.group(3))
    if len(cost) < 2:
        return None
    srcs = list(dict.fromkeys(a for a, _ in cost))
    dsts = list(dict.fromkeys(b for _, b in cost))
    supply, demand = [], []
    for s in srcs:
        n = near_number(
            ctx.text,
            rf"\b{re.escape(s)}\b[^.;\d]{{0,40}}?(?:kapasitas|memproduksi|menyediakan|persediaan|penawaran|memiliki|tersedia|sebanyak)",
            after=30,
        )
        supply.append(n.value if n else None)
    for d in dsts:
        n = near_number(
            ctx.text,
            rf"\b{re.escape(d)}\b[^.;\d]{{0,40}}?(?:membutuhkan|permintaan|kebutuhan|memerlukan|memesan|sebanyak)",
            after=30,
        )
        demand.append(n.value if n else None)
    if None in supply or None in demand:
        return None
    return {
        "costs": [[cost.get((s, d), 0.0) for d in dsts] for s in srcs],
        "supply": supply,
        "demand": demand,
        "sources": srcs,
        "destinations": dsts,
    }


def matrix_table(ctx: Ctx) -> tuple[list[list[float]], list[str], list[str]] | None:
    best = None
    for tb in ctx.tables:
        mat, rl, cl = table_matrix(tb)
        if (
            len(mat) >= 2
            and len(mat[0]) >= 2
            and (best is None or len(mat) * len(mat[0]) > len(best[0]) * len(best[0][0]))
        ):
            best = (mat, rl, cl)
    return best


# ---------------------------------------------------------------- proyek (CPM/PERT)

_CODE = r"[A-Z]\d?"


def activities(ctx: Ctx) -> list[tuple[str, list[str], list[float], str]]:
    acts: dict[str, tuple[list[str], list[float], str]] = {}
    chunks = [ln for ln in ctx.text.split("\n") if ln.strip()]
    if len(chunks) <= 2:
        chunks = [s.text for s in sentences(ctx.text)]
    for ch in chunks:
        line = ch.strip()
        m = re.match(rf"^(?:aktivitas|kegiatan|pekerjaan|tugas|activity|task)?\s*({_CODE})(?![a-z])\b", line, re.I)
        if not m or not re.fullmatch(_CODE, m.group(1)):
            m = re.search(rf"(?:aktivitas|kegiatan|pekerjaan|tugas)\s+({_CODE})\b", line)
            if not m:
                continue
        code = m.group(1)
        rest = line[m.end() :]
        nums = [n for n in find_numbers(rest)]
        preds = [c for c in re.findall(rf"(?<![\w-])({_CODE})(?![\w])", rest) if c != code]
        if re.search(
            r"tanpa|tidak ada|tidak memiliki|awal|pertama|dimulai langsung|^\s*[|\s]*-", rest, re.I
        ) and not re.search(r"setelah|sesudah|didahului|menunggu|bergantung", rest, re.I):
            preds = []
        name = ""
        if "|" in line:
            cells = [c.strip() for c in line.split("|")]
            texty = [c for c in cells[1:] if re.search(r"[a-z]{3,}", c)]
            name = texty[-1] if texty else ""
        if nums:
            acts[code] = (list(dict.fromkeys(preds)), [n.value for n in nums], name)
    return [(c, p, v, nm) for c, (p, v, nm) in acts.items()]


# ---------------------------------------------------------------- jaringan


def edges(ctx: Ctx) -> list[tuple[str, str, list[float]]]:
    out: list[tuple[str, str, list[float]]] = []
    seen = set()
    for ln in ctx.text.split("\n"):
        m = re.match(
            r"^\s*([A-Za-z]\w{0,15})\s*(?:-|–|→|->|ke|,|\s)\s*([A-Za-z]\w{0,15})\s*[:|=,]?\s*(\d+(?:[.,]\d+)?(?:\s+\d+(?:[.,]\d+)?)?)\s*\w*\s*$",
            ln,
        )
        if m:
            vals = [n.value for n in find_numbers(m.group(3))]
            key = (m.group(1), m.group(2))
            if key not in seen:
                out.append((m.group(1), m.group(2), vals))
                seen.add(key)
    if len(out) >= 3:
        return out
    out, seen = [], set()
    for m in re.finditer(
        r"(?:dari\s+)?(?:kota|titik|node|simpul|lokasi|desa|gudang|stasiun)?\s*\b([A-Z]\w*)\s*(?:ke|menuju|dengan|-|–|→)\s*(?:kota|titik|node|simpul|lokasi|desa)?\s*\b([A-Z]\w*)\b[^.;\n\d]{0,40}?(\d+(?:[.,]\d+)?)",
        ctx.text,
    ):
        a, b = m.group(1), m.group(2)
        if a in ("Dari", "Jarak", "Biaya", "Waktu") or a == b:
            continue
        key = (a, b)
        if key not in seen:
            out.append((a, b, [find_numbers(m.group(3))[0].value]))
            seen.add(key)
    return out


def endpoints(ctx: Ctx, nodes: list[str]) -> tuple[str | None, str | None]:
    q = (
        " ".join(
            s.text
            for s in sentences(ctx.text)
            if re.search(
                r"terpendek|tercepat|termurah|rute|lintasan|jalur|aliran|maksimum|dialirkan|tentukan|berapa",
                s.text,
                re.I,
            )
        )
        or ctx.text
    )
    m = re.search(
        r"dari\s+(?:kota|titik|node|simpul|sumber)?\s*([A-Z]\w*)\s+(?:ke|menuju|hingga|sampai)\s+(?:kota|titik|node|simpul|tujuan)?\s*([A-Z]\w*)",
        q,
    )
    if m and m.group(1) in nodes and m.group(2) in nodes:
        return m.group(1), m.group(2)
    return (nodes[0], nodes[-1]) if nodes else (None, None)


# ---------------------------------------------------------------- knapsack


def items(ctx: Ctx) -> tuple[list[str], list[float], list[float]] | None:
    for tb in ctx.tables:
        hdr = [h.lower() for h in tb.header]
        if len(tb.rows) >= 2 and all(len(r.values) >= 2 for r in tb.rows):
            wi = next((i for i, h in enumerate(hdr[-2:]) if re.search(r"berat|bobot|ukuran|volume|kg", h)), 0)
            vi = 1 - wi
            return (
                [r.label or f"Barang {i + 1}" for i, r in enumerate(tb.rows)],
                [r.values[-2 + wi] for r in tb.rows],
                [r.values[-2 + vi] for r in tb.rows],
            )
    names, w, v = [], [], []
    for s in sentences(ctx.text):
        m = re.search(r"(?:barang|item|benda|kotak|paket|proyek)\s+([A-Z0-9]\w*)", s.text, re.I)
        bw = near_number(s.text, r"berat(?:nya)?|bobot|ukuran|volume", after=25)
        bv = near_number(s.text, r"nilai(?:nya)?|harga(?:nya)?|keuntungan|manfaat|laba", after=30)
        if m and bw and bv:
            names.append(m.group(1))
            w.append(bw.value)
            v.append(bv.value)
    return (names, w, v) if len(names) >= 2 else None


# ---------------------------------------------------------------- peramalan


def horizon(ctx: Ctx, n_data: int | None) -> int | None:
    m = re.search(
        r"(\d+|satu|dua|tiga|empat|lima|enam)\s+(?:periode|bulan|minggu|tahun|hari|kuartal|triwulan)\s+(?:ke depan|berikutnya|mendatang|selanjutnya)",
        ctx.lower,
    )
    if m:
        return _num_or_word(m.group(1))
    m = re.search(r"(?:periode|bulan|minggu|tahun|hari)\s+ke[- ]?(\d+)", ctx.lower)
    if m and n_data and int(m.group(1)) > n_data:
        return int(m.group(1)) - n_data
    if re.search(r"(?:periode|bulan|minggu|tahun|hari)\s+(?:berikutnya|depan|selanjutnya|mendatang)", ctx.lower):
        return 1
    return None


def longest_seq(ctx: Ctx) -> Sequence | None:
    return max(ctx.seqs, key=lambda s: len(s.values), default=None)


# ---------------------------------------------------------------- registri angka (field number/integer)

NumberRule = Callable[[Ctx], float | None]


def _pat(pattern: str, after: int = 50, fraction: bool = False) -> NumberRule:
    def rule(ctx: Ctx) -> float | None:
        n = _first(pattern, ctx, after=after)
        if not n:
            return None
        return round(n.fraction, 6) if fraction else n.value

    return rule


NUMBER_RULES: dict[str, NumberRule] = {
    "mu0": mu0,
    "mean": sample_mean,
    "sd": lambda c: sample_sd(c, False),
    "sigma": lambda c: sample_sd(c, True),
    "n": lambda c: sample_n(c),
    "n1": lambda c: sample_n(c),
    "confidence": confidence,
    "p0": p0,
    "deadline": _pat(
        r"batas waktu|tenggat|deadline|harus (?:sudah )?selesai dalam|diselesaikan dalam|target (?:waktu )?penyelesaian|selesai paling lambat",
        40,
    ),
    "current_time": _pat(r"saat ini (?:proyek )?(?:sudah )?berjalan|hari ke|minggu ke|pada waktu", 30),
    "capacity": _pat(r"kapasitas|daya angkut|maksimal|mampu (?:memuat|menampung|membawa)|batas berat", 40),
    "total": _pat(r"total|sebanyak|tersedia|jumlah", 40),
    "steps": _pat(r"(?:setelah|dalam)\s+", 15),
    "k": _pat(
        r"kapasitas (?:sistem|ruang tunggu|antrian|tempat)|maksimal|paling banyak|hanya (?:dapat|mampu) menampung", 40
    ),
    "population": _pat(r"populasi|sebanyak|jumlah (?:mesin|pelanggan|unit)|memiliki", 40),
    "server_cost": _pat(
        r"biaya (?:per |setiap |tiap )?(?:server|pelayan|kasir|petugas|operator|karyawan|pegawai|mekanik|teknisi)", 50
    ),
    "wait_cost": _pat(r"biaya (?:menunggu|tunggu|waktu tunggu|kehilangan|antre|antri)", 50),
    "horizon": lambda c: horizon(c, len(longest_seq(c).values) if longest_seq(c) else None),
    "season": _pat(r"musim(?:an)?\s*(?:sebanyak|=|dengan panjang)?|panjang musim", 25),
    "beta": _pat(r"β|beta|konstanta tren|pemulusan tren", 20),
    "cost": _pat(r"biaya (?:survei|eksperimen|informasi|riset|penelitian|uji)", 50),
    "discount": _pat(r"faktor diskon|diskon|discount", 25, fraction=True),
}


def number_for(key: str, ftype: str, ctx: Ctx, variant_id: str) -> float | None:
    leaf = key.split(".")[-1]
    if variant_id.startswith(("mms", "mmsk", "finite", "mg1", "mds", "queue", "priority")) or leaf in (
        "lam",
        "mu",
        "s",
    ):
        if leaf in ("lam", "mu"):
            lam, mu, _ = queue_rates(ctx)
            return lam if leaf == "lam" else mu
        if leaf == "s":
            return servers(ctx)
    if leaf == "alpha" and ftype == "number":
        if variant_id in ("exp-smoothing", "holt", "seasonal", "reinforcement-learning"):
            return _pat(r"α|alpha|alfa|konstanta (?:pemulusan|penghalusan)|smoothing|faktor pemulusan", 25)(ctx)
        return None
    if leaf == "n" and variant_id == "moving-average":
        m = re.search(r"(?:rata-rata bergerak|moving average)\D{0,15}?(\d+)", ctx.lower) or re.search(
            r"(\d+)[- ](?:bulanan|periodean|mingguan)", ctx.lower
        )
        return int(m.group(1)) if m else None
    rule = NUMBER_RULES.get(leaf)
    v = rule(ctx) if rule else None
    if v is not None and ftype == "integer":
        v = int(round(v))
    return v
