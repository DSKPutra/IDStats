import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from './Theory'

export const descriptiveConfig: VariantPageConfig = {
  title: 'Statistik Deskriptif (Descriptive Statistics)',
  subtitle: 'Ukuran pemusatan, penyebaran, bentuk distribusi, tabel frekuensi, dan diagram pencar.',
  variants: [
    {
      id: 'descriptive',
      label: 'Ringkasan statistik',
      endpoint: '/descriptive/summary',
      fields: [{ key: 'data', label: 'Data sampel', type: 'numbers', required: true, placeholder: 'Contoh: 72, 85, 64, 90, 78 — atau tempel satu kolom dari Excel' }],
      theory: (
        <Theory formulas={[String.raw`\bar{x} = \frac{1}{n}\sum x_i,\qquad s^2 = \frac{1}{n-1}\sum_{i=1}^{n}(x_i-\bar{x})^2`]}>
          <p>
            <strong>Statistik deskriptif</strong> meringkas data menjadi ukuran <em>pemusatan</em> (mean, median, modus),
            <em> penyebaran</em> (varians, simpangan baku, IQR), dan <em>bentuk</em> distribusi (skewness, kurtosis).
          </p>
          <p>Varians sampel memakai pembagi n − 1 (koreksi Bessel) agar menjadi penduga tak bias bagi varians populasi.</p>
          <p>
            Skewness positif berarti ekor kanan lebih panjang; excess kurtosis positif berarti ekor lebih tebal daripada
            distribusi normal. Q-Q plot yang titik-titiknya mengikuti garis lurus mengindikasikan data mendekati normal.
          </p>
        </Theory>
      ),
    },
    {
      id: 'frequency-table',
      label: 'Tabel distribusi frekuensi',
      endpoint: '/descriptive/frequency-table',
      fields: [
        { key: 'data', label: 'Data sampel', type: 'numbers', required: true },
        { key: 'classes', label: 'Jumlah kelas (opsional)', type: 'integer', hint: 'Kosongkan untuk memakai aturan Sturges.' },
      ],
      theory: (
        <Theory formulas={[String.raw`k = 1 + 3{,}322\log_{10} n,\qquad c = \frac{x_{max} - x_{min}}{k}`]}>
          <p>
            Tabel distribusi frekuensi mengelompokkan data ke dalam <em>k</em> kelas dengan panjang <em>c</em>. Aturan
            Sturges memberi jumlah kelas awal yang wajar. Ogive (grafik frekuensi kumulatif) dipakai untuk membaca median
            dan kuartil secara grafis.
          </p>
        </Theory>
      ),
    },
    {
      id: 'scatter',
      label: 'Diagram pencar',
      endpoint: '/descriptive/scatter',
      fields: [
        { key: 'x_name', label: 'Nama variabel X', type: 'text', default: 'x' },
        { key: 'y_name', label: 'Nama variabel Y', type: 'text', default: 'y' },
        { key: 'x', label: 'Data X', type: 'numbers', required: true },
        { key: 'y', label: 'Data Y', type: 'numbers', required: true },
      ],
      theory: (
        <Theory>
          <p>
            Diagram pencar (scatter plot) menampilkan hubungan dua variabel numerik. Pola naik menunjukkan hubungan
            positif, pola turun hubungan negatif. Lanjutkan ke modul Korelasi & Regresi untuk mengujinya secara formal.
          </p>
        </Theory>
      ),
    },
  ],
}
