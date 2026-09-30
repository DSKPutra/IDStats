import type { RawValues } from '@/components/form/fields'
import type { VariantPageConfig } from '@/pages/VariantPage'
import { alpha, alternative, sampleFields, twoSamples } from './common'
import { Theory } from './Theory'

const hypothesisTheory = (
  <p>
    Langkah uji hipotesis: (1) rumuskan H₀ dan H₁, (2) tentukan α, (3) hitung statistik uji, (4) bandingkan dengan nilai
    kritis atau p-value, (5) ambil keputusan: tolak H₀ bila p-value &lt; α.
  </p>
)

export const inferentialConfig: VariantPageConfig = {
  title: 'Statistik Inferensial (Inferential Statistics)',
  subtitle: 'Interval kepercayaan dan uji hipotesis untuk rata-rata, proporsi, varians, dan tabel kontingensi.',
  variants: [
    {
      id: 'confidence-interval',
      label: 'Interval kepercayaan',
      endpoint: '/inferential/confidence-interval',
      fields: [
        {
          key: 'kind',
          label: 'Parameter',
          type: 'select',
          options: [
            { value: 'mean_t', label: 'Rata-rata (σ tidak diketahui, t)' },
            { value: 'mean_z', label: 'Rata-rata (σ diketahui, z)' },
            { value: 'proportion', label: 'Proporsi' },
            { value: 'variance', label: 'Varians' },
          ],
        },
        { key: 'confidence', label: 'Tingkat kepercayaan', type: 'number', default: '0.95' },
        { key: 'sigma', label: 'σ populasi', type: 'number', required: true, showIf: (r) => r.kind === 'mean_z' },
        { key: 'successes', label: 'Jumlah sukses x', type: 'integer', required: true, showIf: (r) => r.kind === 'proportion' },
        { key: 'n', label: 'Ukuran sampel n', type: 'integer', required: true, showIf: (r) => r.kind === 'proportion' },
        ...sampleFields({ sd: true }).map((f) => ({ ...f, showIf: (r: RawValues) => r.kind !== 'proportion' && (!f.showIf || f.showIf(r)) })),
      ],
      theory: (
        <Theory formulas={[String.raw`\bar{x} \pm t_{\alpha/2,\,n-1}\frac{s}{\sqrt{n}},\qquad \hat{p} \pm z_{\alpha/2}\sqrt{\frac{\hat{p}(1-\hat{p})}{n}}`]}>
          <p>
            Interval kepercayaan 95% berarti: bila pengambilan sampel diulang berkali-kali, sekitar 95% interval yang
            terbentuk akan memuat parameter populasi yang sebenarnya.
          </p>
        </Theory>
      ),
    },
    {
      id: 'z-test',
      label: 'Uji-z',
      endpoint: '/inferential/z-test',
      fields: [...sampleFields(), { key: 'mu0', label: 'μ₀ (nilai hipotesis)', type: 'number', required: true }, { key: 'sigma', label: 'σ populasi', type: 'number', required: true }, alternative, alpha],
      theory: <Theory formulas={[String.raw`z = \frac{\bar{x}-\mu_0}{\sigma/\sqrt{n}}`]}>{hypothesisTheory}<p>Uji-z dipakai bila simpangan baku populasi σ diketahui (atau n besar).</p></Theory>,
    },
    {
      id: 't-one-sample',
      label: 'Uji-t satu sampel',
      endpoint: '/inferential/t-test/one-sample',
      fields: [...sampleFields({ sd: true }), { key: 'mu0', label: 'μ₀ (nilai hipotesis)', type: 'number', required: true }, alternative, alpha],
      theory: <Theory formulas={[String.raw`t = \frac{\bar{x}-\mu_0}{s/\sqrt{n}},\quad df = n-1`]}>{hypothesisTheory}<p>Asumsi: data berasal dari populasi (mendekati) normal.</p></Theory>,
    },
    {
      id: 't-independent',
      label: 'Uji-t dua sampel independen',
      endpoint: '/inferential/t-test/independent',
      fields: [...twoSamples, { key: 'equal_var', label: 'Varians sama', type: 'boolean', default: 'true', placeholder: 'Asumsikan varians kedua populasi sama (pooled); hapus centang untuk uji Welch' }, alternative, alpha],
      theory: (
        <Theory formulas={[String.raw`t = \frac{\bar{x}_1-\bar{x}_2}{\sqrt{s_p^2\left(\frac{1}{n_1}+\frac{1}{n_2}\right)}}`]}>
          {hypothesisTheory}
          <p>Jika varians kedua kelompok berbeda jauh (cek dengan uji F), gunakan uji Welch.</p>
        </Theory>
      ),
    },
    {
      id: 't-paired',
      label: 'Uji-t berpasangan',
      endpoint: '/inferential/t-test/paired',
      fields: [
        { key: 'x', label: 'Pengukuran 1 (mis. sebelum)', type: 'numbers', required: true },
        { key: 'y', label: 'Pengukuran 2 (mis. sesudah)', type: 'numbers', required: true },
        alternative,
        alpha,
      ],
      theory: <Theory formulas={[String.raw`d_i = x_{1i}-x_{2i},\quad t = \frac{\bar{d}}{s_d/\sqrt{n}}`]}>{hypothesisTheory}<p>Dipakai bila setiap pengamatan pada kedua sampel berpasangan (subjek yang sama).</p></Theory>,
    },
    {
      id: 'proportion-test',
      label: 'Uji proporsi',
      endpoint: '/inferential/proportion-test',
      fields: [
        { key: 'mode', label: 'Jenis', type: 'select', virtual: true, options: [{ value: 'one', label: 'Satu proporsi' }, { value: 'two', label: 'Dua proporsi' }], infer: (b) => (b.x2 !== undefined ? 'two' : 'one') },
        { key: 'x1', label: 'Jumlah sukses x₁', type: 'integer', required: true },
        { key: 'n1', label: 'Ukuran sampel n₁', type: 'integer', required: true },
        { key: 'p0', label: 'p₀ (proporsi hipotesis)', type: 'number', required: true, showIf: (r) => r.mode === 'one' },
        { key: 'x2', label: 'Jumlah sukses x₂', type: 'integer', required: true, showIf: (r) => r.mode === 'two' },
        { key: 'n2', label: 'Ukuran sampel n₂', type: 'integer', required: true, showIf: (r) => r.mode === 'two' },
        alternative,
        alpha,
      ],
      theory: <Theory formulas={[String.raw`z = \frac{\hat{p}-p_0}{\sqrt{p_0(1-p_0)/n}}`]}>{hypothesisTheory}<p>Pendekatan normal layak bila np₀ ≥ 5 dan n(1−p₀) ≥ 5.</p></Theory>,
    },
    {
      id: 'chi-square-gof',
      label: 'Chi-square goodness of fit',
      endpoint: '/inferential/chi-square/goodness-of-fit',
      fields: [
        { key: 'categories', label: 'Nama kategori (opsional)', type: 'labels', placeholder: 'Senin, Selasa, Rabu' },
        { key: 'observed', label: 'Frekuensi observasi O', type: 'numbers', required: true },
        { key: 'expected', label: 'Frekuensi harapan E atau peluang (opsional)', type: 'numbers', hint: 'Kosong = semua kategori berpeluang sama. Boleh diisi peluang yang berjumlah 1.' },
        { key: 'estimated_params', label: 'Jumlah parameter yang diestimasi dari data', type: 'integer', default: '0' },
        alpha,
      ],
      theory: <Theory formulas={[String.raw`\chi^2 = \sum\frac{(O_i-E_i)^2}{E_i},\quad df = k-1-m`]}>{hypothesisTheory}<p>Menguji apakah frekuensi observasi sesuai dengan distribusi teoretis tertentu.</p></Theory>,
    },
    {
      id: 'chi-square-independence',
      label: 'Chi-square independensi',
      endpoint: '/inferential/chi-square/independence',
      fields: [
        { key: 'table', label: 'Tabel kontingensi', type: 'matrix', required: true, placeholder: '20 15 25\n30 25 10', hint: 'Satu baris per baris tabel; pisahkan kolom dengan spasi atau koma.' },
        { key: 'row_labels', label: 'Label baris (opsional)', type: 'labels', placeholder: 'Pria, Wanita' },
        { key: 'col_labels', label: 'Label kolom (opsional)', type: 'labels', placeholder: 'A, B, C' },
        alpha,
      ],
      theory: <Theory formulas={[String.raw`E_{ij} = \frac{R_i C_j}{N},\quad \chi^2 = \sum\sum\frac{(O_{ij}-E_{ij})^2}{E_{ij}},\quad df=(r-1)(c-1)`]}>{hypothesisTheory}<p>Menguji apakah dua variabel kategorik saling bebas.</p></Theory>,
    },
    {
      id: 'f-test',
      label: 'Uji F (dua varians)',
      endpoint: '/inferential/f-test',
      fields: [...twoSamples, alternative, alpha],
      theory: <Theory formulas={[String.raw`F = \frac{s_1^2}{s_2^2},\quad df = (n_1-1,\ n_2-1)`]}>{hypothesisTheory}<p>Sering dipakai sebelum uji-t independen untuk memeriksa asumsi varians sama.</p></Theory>,
    },
  ],
}
