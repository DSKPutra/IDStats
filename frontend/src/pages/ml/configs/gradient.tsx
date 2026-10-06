import type { FieldDef } from '@/components/form/fields'
import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from '@/pages/stats/configs/Theory'

const FUNCTIONS = [
  { value: 'rosenbrock', label: 'Rosenbrock (lembah sempit)' },
  { value: 'rastrigin', label: 'Rastrigin (banyak minimum lokal)' },
  { value: 'ackley', label: 'Ackley' },
  { value: 'beale', label: 'Beale' },
  { value: 'himmelblau', label: 'Himmelblau (4 minimum)' },
  { value: 'sphere', label: 'Sphere (konveks)' },
  { value: 'booth', label: 'Booth' },
  { value: 'styblinski-tang', label: 'Styblinski-Tang' },
]

const playgroundFields: FieldDef[] = [
  { key: 'function', label: 'Fungsi uji', type: 'select', options: FUNCTIONS },
  { key: 'iterations', label: 'Iterasi', type: 'integer', default: '300' },
  { key: 'start', label: 'Titik awal (opsional)', type: 'numbers', placeholder: '-1.5, 2', hint: 'Kosongkan untuk titik awal standar fungsi.' },
  { key: 'optimizers', label: 'Optimizer (maks. 8)', type: 'optimizers', required: true, minItems: 8, default: 'sgd lr=0.001\nadamw lr=0.05 weight_decay=0\nlion lr=0.01' },
]

const trainFields: FieldDef[] = [
  {
    key: 'dataset',
    label: 'Dataset',
    type: 'select',
    options: [
      { value: 'iris', label: 'Iris (150 × 4, 3 kelas)' },
      { value: 'breast_cancer', label: 'Breast Cancer (569 × 30, 2 kelas)' },
      { value: 'wine', label: 'Wine (178 × 13, 3 kelas)' },
      { value: 'digits', label: 'Digits — subset MNIST 8×8 (1797 × 64, 10 kelas)' },
      { value: 'csv', label: 'Dataset aktif (dari Manajemen Data)' },
    ],
  },
  { key: 'target', label: 'Kolom target (untuk dataset aktif)', type: 'text', showIf: (r) => r.dataset === 'csv', required: true },
  { key: 'model', label: 'Model', type: 'select', options: [{ value: 'logreg', label: 'Regresi logistik (softmax)' }, { value: 'mlp', label: 'MLP 1 lapisan tersembunyi (ReLU)' }] },
  { key: 'hidden', label: 'Neuron tersembunyi', type: 'integer', default: '16', showIf: (r) => r.model === 'mlp' },
  { key: 'epochs', label: 'Epoch', type: 'integer', default: '50' },
  { key: 'batch_size', label: 'Ukuran mini-batch', type: 'integer', default: '32' },
  { key: 'seed', label: 'Seed', type: 'integer', default: '0' },
  { key: 'optimizers', label: 'Optimizer (maks. 6)', type: 'optimizers', required: true, minItems: 6, default: 'sgd lr=0.1\nadamw lr=0.01' },
]

const theory = (
  <Theory formulas={[String.raw`m_t = \beta_1 m_{t-1} + (1-\beta_1)g_t,\quad v_t = \beta_2 v_{t-1} + (1-\beta_2)g_t^2,\quad \hat m_t = \frac{m_t}{1-\beta_1^t},\ \hat v_t = \frac{v_t}{1-\beta_2^t}`]}>
    <p>
      Liu et al. (2025) membagi optimizer berbasis gradien menjadi metode <strong>adaptif</strong> turunan Adam (AdamW, AdamP,
      Adai, NAdam, AMSGrad, RAdam, QHAdam, Adamax), metode <strong>layer-wise</strong> untuk batch besar (LAMB, NovoGrad),
      metode <strong>berbasis tanda</strong> (LION), dan <strong>pembungkus</strong> (Lookahead). Rumus pembaruan tiap optimizer
      ditampilkan saat dipilih dan di tab Langkah-langkah.
    </p>
    <p>
      Kelebihan metode adaptif: konvergen cepat dan tidak sensitif terhadap skala gradien; kekurangannya: generalisasi kadang
      lebih buruk daripada SGD + momentum dan memerlukan memori tambahan untuk momen. Semua optimizer di sini ditulis dari nol
      dengan NumPy; gradien fungsi uji dihitung secara numerik, sedangkan gradien model dihitung dengan backpropagation manual.
    </p>
  </Theory>
)

export const playgroundConfig: VariantPageConfig = {
  title: 'Playground Optimizer Gradien (Loss Surface)',
  subtitle: 'Animasi lintasan beberapa optimizer sekaligus pada permukaan loss 2D/3D: Rosenbrock, Rastrigin, Ackley, Beale, dan lainnya.',
  exampleModule: 'ml',
  variants: [
    { id: 'gradient-playground', label: 'Rosenbrock', endpoint: '/ml/playground', fields: playgroundFields, theory },
    { id: 'playground-rastrigin', label: 'Rastrigin', endpoint: '/ml/playground', fields: playgroundFields, theory },
  ],
}

const withDataset = (body: Record<string, unknown>, ctx: { dataset: { columns: string[]; rows: unknown[][] } | null }) => {
  if (body.dataset !== 'csv') return body
  if (!ctx.dataset) return 'Belum ada dataset aktif. Muat data di halaman Manajemen Data terlebih dahulu.'
  return { ...body, columns: ctx.dataset.columns, rows: ctx.dataset.rows }
}

export const trainingConfig: VariantPageConfig = {
  title: 'Perbandingan Optimizer pada Model Nyata',
  subtitle: 'Latih regresi logistik atau MLP pada Iris, Breast Cancer, Wine, Digits (MNIST 8×8), atau dataset Anda; bandingkan kurva loss & akurasi.',
  exampleModule: 'ml',
  variants: [
    { id: 'gradient-training', label: 'Regresi logistik', endpoint: '/ml/train', fields: trainFields, theory, prepareBody: withDataset },
    { id: 'training-mlp', label: 'MLP', endpoint: '/ml/train', fields: trainFields, theory, prepareBody: withDataset },
  ],
}
