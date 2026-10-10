"""Penerjemah soal cerita berbasis aturan (tanpa layanan AI, tanpa API key).

``interpret`` mencoba setiap varian halaman, mengisi field dari teks soal dengan aturan bahasa Indonesia
(angka “Rp70.000”, “5%”, “0,05”; kata kunci “tersedia”, “paling sedikit”, “taraf nyata”, …), lalu memilih varian
dengan isian paling lengkap + kata kunci paling cocok. Field yang tidak ditemukan dilaporkan agar diisi manual.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import EXAMPLES_DIR
from app.core.errors import SolverError
from app.services.story_rules import fill, lp
from app.services.story_rules.fill import Ctx

_SLUG = re.compile(r"^[a-z0-9-]+$")
MAX_STORY_CHARS = 6000

ESSENTIAL_TYPES = {
    "numbers",
    "matrix",
    "textarea",
    "graph",
    "groups",
    "variables",
    "cells",
    "number",
    "integer",
    "text",
    "labels",
}

# kata kunci yang menguatkan pilihan varian
VARIANT_HINTS: dict[str, str] = {
    "big-m": r"big[\s-]?m\b",
    "two-phase": r"dua fase|two[\s-]?phase",
    "dual-simplex": r"dual simpleks|dual simplex",
    "revised-simplex": r"direvisi|revised",
    "duality": r"dual\b|dualitas|sensitivitas|harga bayangan|shadow price",
    "upper-bound": r"batas atas|upper bound",
    "interior-point": r"titik interior|interior point|karmarkar",
    "branch-and-bound": r"biner|0\s*(?:atau|/)\s*1|ya\s*(?:atau|/)\s*tidak|branch",
    "mip": r"bilangan bulat|integer|bulat",
    "assignment": r"penugasan|ditugaskan|menugaskan|hungaria|setiap (?:pekerja|karyawan|mesin|orang|salesman|tim)",
    "transportation": r"angkut|pengiriman|transportasi|dikirim|distribusi|gudang|penawaran",
    "shortest-path": r"terpendek|tercepat|termurah|lintasan|rute",
    "minimum-spanning-tree": r"menghubungkan (?:semua|seluruh)|kabel|pipa|pohon rentang|spanning|jaringan minimum",
    "max-flow": r"aliran maksimum|maksimum[^.]*dialirkan|kapasitas (?:jalur|pipa|jalan)|max(?:imum)? flow",
    "min-cost-flow": r"aliran biaya minimum|min(?:imum)? cost flow",
    "pert": r"optimis|pesimis|paling mungkin|tiga estimasi|pert\b",
    "crashing": r"crash|dipercepat|percepatan|time-cost",
    "pert-cost": r"anggaran|biaya aktual|pert/cost",
    "cpm": r"jalur kritis|critical path|cpm",
    "mmsk": r"kapasitas (?:sistem|ruang tunggu|antrian|tempat)|hanya (?:dapat|mampu) menampung|maksimal \d+ (?:pelanggan|orang|mobil)",
    "finite-source": r"populasi terbatas|sumber terbatas|(?:mesin|unit)[^.]*rusak|memperbaiki mesin",
    "mg1": r"simpangan baku waktu (?:pelayanan|layanan)|distribusi (?:umum|sembarang)",
    "mds": r"konstan|deterministik|tetap selama|selalu \d+ menit",
    "queue-cost": r"biaya (?:server|pelayan|kasir|petugas|menunggu|tunggu)",
    "priority": r"prioritas",
    "eoq-backorder": r"kekurangan|backorder|kehabisan diizinkan|stockout",
    "quantity-discount": r"diskon|potongan harga|harga (?:grosir|bertingkat)",
    "epq": r"laju produksi|diproduksi sendiri|kapasitas produksi",
    "newsvendor": r"koran|majalah|sisa[^.]*dijual|tidak terjual|kedaluwarsa|basi|musiman",
    "wagner-whitin": r"wagner|permintaan (?:setiap|tiap|per) (?:bulan|periode)[^.]*berbeda",
    "rq": r"titik pemesanan ulang|reorder|tingkat layanan|safety stock|stok pengaman",
    "moving-average": r"rata-rata bergerak|moving average",
    "exp-smoothing": r"pemulusan eksponensial|exponential smoothing|penghalusan eksponensial|konstanta pemulusan",
    "holt": r"\bholt\b|tren\b[^.]*pemulusan|double exponential",
    "trend-regression": r"regresi (?:tren|linier)|tren linier|garis tren",
    "seasonal": r"musim|kuartal|triwulan",
    "arima": r"arima|box[- ]jenkins",
    "last-value": r"nilai terakhir|naive|naif",
    "absorbing": r"penyerap|absorbing|lunas|macet|keluar dari sistem",
    "ctmc": r"waktu kontinu|laju transisi|per jam",
    "decision-experiment": r"survei|eksperimen|informasi tambahan|riset pasar|evsi",
    "decision-tree": r"pohon keputusan",
    "zero-sum": r"strategi campuran|zero[- ]sum|jumlah nol",
    "saddle-point": r"titik pelana|saddle",
    "t-paired": r"berpasangan|sebelum[^.]*sesudah|sebelum dan sesudah|pre[- ]?test|post[- ]?test|pasangan",
    "t-independent": r"dua (?:kelompok|sampel|kelas|metode|merek|populasi)|independen|kelompok a[^.]*kelompok b",
    "z-test": r"simpangan baku populasi|σ\s*=|standar deviasi populasi|uji[- ]z",
    "t-one-sample": r"uji[- ]t|rata-rata",
    "proportion-test": r"proporsi|persentase|\d+\s*%",
    "chi-square-gof": r"kecocokan|goodness|sesuai dengan (?:proporsi|perbandingan|distribusi)|frekuensi harapan",
    "chi-square-independence": r"independensi|hubungan antara|bebas (?:dari|terhadap)|tabel kontingensi",
    "f-test": r"varians|ragam|keragaman|homogen",
    "confidence-interval": r"interval|selang kepercayaan|estimasi|taksiran|pendugaan",
    "anova-one-way": r"anova|analisis varians|tiga (?:kelompok|metode|perlakuan|jenis)|lebih dari dua",
    "tukey-hsd": r"tukey|uji lanjut|post[- ]hoc",
    "anova-two-way": r"dua arah|dua faktor",
    "kruskal-wallis": r"kruskal",
    "mann-whitney": r"mann|whitney",
    "wilcoxon": r"wilcoxon",
    "correlation": r"korelasi|hubungan|keeratan",
    "regression-simple": r"regresi|pengaruh|persamaan garis|memprediksi|ramalkan",
    "regression-multiple": r"berganda|beberapa variabel|dua variabel bebas",
    "descriptive": r"rata-rata|median|modus|simpangan|kuartil|statistik deskriptif|ringkas",
    "frequency-table": r"distribusi frekuensi|tabel frekuensi|kelas interval|histogram",
    "scatter": r"diagram pencar|scatter",
    "shapiro-wilk": r"normal|shapiro",
    "kolmogorov-smirnov": r"kolmogorov|smirnov",
    "knapsack": r"knapsack|ransel|tas|daya angkut|muatan",
    "resource-allocation": r"alokasi|mengalokasikan|dibagikan",
    "stagecoach": r"tahap|stagecoach",
}

DOMAINS: list[tuple[str, str, str]] = [
    (
        "transportasi",
        "/or/transportation",
        r"(?:biaya (?:angkut|pengiriman|transportasi|distribusi)|mengirim|dikirim|diangkut)[^.]*|gudang[^.]*(?:toko|kota|tujuan)",
    ),
    (
        "penugasan",
        "/or/transportation?metode=assignment",
        r"penugasan|ditugaskan|menugaskan|setiap (?:pekerja|karyawan|orang) (?:hanya )?(?:dapat|boleh|mengerjakan) satu",
    ),
    ("antrian", "/or/queueing", r"antri|antre|antrian|kedatangan[^.]*(?:dilayani|pelayanan)|loket|kasir[^.]*melayani"),
    (
        "persediaan",
        "/or/inventory",
        r"biaya pesan|biaya pemesanan|biaya simpan|biaya penyimpanan|\beoq\b|persediaan optimal|jumlah pesanan ekonomis",
    ),
    (
        "proyek",
        "/or/pert-cpm",
        r"(?:aktivitas|kegiatan)[^.]*(?:pendahulu|didahului|setelah)|jalur kritis|critical path",
    ),
    ("Markov", "/or/markov-chains", r"transisi|markov|berpindah|beralih[^.]*peluang"),
    (
        "analisis keputusan",
        "/or/decision-analysis",
        r"payoff|keadaan alam|state of nature|alternatif keputusan|nilai harapan|evpi",
    ),
    ("teori permainan", "/or/game-theory", r"permainan[^.]*(?:pemain|strategi)|pemain [ab]\b"),
    ("jaringan", "/or/network", r"rute terpendek|lintasan terpendek|jarak[^.]*kota|aliran maksimum|pohon rentang"),
    ("knapsack", "/or/dynamic-programming?metode=knapsack", r"knapsack|ransel|daya angkut"),
    ("peramalan", "/or/forecasting", r"ramal|peramalan|forecast"),
    ("ANOVA", "/stats/anova", r"\banova\b|analisis varians"),
    ("regresi & korelasi", "/stats/regression", r"regresi|korelasi"),
    (
        "distribusi peluang",
        "/stats/distributions",
        r"berdistribusi|distribusi (?:normal|binomial|poisson|eksponensial)",
    ),
    (
        "statistik inferensial",
        "/stats/inferential",
        r"\buji\b|hipotesis|taraf nyata|signifikan|klaim|selang kepercayaan|interval kepercayaan",
    ),
]

IP_VARIANTS = {"branch-and-bound", "mip", "binary-formulation"}
# field yang punya nilai bawaan wajar / pelengkap — tidak dihitung sebagai “belum ditemukan”
OPTIONAL_KEYS = {
    "predict",
    "future_x",
    "max_copies",
    "what_if_rhs",
    "what_if_obj",
    "expected",
    "estimated_params",
    "initial",
    "steps",
    "deadline",
    "unit_cost",
    "lead_time",
    "classes",
    "horizon",
    "equal_var",
    "start",
    "theta_max",
    "direction",
    "current_time",
    "seed",
    "replications",
    "tol",
    "iterations",
}


def _example(module: str, vid: str) -> dict[str, Any]:
    if not (_SLUG.match(module) and _SLUG.match(vid)):
        return {}
    path = EXAMPLES_DIR / module / f"{vid}.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("input", {})


def _set(body: dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    cur = body
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def _get(body: dict[str, Any], key: str) -> Any:
    cur: Any = body
    for p in key.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _fmt_val(v: Any) -> str:
    if isinstance(v, float):
        return lp.fmt(v)
    if isinstance(v, list):
        if v and isinstance(v[0], list):
            return "matriks " + f"{len(v)}×{len(v[0])}"
        if v and isinstance(v[0], dict):
            return ", ".join(f"{g.get('name')} ({len(g.get('data', []))} data)" for g in v)
        s = ", ".join(_fmt_val(x) for x in v[:12])
        return s + (", …" if len(v) > 12 else "")
    if isinstance(v, dict):
        return ", ".join(
            f"{k} ({len(x)} data)" if isinstance(x, list) else f"{k} = {_fmt_val(x)}" for k, x in v.items()
        )
    if isinstance(v, str) and "\n" in v:
        return f"{len(v.splitlines())} baris"
    return str(v)


# ---------------------------------------------------------------- pengisian per varian


def _fill_variant(ctx: Ctx, module: str, v: dict[str, Any]) -> dict[str, Any]:
    vid = v["id"]
    fields = [f for f in v.get("fields", []) if not f.get("virtual")]
    keys = {f["key"] for f in fields}
    body: dict[str, Any] = {}
    formulation: str | None = None
    notes: list[str] = []
    seqs = ctx.seqs

    # ---- model LP / IP
    if "model" in keys and module == "or":
        res = lp.build_lp(ctx.raw, allow_int=vid in IP_VARIANTS)
        if res:
            body["model"] = res.model
            formulation = res.formulation
            notes += res.assumptions
            if "method" in keys and vid == "simplex":
                body["method"] = "auto"

    # ---- proyek
    if "activities" in keys:
        acts = fill.activities(ctx)
        need = {"cpm": 1, "pert": 3, "crashing": 4, "pert-cost": 1}.get(vid, 1)
        rows = []
        for code, preds, vals, name in acts:
            if len(vals) < need:
                rows = []
                break
            nums = " ".join(lp.fmt(x) for x in vals[:need]) if vid != "pert-cost" else " ".join(lp.fmt(x) for x in vals)
            rows.append(
                f"{code} | {', '.join(preds) or '-'} | {nums}" + (f" | {name}" if name and vid == "cpm" else "")
            )
        if len(rows) >= 2:
            body["activities"] = "\n".join(rows)

    # ---- jaringan
    graph_key = next((k for k in ("edges", "arcs") if k in keys), None)
    if graph_key:
        es = fill.edges(ctx)
        if len(es) >= 3:
            body[graph_key] = "\n".join(f"{a} {b} {' '.join(lp.fmt(x) for x in vals)}" for a, b, vals in es)
            nodes = list(dict.fromkeys([a for a, _, _ in es] + [b for _, b, _ in es]))
            src, dst = fill.endpoints(ctx, nodes)
            for k, val in (("source", src), ("target", dst), ("sink", dst)):
                if k in keys and val:
                    body[k] = val
            if "directed" in keys:
                body["directed"] = bool(re.search(r"satu arah|berarah|searah", ctx.lower))

    # ---- transportasi & penugasan
    if vid == "transportation":
        tr = fill.transport(ctx)
        if tr:
            body.update(tr)
            total_s, total_d = sum(tr["supply"]), sum(tr["demand"])
            if abs(total_s - total_d) > 1e-9:
                notes.append(
                    f"Total penawaran ({lp.fmt(total_s)}) ≠ total permintaan ({lp.fmt(total_d)}); solver menambah baris/kolom dummy."
                )
        if "method" in keys:
            body["method"] = (
                "nwc"
                if re.search(r"barat laut|north[- ]?west|nwc", ctx.lower)
                else "least_cost"
                if re.search(r"biaya terkecil|least cost|ongkos terkecil", ctx.lower)
                else "vam"
            )
    elif vid == "assignment":
        mt = fill.matrix_table(ctx)
        if mt:
            body["costs"], body["rows"], body["cols"] = (
                mt[0],
                mt[1] or [f"Baris {i + 1}" for i in range(len(mt[0]))],
                mt[2] or [f"Kolom {j + 1}" for j in range(len(mt[0][0]))],
            )
            body["maximize"] = bool(
                re.search(r"keuntungan|laba|maksim|nilai (?:tertinggi|terbesar)|produktivitas|skor", ctx.lower)
            )

    # ---- matriks umum (Markov, keputusan, permainan, chi-square, matriks)
    mat_key = next(
        (
            k
            for k in ("payoff", "matrix", "table", "rates", "a")
            if k in keys and next(f for f in fields if f["key"] == k)["type"] == "matrix"
        ),
        None,
    )
    if mat_key and mat_key not in body:
        mt = fill.matrix_table(ctx)
        if mt:
            mat, rl, cl = mt
            if mat_key in ("matrix",) and vid in ("markov-chain", "absorbing"):
                if any(x > 1 for r in mat for x in r):
                    mat = [[x / 100 for x in r] for r in mat]
                    notes.append("Peluang transisi dalam persen dikonversi ke pecahan.")
            body[mat_key] = mat
            for k, labels in (
                ("names", rl),
                ("row_labels", rl),
                ("col_labels", cl),
                ("row_names", rl),
                ("col_names", cl),
                ("actions", rl),
                ("states", cl),
            ):
                if k in keys and labels and all(labels):
                    body[k] = labels
    if "prior" in keys:
        for s in fill.sentences(ctx.text):
            if re.search(r"peluang|probabilitas|kemungkinan", s.text, re.I):
                ps = [n.fraction for n in fill.find_numbers(s.text)]
                if len(ps) >= 2 and abs(sum(ps) - 1) < 0.02:
                    body["prior"] = [round(p, 6) for p in ps]
                    break
    if "initial" in keys:
        for s in fill.sentences(ctx.text):
            if re.search(r"awal|saat ini|sekarang|mula-mula|pertama kali", s.text, re.I):
                ps = [n.fraction for n in fill.find_numbers(s.text)]
                if len(ps) >= 2 and abs(sum(ps) - 1) < 0.02:
                    body["initial"] = [round(p, 6) for p in ps]
                    break
    if "steps" in keys:
        m = re.search(
            r"(\d+)\s*(?:langkah|periode|hari|minggu|bulan|tahun|tahap|transisi)\s*(?:ke depan|kemudian|berikutnya|lagi|mendatang)",
            ctx.lower,
        )
        if m:
            body["steps"] = int(m.group(1))

    # ---- knapsack
    if vid in ("knapsack", "knapsack-meta"):
        it = fill.items(ctx)
        if it:
            names, w, val = it
            body["weights"], body["values"] = w, val
            if "names" in keys:
                body["names"] = names
        cap = fill.number_for("capacity", "integer" if vid == "knapsack" else "number", ctx, vid)
        if cap is not None:
            body["capacity"] = cap

    # ---- distribusi
    if vid == "distribution-calculator":
        d = fill.distribution(ctx)
        if d:
            body.update(d)

    # ---- persediaan
    if module == "or" and keys & {"setup", "holding", "holding_rate"} and vid != "transportation":
        inv = fill.inventory(ctx)
        for k in (
            "demand",
            "setup",
            "holding",
            "unit_cost",
            "lead_time",
            "shortage",
            "holding_rate",
            "production_rate",
        ):
            if k in keys and k in inv:
                body[k] = inv[k]
        notes += [n for n in ctx.notes if "dikonversi" in n or "Biaya simpan" in n]

    # ---- data statistik
    stat_seq_keys = [
        k for k in ("data", "x", "y") if k in keys and next(f for f in fields if f["key"] == k)["type"] == "numbers"
    ]
    if stat_seq_keys and module in ("stats", "or") and not body.get("model"):
        if keys >= {"x", "y"} and len(seqs) >= 2:
            body["x"], body["y"] = seqs[0].values, seqs[1].values
            if "x_name" in keys and seqs[0].label:
                body["x_name"] = seqs[0].label
            if "y_name" in keys and seqs[1].label:
                body["y_name"] = seqs[1].label
        elif "data" in keys and seqs:
            body["data"] = fill.longest_seq(ctx).values
        if vid == "wilcoxon" and len(seqs) == 1:
            body.pop("x", None)
    if "groups" in keys and len(seqs) >= 2:
        body["groups"] = [{"name": s.label or f"Kelompok {i + 1}", "data": s.values} for i, s in enumerate(seqs)]
    if "variables" in keys and len(seqs) >= 2:
        body["variables"] = {s.label or f"X{i + 1}": s.values for i, s in enumerate(seqs)}
    if "predictors" in keys and len(seqs) >= 3:
        yi = next(
            (
                i
                for i, s in enumerate(seqs)
                if re.search(r"\by\b|terikat|dependen|penjualan|hasil|nilai akhir", s.label, re.I)
            ),
            len(seqs) - 1,
        )
        body["y"] = seqs[yi].values
        body["y_name"] = seqs[yi].label or "Y"
        body["predictors"] = {s.label or f"X{i + 1}": s.values for i, s in enumerate(seqs) if i != yi}
    if vid == "chi-square-gof" and seqs:
        body["observed"] = seqs[0].values
        if len(seqs) >= 2:
            body["expected"] = seqs[1].values

    # ---- proporsi
    if vid == "proportion-test":
        pairs = fill.proportion_pairs(ctx)
        if pairs:
            body["x1"], body["n1"] = pairs[0]
            if len(pairs) >= 2:
                body["x2"], body["n2"] = pairs[1]
        p0 = fill.p0(ctx)
        if p0 is not None and len(pairs) < 2:
            body["p0"] = p0
    if vid == "confidence-interval":
        kind = (
            "proportion"
            if re.search(r"proporsi|persentase", ctx.lower)
            else "variance"
            if re.search(r"varians|ragam", ctx.lower)
            else "mean_z"
            if re.search(r"simpangan baku populasi|σ\s*=", ctx.lower)
            else "mean_t"
        )
        body["kind"] = kind
        if kind == "proportion":
            pairs = fill.proportion_pairs(ctx)
            if pairs:
                body["successes"], body["n"] = pairs[0]

    # ---- isian generik untuk field bertipe angka/alpha/alternative/text/select
    for f in fields:
        k, ftype = f["key"], f["type"]
        if _get(body, k) is not None:
            continue
        if ftype == "alpha":
            a = fill.alpha(ctx)
            if a is not None:
                _set(body, k, a)
        elif ftype == "alternative":
            alt = fill.alternative(ctx)
            if alt:
                _set(body, k, alt)
        elif ftype in ("number", "integer") and not (vid == "distribution-calculator"):
            val = fill.number_for(k, ftype, ctx, vid)
            if val is not None:
                _set(body, k, val)
        elif ftype == "select" and k == "method" and vid == "correlation":
            _set(body, k, "spearman" if re.search(r"spearman|peringkat|rank", ctx.lower) else "pearson")
        elif ftype == "text" and k in ("func", "objective"):
            m = re.search(r"(?:f\s*\(\s*x[^)]*\)|z)\s*=\s*([^\n;]+)", ctx.text, re.I)
            if m:
                _set(body, k, m.group(1).strip().rstrip("."))

    # data vs ringkasan (n, rata-rata, simpangan baku) adalah dua cara isi yang setara
    essential = set()
    example = _example(module, vid)
    for f in fields:
        top = f["key"].split(".")[0]
        if (
            f["type"] in ESSENTIAL_TYPES
            and top in example
            and f["key"] not in OPTIONAL_KEYS
            and "opsional" not in f.get("label", "").lower()
            and f["key"]
            not in (
                "x_name",
                "y_name",
                "names",
                "sources",
                "destinations",
                "rows",
                "cols",
                "row_labels",
                "col_labels",
                "row_names",
                "col_names",
                "actions",
                "states",
                "categories",
                "y_name",
            )
        ):
            essential.add(f["key"])
    if "data" in keys and "mean" in keys:
        if "data" in body:
            for k in ("n", "mean", "sd"):
                body.pop(k, None)
                essential.discard(k)
        else:
            essential.discard("data")
            essential |= {k for k in ("n", "mean") if k in keys}
            if vid != "z-test" and "sd" in keys:
                essential.add("sd")
    if vid == "proportion-test" and "x2" in body:
        essential.discard("p0")
    if vid == "distribution-calculator":
        essential = {"dist"} | ({"x"} if "x" in example else set())
        if "dist" in body:
            essential = {"dist", "params"} | ({"x"} if body.get("mode") not in ("between", "ppf") else set())

    filled = {k for k in essential if _get(body, k) is not None and _get(body, k) != {}}
    missing = [next((f["label"] for f in fields if f["key"] == k), k) for k in sorted(essential - filled)]
    hint = VARIANT_HINTS.get(vid)
    hits = len(re.findall(hint, ctx.lower)) if hint else 0
    ratio = len(filled) / len(essential) if essential else 0.0
    score = ratio * 10 + min(hits, 3) * 2.5 + (3 if essential and not missing else 0)
    return {
        "id": vid,
        "label": v.get("label", vid),
        "body": body,
        "formulation": formulation,
        "notes": notes,
        "missing": missing,
        "score": score,
        "complete": bool(essential) and not missing,
    }


def _domain(ctx: Ctx) -> tuple[str, str] | None:
    if lp.looks_like_lp(ctx.raw) and not re.search(r"angkut|pengiriman|transportasi|ditugaskan|penugasan", ctx.lower):
        res = lp.build_lp(ctx.raw)
        if res:
            return ("program linear", "/or/lp-graphical" if res.n_vars == 2 else "/or/simplex")
    for name, path, pat in DOMAINS:
        if re.search(pat, ctx.lower):
            return name, path
    if ctx.seqs:
        return ("statistik deskriptif", "/stats/descriptive")
    return None


def interpret(
    text: str, page_title: str, module: str, variants: list[dict[str, Any]], page_path: str = ""
) -> dict[str, Any]:
    text = (text or "").strip()
    if len(text) < 15:
        raise SolverError("Soal cerita terlalu pendek. Tempel teks soal lengkap beserta angkanya.")
    if len(text) > MAX_STORY_CHARS:
        raise SolverError(f"Soal cerita terlalu panjang (maksimal {MAX_STORY_CHARS} karakter).")
    if not variants:
        raise SolverError("Halaman ini tidak memiliki varian metode.")
    ctx = Ctx.of(text)
    results = [_fill_variant(ctx, module, v) for v in variants]
    best = max(results, key=lambda r: r["score"])  # max mengambil yang pertama bila seri → varian bawaan halaman

    lines: list[str] = []
    if best["formulation"]:
        lines.append(best["formulation"])
    else:
        filled_lines = [f"  {k}: {_fmt_val(v)}" for k, v in best["body"].items() if k not in ("method",)]
        if filled_lines:
            lines.append("Data yang dibaca dari soal:")
            lines += filled_lines
    if best["missing"]:
        lines.append("Belum ditemukan di soal (isi manual): " + ", ".join(best["missing"]) + ".")
    assumptions = list(dict.fromkeys(best["notes"]))
    if not best["body"].get("alpha") and any(
        f["type"] == "alpha" for v in variants if v["id"] == best["id"] for f in v.get("fields", [])
    ):
        assumptions.append("Taraf nyata tidak disebut; dipakai α = 0,05.")

    suggestion = None
    dom = _domain(ctx)
    if dom and not best["complete"]:
        base = dom[1].split("?")[0]
        if not page_path or not page_path.startswith(base):
            suggestion = {"title": dom[0], "path": dom[1]}
    if not best["body"]:
        msg = "Soal cerita belum dapat diterjemahkan untuk halaman ini."
        if suggestion:
            msg += f" Soal ini tampaknya masalah {suggestion['title']} — buka halaman {suggestion['path']}."
        else:
            msg += " Pastikan angka-angka soal tertulis jelas, atau isi formulir secara manual."
        raise SolverError(msg)
    return {
        "variant_id": best["id"],
        "input": best["body"],
        "formulation": "\n".join(lines),
        "assumptions": assumptions,
        "missing": best["missing"],
        "complete": best["complete"],
        "engine": "aturan",
        "suggestion": suggestion,
    }
