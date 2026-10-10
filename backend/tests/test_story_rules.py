"""Penerjemah soal cerita berbasis aturan: soal → input → diselesaikan solver → jawaban buku/hitungan manual."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import EXAMPLES_DIR
from app.core.errors import SolverError
from app.main import app
from app.services.story_rules import interpret
from app.services.story_rules.lp import build_lp
from app.services.story_rules.text import find_numbers

PAGES = json.loads((Path(__file__).parent / "story_pages.json").read_text(encoding="utf-8"))
client = TestClient(app)


def run(page: str, text: str, path: str = "/x"):
    p = PAGES[page]
    out = interpret(text, p["title"], p["module"], p["variants"], path)
    endpoint = json.loads((EXAMPLES_DIR / p["module"] / f"{out['variant_id']}.json").read_text())["endpoint"]
    res = client.post(f"/api{endpoint}", json=out["input"])
    assert res.status_code == 200, res.text
    return out, res.json()


def test_angka_format_indonesia():
    vals = [n.value for n in find_numbers("Rp70.000, 0,05, 5%, 2,5 juta, 1.250,75 dan 3 ribu")]
    assert vals == [70000, 0.05, 5, 2_500_000, 1250.75, 3000]


LP_CASES = {
    "prosa": (
        "Sebuah perusahaan mebel memproduksi dua jenis produk, yaitu meja dan kursi. Setiap meja memerlukan 4 jam perakitan "
        "dan 2 jam pengecatan, sedangkan setiap kursi memerlukan 3 jam perakitan dan 1 jam pengecatan. Waktu perakitan yang "
        "tersedia 240 jam dan pengecatan 100 jam. Keuntungan meja Rp70.000 dan kursi Rp50.000. Tentukan jumlah produksi agar "
        "keuntungan maksimum.",
        "max Z = 70000x1 + 50000x2\n4x1 + 3x2 <= 240\n2x1 + x2 <= 100",
    ),
    "wyndor": (
        "PT Kaca Wyndor memproduksi pintu kaca (laba 3 ribu) dan jendela (laba 5 ribu). Pabrik 1 tersedia 4 jam, pintu butuh "
        "1 jam. Pabrik 2 tersedia 12 jam, jendela butuh 2 jam. Pabrik 3 tersedia 18 jam, pintu 3 jam dan jendela 2 jam. "
        "Tentukan produksi yang memaksimalkan laba.",
        "max Z = 3000x1 + 5000x2\nx1 <= 4\n2x2 <= 12\n3x1 + 2x2 <= 18",
    ),
    "diet": (
        "Seorang peternak mencampur dua jenis pakan, yaitu pakan A dan pakan B. Setiap kg pakan A mengandung 2 unit protein "
        "dan 3 unit lemak. Setiap kg pakan B mengandung 4 unit protein dan 1 unit lemak. Kebutuhan minimal protein 16 unit "
        "dan lemak 12 unit. Harga pakan A Rp5.000 per kg dan pakan B Rp4.000 per kg. Tentukan campuran dengan biaya minimum.",
        "min Z = 5000x1 + 4000x2\n2x1 + 4x2 >= 16\n3x1 + x2 >= 12",
    ),
    "eksplisit": (
        "Maksimumkan Z = 3x + 5y\ndengan kendala:\nx ≤ 4\n2y ≤ 12\n3x + 2y ≤ 18\nx, y ≥ 0",
        "max Z = 3x1 + 5x2\nx1 <= 4\n2x2 <= 12\n3x1 + 2x2 <= 18",
    ),
    "eksplisit-desimal": (
        "Minimumkan Z = 0,4x1 + 0,5x2 terhadap 0,3x1 + 0,1x2 ≤ 2,7; 0,5x1 + 0,5x2 = 6; 0,6x1 + 0,4x2 ≥ 6; x1, x2 ≥ 0",
        "min Z = 0.4x1 + 0.5x2\n0.3x1 + 0.1x2 <= 2.7\n0.5x1 + 0.5x2 = 6\n0.6x1 + 0.4x2 >= 6",
    ),
    "tabel": (
        "Produk\tMeja\tKursi\tKapasitas\nPerakitan\t4\t3\t240\nPengecatan\t2\t1\t100\nKeuntungan\t70000\t50000\nTentukan keuntungan maksimum.",
        "max Z = 70000x1 + 50000x2\n4x1 + 3x2 <= 240\n2x1 + x2 <= 100",
    ),
    "mesin-dan-permintaan": (
        "Perusahaan membuat produk A dan produk B. Produk A diproses di mesin I selama 2 jam dan mesin II selama 1 jam. "
        "Produk B diproses di mesin I selama 1 jam dan mesin II selama 3 jam. Mesin I beroperasi maksimal 40 jam dan mesin II "
        "maksimal 45 jam per minggu. Laba produk A Rp30.000 dan produk B Rp20.000 per unit. Permintaan produk A paling banyak "
        "15 unit. Berapa produksi agar laba maksimal?",
        "max Z = 30000x1 + 20000x2\n2x1 + x2 <= 40\nx1 + 3x2 <= 45\nx1 <= 15",
    ),
    "masing-masing": (
        "Toko kue membuat bolu dan brownies. Bolu dan brownies masing-masing membutuhkan 200 gram tepung dan 100 gram tepung. "
        "Bolu dan brownies masing-masing membutuhkan 50 gram gula dan 75 gram gula. Persediaan tepung 10.000 gram dan gula "
        "6.000 gram. Keuntungan bolu Rp4.000 dan brownies Rp5.000. Tentukan keuntungan maksimum.",
        "max Z = 4000x1 + 5000x2\n200x1 + 100x2 <= 10000\n50x1 + 75x2 <= 6000",
    ),
    "tiga-produk": (
        "Sebuah perusahaan memproduksi tiga jenis produk, yaitu A, B, dan C. Setiap unit A memerlukan 2 jam mesin dan 1 kg "
        "bahan baku, B memerlukan 3 jam mesin dan 2 kg bahan baku, C memerlukan 1 jam mesin dan 3 kg bahan baku. Waktu mesin "
        "tersedia 100 jam dan bahan baku 80 kg. Keuntungan A Rp4.000, B Rp5.000, C Rp3.000. Tentukan keuntungan maksimum.",
        "max Z = 4000x1 + 5000x2 + 3000x3\n2x1 + 3x2 + x3 <= 100\nx1 + 2x2 + 3x3 <= 80",
    ),
}


@pytest.mark.parametrize("name", list(LP_CASES))
def test_lp_model(name):
    text, model = LP_CASES[name]
    res = build_lp(text)
    assert res is not None and res.model == model


def test_lp_wyndor_diselesaikan_simpleks():
    out, res = run("Metode Simpleks", LP_CASES["wyndor"][0])
    assert out["complete"] and res["result"]["z"] == pytest.approx(36000)
    assert "x1 = jumlah pintu kaca" in out["formulation"]


def test_lp_diet_diselesaikan():
    _, res = run("Metode Simpleks", LP_CASES["diet"][0])
    # titik optimum perpotongan 2x1 + 4x2 = 16 dan 3x1 + x2 = 12 → (3,2; 2,4)
    assert res["result"]["z"] == pytest.approx(5000 * 3.2 + 4000 * 2.4)


def test_lp_grafik_dan_bilangan_bulat():
    out, _ = run("Metode Grafik", LP_CASES["prosa"][0])
    assert out["variant_id"] == "lp-graphical"
    out, _ = run("Pemrograman Bilangan", LP_CASES["prosa"][0] + " Jumlah produksi harus bilangan bulat.")
    assert out["variant_id"] == "mip" and "int x1, x2" in out["input"]["model"]


def test_transportasi_tabel():
    text = (
        "Biaya angkut per unit dari tiga gudang ke empat toko:\nGudang\tT1\tT2\tT3\tT4\tKapasitas\nG1\t8\t6\t10\t9\t35\n"
        "G2\t9\t12\t13\t7\t50\nG3\t14\t9\t16\t5\t40\nPermintaan\t45\t20\t30\t30\nTentukan biaya pengiriman minimum dengan metode VAM."
    )
    out, res = run("Transportasi", text)
    assert out["variant_id"] == "transportation" and out["input"]["demand"] == [45, 20, 30, 30]
    assert res["result"]["total_cost"] == pytest.approx(1020)


def test_penugasan():
    text = (
        "Empat pekerja akan ditugaskan pada empat pekerjaan. Waktu (jam):\nPekerja\tJ1\tJ2\tJ3\tJ4\nAndi\t10\t12\t9\t11\n"
        "Budi\t8\t11\t10\t12\nCici\t12\t9\t11\t10\nDodi\t11\t10\t12\t9\nTentukan penugasan dengan waktu total minimum."
    )
    out, res = run("Transportasi", text)
    assert out["variant_id"] == "assignment" and out["input"]["rows"] == ["Andi", "Budi", "Cici", "Dodi"]
    assert res["result"]["total"] == pytest.approx(9 + 8 + 9 + 9)


@pytest.mark.parametrize(
    ("text", "lam", "mu", "s"),
    [
        (
            "Pelanggan datang ke sebuah bank rata-rata 20 orang per jam. Seorang teller dapat melayani rata-rata 25 orang per jam.",
            20,
            25,
            1,
        ),
        (
            "Mobil tiba di tempat cuci rata-rata 12 mobil per jam. Waktu pelayanan rata-rata 4 menit per mobil dan terdapat 2 tempat cuci.",
            12,
            15,
            2,
        ),
    ],
)
def test_antrian(text, lam, mu, s):
    out, res = run("Teori Antrian", text)
    assert out["input"] == {"lam": lam, "mu": mu, "s": s}
    assert res["result"]["l"] == pytest.approx(lam / (mu - lam)) if s == 1 else res["result"]["l"] > 0


def test_eoq_dengan_persen_biaya_simpan():
    text = "Permintaan tahunan sebuah toko 8.000 unit. Biaya pemesanan Rp12.000 setiap kali pesan, harga per unit Rp10 dan biaya simpan 30% dari harga per unit per tahun. Hitung EOQ."
    out, res = run("Teori Persediaan", text)
    assert out["input"]["holding"] == pytest.approx(3)
    assert res["result"]["q"] == pytest.approx((2 * 8000 * 12000 / 3) ** 0.5)


def test_uji_t_satu_sampel():
    text = "Sebuah pabrik mengklaim rata-rata berat bersih kemasan 500 gram. Diambil sampel 10 kemasan dengan berat: 495, 502, 498, 490, 505, 497, 493, 499, 496, 494. Dengan taraf nyata 5%, apakah rata-rata berat kurang dari 500 gram?"
    out, _ = run("Statistik Inferensial", text)
    assert out["variant_id"] == "t-one-sample"
    assert out["input"]["mu0"] == 500 and out["input"]["alternative"] == "less" and out["input"]["alpha"] == 0.05


def test_uji_t_berpasangan():
    text = "Nilai 8 siswa sebelum pelatihan: 60, 65, 70, 55, 62, 68, 58, 64 dan sesudah pelatihan: 68, 70, 75, 60, 66, 72, 63, 70. Ujilah apakah pelatihan meningkatkan nilai dengan α = 0,05."
    out, _ = run("Statistik Inferensial", text)
    assert out["variant_id"] == "t-paired" and out["input"]["alternative"] == "greater"


def test_uji_z_ringkasan():
    text = "Sebuah perusahaan lampu mengklaim rata-rata umur lampu 1.000 jam dengan simpangan baku populasi 80 jam. Sampel 36 lampu menghasilkan rata-rata 972 jam. Uji dengan taraf nyata 5% apakah rata-rata umur lampu kurang dari 1.000 jam."
    out, _ = run("Statistik Inferensial", text)
    assert out["variant_id"] == "z-test"
    assert out["input"] == {"n": 36, "mean": 972, "mu0": 1000, "sigma": 80, "alternative": "less", "alpha": 0.05}


def test_uji_proporsi():
    text = "Dari 400 produk yang diperiksa, 28 di antaranya cacat. Perusahaan mengklaim persentase cacat tidak lebih dari 5%. Ujilah apakah persentase cacat lebih dari 5% dengan taraf nyata 5%."
    out, _ = run("Statistik Inferensial", text)
    assert (
        out["variant_id"] == "proportion-test"
        and out["input"]["x1"] == 28
        and out["input"]["n1"] == 400
        and out["input"]["p0"] == 0.05
    )


def test_anova_kelompok_berlabel():
    text = "Hasil panen (kuintal) tiga jenis pupuk:\nPupuk A: 23, 25, 21, 22, 24\nPupuk B: 30, 28, 29, 31, 27\nPupuk C: 22, 24, 23, 21, 25\nUji apakah terdapat perbedaan rata-rata hasil panen dengan α = 5%."
    out, _ = run("ANOVA", text)
    assert [g["name"] for g in out["input"]["groups"]] == ["Pupuk A", "Pupuk B", "Pupuk C"]


def test_regresi_sederhana():
    text = "Data biaya iklan (juta): 2, 3, 4, 4, 5, 6, 6, 7 dan penjualan (unit): 25, 31, 33, 36, 40, 44, 43, 50. Tentukan persamaan regresi linier sederhana."
    out, _ = run("Korelasi", text)
    assert (
        out["variant_id"] == "regression-simple"
        and out["input"]["x_name"] == "biaya iklan"
        and out["input"]["y_name"] == "penjualan"
    )


def test_distribusi_normal_dan_binomial():
    out, res = run(
        "Distribusi Probabilitas",
        "Waktu perakitan berdistribusi normal dengan rata-rata 30 menit dan simpangan baku 4 menit. Berapa peluang waktu perakitan lebih dari 36 menit?",
    )
    assert out["input"] == {"dist": "normal", "params": {"mu": 30, "sigma": 4}, "mode": "sf", "x": 36}
    out, _ = run(
        "Distribusi Probabilitas",
        "Peluang sebuah produk cacat 0,1. Jika diambil 10 produk, berapa peluang paling banyak 2 produk cacat?",
    )
    assert out["input"] == {"dist": "binomial", "params": {"n": 10, "p": 0.1}, "mode": "cdf", "x": 2}


def test_cpm_tabel_dan_prosa():
    out, res = run(
        "Manajemen Proyek",
        "Aktivitas | Pendahulu | Durasi\nA | - | 2\nB | A | 4\nC | A | 3\nD | B, C | 5\nE | D | 2\nTentukan jalur kritis.",
    )
    assert res["result"]["duration"] == 13
    text = "Kegiatan A membutuhkan 3 hari dan dapat langsung dimulai. Kegiatan B membutuhkan 4 hari setelah A selesai. Kegiatan C membutuhkan 2 hari setelah A. Kegiatan D membutuhkan 5 hari setelah B dan C selesai. Tentukan waktu penyelesaian proyek."
    out, res = run("Manajemen Proyek", text)
    assert (
        out["input"]["activities"] == "A | - | 3\nB | A | 4\nC | A | 2\nD | B, C | 5"
        and res["result"]["duration"] == 12
    )


def test_lintasan_terpendek():
    text = "Jarak antar kota (km):\nO A 2\nO B 5\nO C 4\nA B 2\nA D 7\nB C 1\nB D 4\nB E 3\nC E 4\nD E 1\nD T 5\nE T 7\nTentukan rute terpendek dari O ke T."
    out, res = run("Optimasi Jaringan", text)
    assert out["variant_id"] == "shortest-path" and res["result"]["distance"] == 13


def test_markov_keputusan_peramalan_knapsack():
    out, _ = run(
        "Rantai Markov",
        "Matriks peluang transisi cuaca:\n\tCerah\tHujan\nCerah\t0,8\t0,2\nHujan\t0,4\t0,6\nTentukan peluang steady state.",
    )
    assert out["variant_id"] == "markov-chain" and out["input"]["names"] == ["Cerah", "Hujan"]
    out, _ = run(
        "Analisis Keputusan",
        "Payoff (juta rupiah):\nAlternatif\tPasar baik\tPasar buruk\nPabrik besar\t200\t-180\nPabrik kecil\t100\t-20\nTidak membangun\t0\t0\nPeluang pasar baik 0,5 dan pasar buruk 0,5. Tentukan keputusan terbaik.",
    )
    assert out["input"]["prior"] == [0.5, 0.5] and out["input"]["states"] == ["Pasar baik", "Pasar buruk"]
    out, _ = run(
        "Peramalan",
        "Penjualan 12 bulan terakhir: 382, 409, 429, 439, 440, 416, 434, 422, 428, 435, 431, 447. Ramalkan 3 bulan ke depan dengan rata-rata bergerak 3 bulan.",
    )
    assert out["variant_id"] == "moving-average" and out["input"]["n"] == 3 and out["input"]["horizon"] == 3
    out, res = run(
        "Pemrograman Dinamis",
        "Sebuah tas berkapasitas 10 kg. Barang A berat 3 kg dengan nilai 4. Barang B berat 4 kg dengan nilai 5. Barang C berat 2 kg dengan nilai 3. Barang D berat 5 kg dengan nilai 7. Tentukan isi tas dengan nilai maksimum.",
    )
    assert out["variant_id"] == "knapsack" and out["input"]["capacity"] == 10


def test_deskriptif_dan_saran_halaman():
    out, _ = run(
        "Statistik Deskriptif",
        "Nilai ujian 10 mahasiswa: 78, 85, 62, 90, 71, 88, 95, 67, 80, 74. Hitung rata-rata, median dan simpangan baku.",
    )
    assert out["variant_id"] == "descriptive"
    p = PAGES["Statistik Deskriptif"]
    with pytest.raises(SolverError, match="/or/lp-graphical"):
        interpret(LP_CASES["prosa"][0], p["title"], p["module"], p["variants"], "/stats/descriptive")


def test_data_tidak_lengkap_dilaporkan():
    p = PAGES["Teori Antrian"]
    out = interpret(
        "Pelanggan datang rata-rata 20 orang per jam ke sebuah loket.", p["title"], p["module"], p["variants"]
    )
    assert not out["complete"] and any("μ" in m or "layan" in m.lower() for m in out["missing"])


def test_endpoint_tanpa_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = PAGES["Teori Antrian"]
    res = client.post(
        "/api/story/interpret",
        json={
            "text": "Pelanggan datang rata-rata 20 orang per jam. Seorang kasir melayani 25 orang per jam.",
            "module": p["module"],
            "variants": p["variants"],
            "page_path": "/or/queueing",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["engine"] == "aturan" and body["input"] == {"lam": 20, "mu": 25, "s": 1}
