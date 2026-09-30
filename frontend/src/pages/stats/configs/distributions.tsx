import type { FieldDef, RawValues } from '@/components/form/fields'
import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from './Theory'

const dist = (...ids: string[]) => (r: RawValues) => ids.includes(r.dist as string)
const mode = (...ms: string[]) => (r: RawValues) => ms.includes(r.mode as string)

const distributionFields: FieldDef[] = [
  {
    key: 'dist',
    label: 'Distribusi',
    type: 'select',
    options: [
      { value: 'normal', label: 'Normal' },
      { value: 'binomial', label: 'Binomial' },
      { value: 'poisson', label: 'Poisson' },
      { value: 'exponential', label: 'Eksponensial' },
      { value: 'uniform', label: 'Seragam (Uniform)' },
      { value: 't', label: 't-Student' },
      { value: 'chi2', label: 'Chi-square (χ²)' },
      { value: 'f', label: 'F' },
      { value: 'gamma', label: 'Erlang / Gamma' },
    ],
  },
  {
    key: 'mode',
    label: 'Yang dihitung',
    type: 'select',
    options: [
      { value: 'cdf', label: 'P(X ≤ x) — CDF' },
      { value: 'sf', label: 'P(X > x) — ekor kanan' },
      { value: 'between', label: 'P(a ≤ X ≤ b)' },
      { value: 'pdf', label: 'P(X = x) / f(x) — PMF/PDF' },
      { value: 'ppf', label: 'Invers: x bila P(X ≤ x) = p' },
    ],
  },
  { key: 'params.mu', label: 'μ (rata-rata)', type: 'number', default: '0', required: true, showIf: dist('normal') },
  { key: 'params.sigma', label: 'σ (simpangan baku)', type: 'number', default: '1', required: true, showIf: dist('normal') },
  { key: 'params.n', label: 'n (jumlah percobaan)', type: 'integer', default: '10', required: true, showIf: dist('binomial') },
  { key: 'params.p', label: 'p (peluang sukses)', type: 'number', default: '0.5', required: true, showIf: dist('binomial') },
  { key: 'params.lam', label: 'λ (laju / rata-rata)', type: 'number', default: '2', required: true, showIf: dist('poisson', 'exponential', 'gamma') },
  { key: 'params.k', label: 'k (bentuk; bulat = Erlang)', type: 'number', default: '2', required: true, showIf: dist('gamma') },
  { key: 'params.a', label: 'a (batas bawah)', type: 'number', default: '0', required: true, showIf: dist('uniform') },
  { key: 'params.b', label: 'b (batas atas)', type: 'number', default: '1', required: true, showIf: dist('uniform') },
  { key: 'params.df', label: 'Derajat bebas', type: 'number', default: '10', required: true, showIf: dist('t', 'chi2') },
  { key: 'params.df1', label: 'df₁ (pembilang)', type: 'number', default: '5', required: true, showIf: dist('f') },
  { key: 'params.df2', label: 'df₂ (penyebut)', type: 'number', default: '10', required: true, showIf: dist('f') },
  { key: 'x', label: 'x', type: 'number', required: true, showIf: mode('cdf', 'sf', 'pdf') },
  { key: 'a', label: 'a (batas bawah)', type: 'number', required: true, showIf: mode('between') },
  { key: 'b', label: 'b (batas atas)', type: 'number', required: true, showIf: mode('between') },
  { key: 'p', label: 'Peluang p', type: 'number', required: true, showIf: mode('ppf') },
]

export const distributionsConfig: VariantPageConfig = {
  title: 'Distribusi Probabilitas (Probability Distributions)',
  subtitle: 'Kalkulator PMF/PDF, CDF, dan invers untuk distribusi diskrit & kontinu, plus tabel statistik (Appendix 5).',
  variants: [
    {
      id: 'distribution-calculator',
      label: 'Kalkulator distribusi',
      endpoint: '/distributions/compute',
      fields: distributionFields,
      theory: (
        <Theory formulas={[String.raw`F(x) = P(X \le x),\qquad P(a \le X \le b) = F(b) - F(a^-)`]}>
          <p>
            Distribusi <strong>diskrit</strong> (Binomial, Poisson) memiliki fungsi massa peluang P(X = x). Distribusi
            <strong> kontinu</strong> memiliki fungsi kepadatan f(x); untuk variabel kontinu P(X = x) = 0 sehingga peluang
            dihitung sebagai luas di bawah kurva.
          </p>
          <p>
            Eksponensial dan Erlang dipakai pada teori antrian (Bab 17): waktu antarkedatangan pada proses Poisson
            berdistribusi eksponensial, dan jumlah k fase eksponensial berdistribusi Erlang.
          </p>
        </Theory>
      ),
    },
    {
      id: 'distribution-table',
      label: 'Tabel statistik',
      endpoint: '/distributions/table',
      fields: [
        {
          key: 'kind',
          label: 'Tabel',
          type: 'select',
          options: [
            { value: 'z', label: 'Normal baku Φ(z)' },
            { value: 't', label: 'Nilai kritis t' },
            { value: 'chi2', label: 'Nilai kritis χ²' },
            { value: 'f', label: 'Nilai kritis F' },
          ],
        },
        { key: 'alpha', label: 'α (untuk tabel F)', type: 'alpha', showIf: (r) => r.kind === 'f' },
      ],
      theory: (
        <Theory>
          <p>
            Tabel statistik berisi nilai kuantil yang biasa dipakai untuk uji hipotesis secara manual. Nilai di sini
            dihitung langsung sehingga sama dengan tabel di Appendix 5 buku Hillier &amp; Lieberman.
          </p>
        </Theory>
      ),
    },
  ],
}
