import type { VariantPageConfig } from '@/pages/VariantPage'
import { alpha, groups } from './common'
import { Theory } from './Theory'

export const anovaConfig: VariantPageConfig = {
  title: 'ANOVA & Tukey HSD',
  subtitle: 'Analisis varians satu arah dan dua arah, dilanjutkan uji perbandingan berganda Tukey.',
  variants: [
    {
      id: 'anova-one-way',
      label: 'ANOVA satu arah',
      endpoint: '/anova/one-way',
      fields: [groups, alpha],
      theory: (
        <Theory formulas={[String.raw`F = \frac{SSB/(k-1)}{SSW/(N-k)}`]}>
          <p>
            ANOVA satu arah menguji kesamaan rata-rata ≥ 3 kelompok sekaligus tanpa menaikkan galat tipe I seperti bila
            melakukan banyak uji-t. Asumsi: normalitas, varians homogen, pengamatan independen.
          </p>
        </Theory>
      ),
    },
    {
      id: 'anova-two-way',
      label: 'ANOVA dua arah',
      endpoint: '/anova/two-way',
      fields: [
        { key: 'factor_a', label: 'Nama faktor A', type: 'text', default: 'Faktor A' },
        { key: 'factor_b', label: 'Nama faktor B', type: 'text', default: 'Faktor B' },
        {
          key: 'cells',
          label: 'Data per sel',
          type: 'cells',
          required: true,
          placeholder: 'a1 | b1 | 12 14 13\na1 | b2 | 18 17 19\na2 | b1 | 15 16 14\na2 | b2 | 25 24 26',
          hint: 'Format per baris: level A | level B | nilai ulangan. Jumlah ulangan tiap sel harus sama. Satu nilai per sel = tanpa interaksi.',
        },
        alpha,
      ],
      theory: (
        <Theory formulas={[String.raw`SST = SS_A + SS_B + SS_{AB} + SSE`]}>
          <p>
            ANOVA dua arah menguji efek dua faktor sekaligus. Dengan ulangan (&gt; 1 nilai per sel) efek interaksi
            juga dapat diuji: interaksi terjadi bila pengaruh faktor A bergantung pada level faktor B (garis pada plot
            interaksi tidak sejajar).
          </p>
        </Theory>
      ),
    },
    {
      id: 'tukey-hsd',
      label: 'Uji lanjut Tukey HSD',
      endpoint: '/anova/tukey-hsd',
      fields: [groups, alpha],
      theory: (
        <Theory formulas={[String.raw`HSD = q_{\alpha;\,k,\,N-k}\sqrt{\frac{MSE}{2}\left(\frac{1}{n_i}+\frac{1}{n_j}\right)}`]}>
          <p>
            Setelah ANOVA menolak H₀, uji Tukey HSD menentukan pasangan kelompok mana yang berbeda nyata sambil menjaga
            galat tipe I keseluruhan tetap α. Untuk ukuran kelompok tak sama dipakai varian Tukey–Kramer.
          </p>
        </Theory>
      ),
    },
  ],
}
