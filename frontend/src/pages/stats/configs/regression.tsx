import type { VariantPageConfig } from '@/pages/VariantPage'
import { alpha } from './common'
import { Theory } from './Theory'

export const regressionConfig: VariantPageConfig = {
  title: 'Korelasi & Regresi (Correlation & Regression)',
  subtitle: 'Korelasi Pearson/Spearman, regresi linier sederhana & berganda, prediksi, dan uji asumsi klasik.',
  variants: [
    {
      id: 'correlation',
      label: 'Korelasi',
      endpoint: '/regression/correlation',
      fields: [
        { key: 'method', label: 'Metode', type: 'select', options: [{ value: 'pearson', label: 'Pearson (linier)' }, { value: 'spearman', label: 'Spearman (peringkat)' }] },
        alpha,
        { key: 'variables', label: 'Variabel', type: 'variables', itemLabel: 'Variabel', minItems: 2, hint: 'Dua variabel → uji detail; lebih dari dua → matriks korelasi.' },
      ],
      theory: (
        <Theory formulas={[String.raw`r = \frac{\sum(x-\bar{x})(y-\bar{y})}{\sqrt{\sum(x-\bar{x})^2\sum(y-\bar{y})^2}},\qquad t = r\sqrt{\frac{n-2}{1-r^2}}`]}>
          <p>
            Korelasi Pearson mengukur kekuatan hubungan <em>linier</em>; Spearman memakai peringkat sehingga cocok untuk
            hubungan monoton dan data ordinal atau ber-outlier. Korelasi tidak sama dengan sebab-akibat.
          </p>
        </Theory>
      ),
    },
    {
      id: 'regression-simple',
      label: 'Regresi linier sederhana',
      endpoint: '/regression/simple',
      fields: [
        { key: 'x_name', label: 'Nama variabel X', type: 'text', default: 'x' },
        { key: 'y_name', label: 'Nama variabel Y', type: 'text', default: 'y' },
        { key: 'x', label: 'Data X (variabel bebas)', type: 'numbers', required: true },
        { key: 'y', label: 'Data Y (variabel terikat)', type: 'numbers', required: true },
        { key: 'predict', label: 'Prediksi untuk nilai X (opsional)', type: 'numbers', placeholder: 'Contoh: 10, 12' },
        alpha,
      ],
      theory: (
        <Theory formulas={[String.raw`\hat{y} = b_0 + b_1x,\quad b_1 = \frac{S_{xy}}{S_{xx}},\quad b_0 = \bar{y} - b_1\bar{x}`]}>
          <p>
            Metode kuadrat terkecil memilih garis yang meminimumkan jumlah kuadrat residual. R² menunjukkan proporsi
            variasi Y yang dijelaskan X. Regresi linier kausal juga dipakai untuk peramalan (Bab 20).
          </p>
        </Theory>
      ),
    },
    {
      id: 'regression-multiple',
      label: 'Regresi linier berganda',
      endpoint: '/regression/multiple',
      fields: [
        { key: 'y_name', label: 'Nama variabel Y', type: 'text', default: 'y' },
        { key: 'y', label: 'Data Y (variabel terikat)', type: 'numbers', required: true },
        { key: 'predictors', label: 'Variabel bebas X', type: 'variables', itemLabel: 'X', minItems: 1 },
        { key: 'predict', label: 'Prediksi (opsional)', type: 'matrix', placeholder: '10 5\n12 4', hint: 'Satu baris per prediksi, nilai X sesuai urutan variabel bebas.' },
        alpha,
      ],
      theory: (
        <Theory formulas={[String.raw`\mathbf{b} = (\mathbf{X}^\top\mathbf{X})^{-1}\mathbf{X}^\top\mathbf{y}`]}>
          <p>
            Regresi berganda memodelkan Y dengan beberapa variabel bebas. Uji F menguji model secara simultan, uji t
            menguji tiap koefisien (parsial). Gunakan R² disesuaikan untuk membandingkan model dengan jumlah variabel
            berbeda.
          </p>
        </Theory>
      ),
    },
    {
      id: 'regression-assumptions',
      label: 'Uji asumsi klasik',
      endpoint: '/regression/assumptions',
      fields: [
        { key: 'y_name', label: 'Nama variabel Y', type: 'text', default: 'y' },
        { key: 'y', label: 'Data Y', type: 'numbers', required: true },
        { key: 'predictors', label: 'Variabel bebas X', type: 'variables', itemLabel: 'X', minItems: 1 },
        alpha,
      ],
      theory: (
        <Theory formulas={[String.raw`VIF_j = \frac{1}{1-R_j^2},\qquad DW = \frac{\sum (e_t-e_{t-1})^2}{\sum e_t^2}`]}>
          <p>
            Asumsi klasik regresi OLS: residual berdistribusi normal (Shapiro-Wilk), varians residual konstan /
            homoskedastis (Breusch-Pagan), tidak ada autokorelasi (Durbin-Watson), dan tidak ada multikolinearitas
            (VIF &lt; 10).
          </p>
        </Theory>
      ),
    },
  ],
}
