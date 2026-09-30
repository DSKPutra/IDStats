"""Manajemen data: baca CSV/XLSX, pembersihan (missing value, outlier), dan transformasi."""

import io
from typing import Any

import numpy as np
import pandas as pd

from app.core.errors import SolverError
from app.schemas.common import NamedTable, SolverResponse, Step, Table
from app.solvers._base import fmt, summary_items

MAX_ROWS = 10_000
MAX_BYTES = 5 * 1024 * 1024


def _to_json_rows(df: pd.DataFrame) -> list[list[Any]]:
    out = df.astype(object).where(pd.notna(df), None)
    return [[(v.item() if isinstance(v, np.generic) else v) for v in row] for row in out.itertuples(index=False)]


def _frame(columns: list[str], rows: list[list[Any]]) -> pd.DataFrame:
    if not columns:
        raise SolverError("Dataset belum memiliki kolom.")
    if len(set(columns)) != len(columns):
        raise SolverError("Nama kolom harus unik.")
    if any(len(r) != len(columns) for r in rows):
        raise SolverError("Setiap baris harus memiliki jumlah sel yang sama dengan jumlah kolom.")
    df = pd.DataFrame(rows, columns=columns)
    df = df.replace({"": None})
    for c in df.columns:
        converted = pd.to_numeric(df[c], errors="coerce")
        if converted.notna().sum() == df[c].notna().sum():
            df[c] = converted
    return df


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _profile(df: pd.DataFrame) -> NamedTable:
    rows = []
    for c in df.columns:
        numeric = pd.api.types.is_numeric_dtype(df[c])
        rows.append(
            [
                c,
                "Numerik" if numeric else "Teks/kategori",
                int(df[c].notna().sum()),
                int(df[c].isna().sum()),
                float(df[c].mean()) if numeric and df[c].notna().any() else None,
            ]
        )
    return NamedTable(title="Profil kolom", columns=["Kolom", "Tipe", "Terisi", "Kosong", "Rata-rata"], rows=rows)


def _dataset_response(
    df: pd.DataFrame, steps: list[Step], warnings: list[str], extra: dict | None = None
) -> SolverResponse:
    return SolverResponse(
        result={"columns": list(map(str, df.columns)), "rows": _to_json_rows(df), "n_rows": len(df), **(extra or {})},
        steps=steps,
        tables=[_profile(df)],
        summary=summary_items(
            [("Jumlah baris", len(df)), ("Jumlah kolom", df.shape[1]), ("Kolom numerik", len(_numeric_columns(df)))]
        ),
        warnings=warnings,
    )


def read_file(content: bytes, filename: str) -> SolverResponse:
    if len(content) > MAX_BYTES:
        raise SolverError("Ukuran file maksimal 5 MB.")
    if not content:
        raise SolverError("File kosong.")
    name = filename.lower()
    try:
        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        elif name.endswith((".csv", ".txt", ".tsv")):
            text = content.decode("utf-8-sig", errors="replace")
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
        else:
            raise SolverError("Format file harus CSV atau XLSX.")
    except SolverError:
        raise
    except Exception as exc:  # noqa: BLE001 - pesan ramah untuk file rusak/aneh
        raise SolverError(f"File tidak dapat dibaca: {exc}") from exc
    warnings = []
    if len(df) > MAX_ROWS:
        warnings.append(f"File berisi {len(df)} baris; hanya {MAX_ROWS} baris pertama yang dimuat.")
        df = df.head(MAX_ROWS)
    df.columns = [str(c).strip() or f"Kolom{i + 1}" for i, c in enumerate(df.columns)]
    # Excel/CSV lokal Indonesia sering memakai koma desimal ("72,5").
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            s = df[c].astype(str).str.strip().str.replace(",", ".", regex=False)
            converted = pd.to_numeric(s.where(df[c].notna()), errors="coerce")
            if df[c].notna().sum() and converted.notna().sum() == df[c].notna().sum():
                df[c] = converted
    steps = [
        Step(
            title="Baca file",
            explanation=f"File “{filename}” dibaca: {len(df)} baris × {df.shape[1]} kolom. Pemisah kolom dideteksi otomatis.",
        )
    ]
    return _dataset_response(df, steps, warnings)


def clean(
    columns: list[str],
    rows: list[list[Any]],
    missing: str = "none",
    outlier: str = "none",
    outlier_action: str = "flag",
    iqr_k: float = 1.5,
    z_threshold: float = 3.0,
    target_columns: list[str] | None = None,
) -> SolverResponse:
    df = _frame(columns, rows)
    numeric = _numeric_columns(df)
    targets = [c for c in (target_columns or numeric) if c in df.columns]
    non_numeric = [c for c in targets if c not in numeric]
    if non_numeric:
        raise SolverError(f"Kolom berikut bukan numerik: {', '.join(non_numeric)}.")
    steps: list[Step] = []
    warnings: list[str] = []
    report: list[list[Any]] = []

    if outlier != "none":
        if outlier not in ("iqr", "zscore"):
            raise SolverError("Metode outlier harus 'iqr' atau 'zscore'.")
        if outlier_action not in ("flag", "remove", "winsorize"):
            raise SolverError("Tindakan outlier harus 'flag', 'remove', atau 'winsorize'.")
        mask_any = pd.Series(False, index=df.index)
        for c in targets:
            col = df[c]
            if outlier == "iqr":
                q1, q3 = col.quantile(0.25), col.quantile(0.75)
                lo, hi = q1 - iqr_k * (q3 - q1), q3 + iqr_k * (q3 - q1)
                rule = rf"[Q_1 - {fmt(iqr_k)}\,IQR,\ Q_3 + {fmt(iqr_k)}\,IQR]"
            else:
                mu, sd = col.mean(), col.std(ddof=1)
                lo, hi = mu - z_threshold * sd, mu + z_threshold * sd
                rule = rf"[\bar{{x}} - {fmt(z_threshold)}s,\ \bar{{x}} + {fmt(z_threshold)}s]"
            mask = (col < lo) | (col > hi)
            report.append([c, float(lo), float(hi), int(mask.sum())])
            if outlier_action == "winsorize":
                df[c] = col.clip(lo, hi)
            mask_any |= mask.fillna(False)
        steps.append(
            Step(
                title="Deteksi outlier",
                explanation="Data di luar batas dianggap outlier. Batas dihitung dari nilai yang terisi, sebelum imputasi.",
                latex=rf"\text{{Batas wajar: }} {rule}",
                table=Table(columns=["Kolom", "Batas bawah", "Batas atas", "Jumlah outlier"], rows=report),
            )
        )
        n_out = int(mask_any.sum())
        if outlier_action == "remove":
            df = df[~mask_any].reset_index(drop=True)
            steps.append(Step(title="Hapus outlier", explanation=f"{n_out} baris yang mengandung outlier dihapus."))
        elif outlier_action == "winsorize":
            steps.append(Step(title="Winsorisasi", explanation="Nilai outlier dipotong ke batas bawah/atas terdekat."))
        else:
            df["outlier"] = mask_any.values
            steps.append(Step(title="Tandai outlier", explanation=f"Kolom baru “outlier” = True pada {n_out} baris."))
    # Imputasi setelah penanganan outlier agar nilai pengisi tidak tertarik oleh outlier.
    before = len(df)
    if missing == "drop":
        df = df.dropna(subset=targets).reset_index(drop=True)
        steps.append(
            Step(
                title="Hapus baris dengan nilai kosong",
                explanation=f"{before - len(df)} baris dihapus (listwise deletion).",
            )
        )
    elif missing in ("mean", "median", "mode"):
        fills = []
        for c in targets:
            n_missing = int(df[c].isna().sum())
            if not n_missing:
                continue
            if df[c].notna().sum() == 0:
                raise SolverError(f"Kolom {c} seluruhnya kosong sehingga tidak dapat diimputasi.")
            value = {"mean": df[c].mean(), "median": df[c].median(), "mode": df[c].mode().iloc[0]}[missing]
            df[c] = df[c].fillna(value)
            fills.append([c, n_missing, float(value)])
        label = {"mean": "rata-rata", "median": "median", "mode": "modus"}[missing]
        steps.append(
            Step(
                title=f"Imputasi nilai kosong dengan {label}",
                explanation="Tidak ada nilai kosong pada kolom terpilih."
                if not fills
                else f"Nilai kosong diganti {label} kolomnya.",
                table=Table(columns=["Kolom", "Jumlah diisi", "Nilai pengisi"], rows=fills) if fills else None,
            )
        )
    elif missing != "none":
        raise SolverError("Metode missing value tidak dikenal.")

    if not steps:
        warnings.append("Tidak ada operasi pembersihan yang dipilih.")
    return _dataset_response(df, steps, warnings, {"outliers": report})


def transform(columns: list[str], rows: list[list[Any]], targets: list[str], method: str) -> SolverResponse:
    df = _frame(columns, rows)
    if not targets:
        raise SolverError("Pilih minimal satu kolom untuk ditransformasi.")
    numeric = _numeric_columns(df)
    formulas = {
        "zscore": (r"z = \frac{x - \bar{x}}{s}", "z"),
        "minmax": (r"x' = \frac{x - x_{min}}{x_{max} - x_{min}}", "minmax"),
        "log": (r"x' = \ln x", "ln"),
        "log10": (r"x' = \log_{10} x", "log10"),
        "sqrt": (r"x' = \sqrt{x}", "sqrt"),
    }
    if method not in formulas:
        raise SolverError("Metode transformasi tidak dikenal.")
    formula, suffix = formulas[method]
    info = []
    for c in targets:
        if c not in numeric:
            raise SolverError(f"Kolom {c} bukan numerik.")
        x = df[c]
        if method == "zscore":
            sd = x.std(ddof=1)
            if not sd:
                raise SolverError(f"Kolom {c} konstan (s = 0).")
            new = (x - x.mean()) / sd
            info.append([c, f"x̄ = {fmt(float(x.mean()))}, s = {fmt(float(sd))}"])
        elif method == "minmax":
            rng = x.max() - x.min()
            if not rng:
                raise SolverError(f"Kolom {c} konstan (max = min).")
            new = (x - x.min()) / rng
            info.append([c, f"min = {fmt(float(x.min()))}, max = {fmt(float(x.max()))}"])
        elif method in ("log", "log10"):
            if (x <= 0).any():
                raise SolverError(f"Kolom {c} memuat nilai ≤ 0; logaritma hanya untuk nilai positif.")
            new = np.log(x) if method == "log" else np.log10(x)
            info.append([c, "semua nilai positif"])
        else:
            if (x < 0).any():
                raise SolverError(f"Kolom {c} memuat nilai negatif; akar kuadrat hanya untuk nilai ≥ 0.")
            new = np.sqrt(x)
            info.append([c, "semua nilai ≥ 0"])
        df[f"{c}_{suffix}"] = new
    steps = [
        Step(
            title="Terapkan transformasi",
            explanation="Kolom hasil ditambahkan di sebelah kanan dengan akhiran _" + suffix + ".",
            latex=formula,
            table=Table(columns=["Kolom", "Parameter"], rows=info),
        )
    ]
    return _dataset_response(df, steps, [])
