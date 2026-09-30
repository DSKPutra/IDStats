import type { VariantPageConfig } from '@/pages/VariantPage'
import { alpha } from './common'
import { Theory } from './Theory'

export const normalityConfig: VariantPageConfig = {
  title: 'Uji Normalitas (Normality Tests)',
  subtitle: 'Shapiro-Wilk dan Kolmogorov-Smirnov / Lilliefors, dengan Q-Q plot.',
  variants: [
    {
      id: 'shapiro-wilk',
      label: 'Shapiro-Wilk',
      endpoint: '/normality/shapiro-wilk',
      fields: [{ key: 'data', label: 'Data sampel', type: 'numbers', required: true }, alpha],
      theory: (
        <Theory>
          <p>
            Shapiro-Wilk adalah uji normalitas paling kuat untuk sampel kecil hingga sedang. H₀: data berdistribusi
            normal — sehingga p-value ≥ α berarti asumsi normalitas <em>tidak ditolak</em>.
          </p>
        </Theory>
      ),
    },
    {
      id: 'kolmogorov-smirnov',
      label: 'Kolmogorov-Smirnov',
      endpoint: '/normality/kolmogorov-smirnov',
      fields: [
        { key: 'data', label: 'Data sampel', type: 'numbers', required: true },
        { key: 'mean', label: 'μ (opsional)', type: 'number', hint: 'Kosongkan μ dan σ untuk mengestimasi dari sampel (koreksi Lilliefors).' },
        { key: 'sd', label: 'σ (opsional)', type: 'number' },
        alpha,
      ],
      theory: (
        <Theory formulas={[String.raw`D = \max_x |F_n(x) - F_0(x)|`]}>
          <p>
            Uji KS membandingkan CDF empiris dengan CDF normal. Bila μ dan σ diestimasi dari data, tabel KS biasa terlalu
            konservatif, sehingga dipakai koreksi Lilliefors.
          </p>
        </Theory>
      ),
    },
  ],
}
