import io

import pytest
from openpyxl import Workbook

from app.core.errors import SolverError
from app.solvers import data

COLS = ["nama", "nilai", "jam"]
ROWS = [["a", 70, 5], ["b", None, 6], ["c", 80, None], ["d", 75, 7], ["e", 300, 6], ["f", 72, 5]]


def test_read_csv_semicolon_and_decimal_comma():
    out = data.read_file(b"nama;nilai\na;72,5\nb;80\n", "x.csv").result
    assert out["columns"] == ["nama", "nilai"]
    assert out["rows"][0] == ["a", 72.5]


def test_read_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.append(["x", "y"])
    ws.append([1, 2])
    buf = io.BytesIO()
    wb.save(buf)
    assert data.read_file(buf.getvalue(), "d.xlsx").result["rows"] == [[1, 2]]


def test_read_rejects_unknown_format():
    with pytest.raises(SolverError):
        data.read_file(b"abc", "x.pdf")


def test_clean_mean_imputation_and_iqr_removal():
    out = data.clean(COLS, ROWS, missing="mean", outlier="iqr", outlier_action="remove").result
    nilai = [r[1] for r in out["rows"]]
    assert 300 not in nilai
    assert all(v is not None for r in out["rows"] for v in r)


def test_clean_drop_and_flag():
    out = data.clean(COLS, ROWS, missing="drop", outlier="zscore", z_threshold=1.5, outlier_action="flag").result
    assert out["n_rows"] == 4
    assert out["columns"][-1] == "outlier"


def test_transform_zscore_and_log_error():
    out = data.transform(["x"], [[1], [2], [3]], ["x"], "zscore").result
    assert [r[1] for r in out["rows"]] == pytest.approx([-1, 0, 1])
    with pytest.raises(SolverError):
        data.transform(["x"], [[0], [2]], ["x"], "log")


def test_upload_endpoint(client):
    res = client.post("/api/data/upload", files={"file": ("d.csv", b"a,b\n1,2\n3,4\n", "text/csv")})
    assert res.status_code == 200
    assert res.json()["result"]["n_rows"] == 2


def test_outliers_handled_before_imputation():
    """Nilai pengisi tidak boleh tertarik oleh outlier (300) yang dibuang."""
    out = data.clean(COLS, ROWS, missing="mean", outlier="iqr", outlier_action="remove").result
    filled = next(r for r in out["rows"] if r[0] == "b")[1]
    assert filled == pytest.approx((70 + 80 + 75 + 72) / 4)
