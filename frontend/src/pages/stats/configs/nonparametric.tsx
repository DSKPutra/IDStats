import type { VariantPageConfig } from '@/pages/VariantPage'
import { alpha, alternative, groups, twoSamples } from './common'
import { Theory } from './Theory'

export const nonparametricConfig: VariantPageConfig = {
  title: 'Uji Non-parametrik (Nonparametric Tests)',
  subtitle: 'Alternatif uji-t dan ANOVA berbasis peringkat, tanpa asumsi normalitas.',
  variants: [
    {
      id: 'mann-whitney',
      label: 'Mann-Whitney U',
      endpoint: '/nonparametric/mann-whitney',
      fields: [...twoSamples, alternative, alpha],
      theory: (
        <Theory formulas={[String.raw`U_1 = R_1 - \frac{n_1(n_1+1)}{2}`]}>
          <p>Alternatif non-parametrik uji-t dua sampel independen: membandingkan peringkat gabungan kedua kelompok.</p>
        </Theory>
      ),
    },
    {
      id: 'wilcoxon',
      label: 'Wilcoxon signed-rank',
      endpoint: '/nonparametric/wilcoxon',
      fields: [
        { key: 'x', label: 'Pengukuran 1 (mis. sebelum)', type: 'numbers', required: true },
        { key: 'y', label: 'Pengukuran 2 (opsional)', type: 'numbers', hint: 'Kosongkan untuk uji satu sampel terhadap median μ₀.' },
        { key: 'mu0', label: 'Median hipotesis μ₀ (uji satu sampel)', type: 'number', default: '0', showIf: (r) => !(r.y as string).trim() },
        alternative,
        alpha,
      ],
      theory: (
        <Theory formulas={[String.raw`W^+ = \sum_{d_i>0} R(|d_i|)`]}>
          <p>Alternatif non-parametrik uji-t berpasangan: peringkat nilai mutlak selisih, lalu jumlahkan per tanda.</p>
        </Theory>
      ),
    },
    {
      id: 'kruskal-wallis',
      label: 'Kruskal-Wallis',
      endpoint: '/nonparametric/kruskal-wallis',
      fields: [groups, alpha],
      theory: (
        <Theory formulas={[String.raw`H = \frac{12}{N(N+1)}\sum\frac{R_i^2}{n_i} - 3(N+1)`]}>
          <p>Alternatif non-parametrik ANOVA satu arah untuk ≥ 3 kelompok independen.</p>
        </Theory>
      ),
    },
  ],
}
