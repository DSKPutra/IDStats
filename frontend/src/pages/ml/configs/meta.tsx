import type { FieldDef } from '@/components/form/fields'
import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from '@/pages/stats/configs/Theory'

const ALGOS = [
  { value: 'noa', label: 'NOA' },
  { value: 'hho', label: 'HHO' },
  { value: 'avoa', label: 'AVOA' },
  { value: 'edo', label: 'EDO' },
  { value: 'iaro', label: 'IARO' },
  { value: 'cmaes', label: 'CMA-ES' },
  { value: 'lmma', label: 'LM-MA' },
  { value: 'aoa', label: 'AOA' },
  { value: 'pso', label: 'PSO' },
  { value: 'ga', label: 'GA' },
  { value: 'de', label: 'DE' },
  { value: 'sa', label: 'SA' },
]
const FUNCS_2D = [
  { value: 'himmelblau', label: 'Himmelblau' },
  { value: 'rastrigin', label: 'Rastrigin' },
  { value: 'ackley', label: 'Ackley' },
  { value: 'rosenbrock', label: 'Rosenbrock' },
  { value: 'beale', label: 'Beale' },
  { value: 'sphere', label: 'Sphere' },
  { value: 'booth', label: 'Booth' },
  { value: 'styblinski-tang', label: 'Styblinski-Tang' },
]
const FUNCS_ND = [
  { value: 'rastrigin', label: 'Rastrigin' },
  { value: 'sphere', label: 'Sphere' },
  { value: 'rosenbrock', label: 'Rosenbrock' },
  { value: 'ackley', label: 'Ackley' },
  { value: 'griewank', label: 'Griewank' },
  { value: 'schwefel', label: 'Schwefel 2.26' },
  { value: 'zakharov', label: 'Zakharov' },
  { value: 'styblinski-tang', label: 'Styblinski-Tang' },
]
const DATASETS = [
  { value: 'breast_cancer', label: 'Breast Cancer' },
  { value: 'iris', label: 'Iris' },
  { value: 'wine', label: 'Wine' },
  { value: 'digits', label: 'Digits (MNIST 8×8)' },
]
const seed: FieldDef = { key: 'seed', label: 'Seed', type: 'integer', default: '1' }

const metaTheory = (
  <Theory>
    <p>
      Metaheuristik berbasis populasi mencari optimum tanpa gradien dengan menyeimbangkan <strong>eksplorasi</strong> (menjelajah
      ruang pencarian) dan <strong>eksploitasi</strong> (memperhalus solusi terbaik). Paper Liu et al. (2025) membahas algoritma
      terinspirasi alam (NOA, HHO, AVOA, IARO), algoritma berbasis matematika/fisika (EDO, AOA), dan evolution strategy (CMA-ES,
      LM-MA). PSO, GA, DE, dan SA disertakan sebagai pembanding klasik.
    </p>
    <p>
      Karena bersifat acak, kinerja harus dinilai dari banyak run independen dan diuji secara statistik (Friedman untuk semua
      algoritma, Wilcoxon signed-rank untuk perbandingan berpasangan). Teorema “no free lunch”: tidak ada algoritma yang terbaik
      untuk semua masalah.
    </p>
  </Theory>
)

export const populationConfig: VariantPageConfig = {
  title: 'Metaheuristik Berbasis Populasi (Population-Based)',
  subtitle: 'Animasi pergerakan populasi NOA, HHO, AVOA, EDO, IARO, CMA-ES, LM-MA, AOA, PSO, GA, DE, dan SA pada fungsi uji 2D.',
  exampleModule: 'ml',
  variants: [
    {
      id: 'metaheuristics',
      label: 'Animasi populasi',
      endpoint: '/ml/population',
      fields: [
        { key: 'function', label: 'Fungsi uji 2D', type: 'select', options: FUNCS_2D },
        { key: 'algorithms', label: 'Algoritma (maks. 6)', type: 'multiselect', options: ALGOS, minItems: 6, required: true, default: 'hho, pso, cmaes' },
        { key: 'pop', label: 'Ukuran populasi', type: 'integer', default: '20' },
        { key: 'iters', label: 'Iterasi', type: 'integer', default: '60' },
        seed,
      ],
      theory: metaTheory,
    },
    {
      id: 'population-rastrigin',
      label: 'Algoritma paper',
      endpoint: '/ml/population',
      fields: [
        { key: 'function', label: 'Fungsi uji 2D', type: 'select', options: FUNCS_2D },
        { key: 'algorithms', label: 'Algoritma (maks. 6)', type: 'multiselect', options: ALGOS, minItems: 6, required: true },
        { key: 'pop', label: 'Ukuran populasi', type: 'integer', default: '20' },
        { key: 'iters', label: 'Iterasi', type: 'integer', default: '80' },
        seed,
      ],
      theory: metaTheory,
    },
  ],
}

export const benchmarkConfig: VariantPageConfig = {
  title: 'Benchmark & Uji Statistik Metaheuristik',
  subtitle: 'N run independen: rata-rata, simpangan baku, terbaik, terburuk, kurva konvergensi, serta uji Friedman dan Wilcoxon.',
  exampleModule: 'ml',
  variants: [
    {
      id: 'metaheuristic-benchmark',
      label: 'Benchmark',
      endpoint: '/ml/benchmark',
      fields: [
        { key: 'function', label: 'Fungsi benchmark', type: 'select', options: FUNCS_ND },
        { key: 'dim', label: 'Dimensi', type: 'integer', default: '10' },
        { key: 'algorithms', label: 'Algoritma (maks. 8)', type: 'multiselect', options: ALGOS, minItems: 8, required: true },
        { key: 'pop', label: 'Ukuran populasi', type: 'integer', default: '30' },
        { key: 'iters', label: 'Iterasi', type: 'integer', default: '100' },
        { key: 'runs', label: 'Jumlah run independen', type: 'integer', default: '10' },
        seed,
      ],
      theory: (
        <Theory formulas={[String.raw`\chi^2_F = \frac{12n}{k(k+1)}\sum_j \left(\bar R_j - \frac{k+1}{2}\right)^2`]}>
          <p>
            Setiap algoritma dijalankan berulang dengan seed berbeda. Uji Friedman (non-parametrik, berpasangan per run) menguji
            apakah ada perbedaan kinerja; bila ya, Wilcoxon signed-rank membandingkan algoritma terbaik dengan setiap pesaingnya
            (lihat modul Statistika → Uji Non-parametrik).
          </p>
        </Theory>
      ),
    },
  ],
}

export const hpoConfig: VariantPageConfig = {
  title: 'Optimasi Hyperparameter (HPO)',
  subtitle: 'Grid search, random search, Bayesian optimization (Gaussian process), dan metaheuristik untuk tuning model scikit-learn.',
  exampleModule: 'ml',
  variants: [
    {
      id: 'hyperparameter-optimization',
      label: 'Tuning model',
      endpoint: '/ml/hyperparameter',
      fields: [
        { key: 'dataset', label: 'Dataset', type: 'select', options: DATASETS },
        { key: 'model', label: 'Model', type: 'select', options: [{ value: 'svm', label: 'SVM RBF (C, γ)' }, { value: 'rf', label: 'Random Forest (n_estimators, max_depth)' }, { value: 'knn', label: 'kNN (k, bobot)' }, { value: 'mlp', label: 'MLP (α, neuron)' }] },
        { key: 'methods', label: 'Metode', type: 'multiselect', required: true, default: 'grid, random, bayes, pso', options: [{ value: 'grid', label: 'Grid search' }, { value: 'random', label: 'Random search' }, { value: 'bayes', label: 'Bayesian (GP-EI)' }, { value: 'pso', label: 'PSO' }, { value: 'de', label: 'DE' }, { value: 'hho', label: 'HHO' }] },
        { key: 'budget', label: 'Evaluasi per metode', type: 'integer', default: '20', hint: 'Setiap evaluasi = validasi silang 3-fold.' },
        { key: 'seed', label: 'Seed', type: 'integer', default: '0' },
      ],
      theory: (
        <Theory formulas={[String.raw`\lambda^* = \arg\max_{\lambda} \text{CV}(\lambda)`]}>
          <p>
            Hyperparameter (mis. C dan γ pada SVM) tidak dipelajari dari data, tetapi menentukan kinerja model. Grid search mudah
            tetapi boros; random search lebih efisien di dimensi tinggi; Bayesian optimization memakai model pengganti (Gaussian
            process) dan fungsi akuisisi expected improvement; metaheuristik mencari secara populasi.
          </p>
        </Theory>
      ),
    },
  ],
}

export const featureConfig: VariantPageConfig = {
  title: 'Seleksi Fitur (Feature Selection)',
  subtitle: 'Wrapper metaheuristik biner (PSO, HHO, …) vs filter (mutual information, chi-square) vs reduksi dimensi PCA.',
  exampleModule: 'ml',
  variants: [
    {
      id: 'feature-selection',
      label: 'Seleksi fitur',
      endpoint: '/ml/feature-selection',
      fields: [
        { key: 'dataset', label: 'Dataset', type: 'select', options: DATASETS },
        { key: 'wrapper', label: 'Wrapper biner', type: 'multiselect', default: 'pso, hho', options: [{ value: 'pso', label: 'PSO' }, { value: 'hho', label: 'HHO' }, { value: 'de', label: 'DE' }, { value: 'ga', label: 'GA' }, { value: 'avoa', label: 'AVOA' }] },
        { key: 'k_filter', label: 'Jumlah fitur filter / komponen PCA', type: 'integer', default: '8' },
        { key: 'alpha', label: 'Bobot akurasi α dalam fitness', type: 'number', default: '0.99' },
        { key: 'seed', label: 'Seed', type: 'integer', default: '0' },
      ],
      theory: (
        <Theory formulas={[String.raw`\text{fitness} = \alpha(1 - \text{akurasi}) + (1-\alpha)\frac{|S|}{D}`]}>
          <p>
            Wrapper menilai subset fitur dengan model (akurat tetapi mahal); filter menilai fitur satu per satu secara statistik
            (cepat); PCA membentuk fitur baru berupa kombinasi linier. Metaheuristik kontinu diubah menjadi biner dengan fungsi
            transfer sigmoid.
          </p>
        </Theory>
      ),
    },
  ],
}

const orTheory = (
  <Theory>
    <p>
      Banyak masalah OR kombinatorial (TSP, knapsack, penjadwalan) bersifat NP-hard: metode eksak (DP, branch-and-bound) hanya
      praktis untuk ukuran kecil. Metaheuristik memberi solusi baik dengan cepat untuk ukuran besar; di sini hasilnya dibandingkan
      langsung dengan solusi eksak dari modul Riset Operasi bila ukurannya memungkinkan.
    </p>
  </Theory>
)

export const metaOrConfig: VariantPageConfig = {
  title: 'Metaheuristik untuk Masalah OR (TSP, Knapsack, Penjadwalan)',
  subtitle: 'GA dan simulated annealing dibandingkan dengan solusi eksak (Held-Karp, DP knapsack, DP penjadwalan).',
  exampleModule: 'ml',
  variants: [
    {
      id: 'metaheuristic-or',
      label: 'TSP',
      endpoint: '/ml/tsp',
      fields: [
        { key: 'coords', label: 'Koordinat kota “x y” per baris (opsional)', type: 'matrix', placeholder: '0 0\n10 5\n3 8', hint: 'Kosongkan untuk kota acak.' },
        { key: 'n_random', label: 'Jumlah kota acak', type: 'integer', default: '10' },
        seed,
      ],
      theory: orTheory,
    },
    {
      id: 'knapsack-meta',
      label: 'Knapsack 0-1',
      endpoint: '/ml/knapsack',
      fields: [
        { key: 'weights', label: 'Bobot barang', type: 'numbers', required: true },
        { key: 'values', label: 'Nilai barang', type: 'numbers', required: true },
        { key: 'capacity', label: 'Kapasitas', type: 'number', required: true },
        seed,
      ],
      theory: orTheory,
    },
    {
      id: 'scheduling',
      label: 'Penjadwalan',
      endpoint: '/ml/scheduling',
      fields: [
        { key: 'processing', label: 'Waktu proses tiap pekerjaan', type: 'numbers', required: true },
        { key: 'weights', label: 'Bobot (kepentingan) tiap pekerjaan', type: 'numbers', required: true },
        { key: 'due', label: 'Tenggat tiap pekerjaan', type: 'numbers', required: true },
        seed,
      ],
      theory: orTheory,
    },
  ],
}

export const rlConfig: VariantPageConfig = {
  title: 'Reinforcement Learning Ringan (Q-learning)',
  subtitle: 'Gridworld dengan Q-learning, dibandingkan dengan solusi optimal MDP (value iteration, Bab 21).',
  exampleModule: 'ml',
  variants: [
    {
      id: 'reinforcement-learning',
      label: 'Gridworld',
      endpoint: '/ml/gridworld',
      fields: [
        { key: 'grid', label: 'Peta grid', type: 'textarea', required: true, placeholder: '. . . G\n. # . T\nS . . .', hint: 'S = start, G = goal, T = jebakan, # = dinding, . = kosong; pisahkan sel dengan spasi.' },
        { key: 'goal_reward', label: 'Imbalan goal', type: 'number', default: '10' },
        { key: 'trap_reward', label: 'Imbalan jebakan', type: 'number', default: '-10' },
        { key: 'step_cost', label: 'Biaya per langkah', type: 'number', default: '0.1' },
        { key: 'gamma', label: 'Faktor diskon γ', type: 'number', default: '0.9' },
        { key: 'alpha', label: 'Laju belajar α', type: 'number', default: '0.3' },
        { key: 'epsilon', label: 'Eksplorasi ε awal', type: 'number', default: '0.3' },
        { key: 'episodes', label: 'Jumlah episode', type: 'integer', default: '3000' },
        { key: 'slip', label: 'Peluang tergelincir', type: 'number', default: '0.1' },
        seed,
      ],
      theory: (
        <Theory formulas={[String.raw`Q(s,a) \leftarrow Q(s,a) + \alpha\left[r + \gamma \max_{a'} Q(s',a') - Q(s,a)\right]`]}>
          <p>
            Q-learning mempelajari nilai aksi tanpa mengetahui model transisi, hanya dari pengalaman (trial-and-error). Bila model
            diketahui, masalah yang sama adalah MDP dan dapat diselesaikan langsung dengan value iteration (Bab 21) — keduanya
            dibandingkan di sini.
          </p>
        </Theory>
      ),
    },
  ],
}
