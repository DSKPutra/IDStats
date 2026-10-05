import type { FieldDef } from '@/components/form/fields'
import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from '@/pages/stats/configs/Theory'
import { LP_SYNTAX_HINT } from './common'

const FUNC_HINT = 'Gunakan ^ untuk pangkat dan * untuk perkalian antarvariabel (x1*x2). Fungsi: ln, exp, sqrt, sin, cos, abs.'
const maximize: FieldDef = { key: 'maximize', label: 'Maksimasi', type: 'boolean', default: 'true', placeholder: 'Maksimumkan (hapus centang untuk minimasi)' }

export const dpConfig: VariantPageConfig = {
  title: 'Pemrograman Dinamis (Dynamic Programming, Bab 11)',
  subtitle: 'Rekursi mundur tahap demi tahap: rute bertahap, alokasi sumber daya, knapsack, dan DP probabilistik.',
  exampleModule: 'or',
  variants: [
    {
      id: 'stagecoach',
      label: 'Stagecoach / rute bertahap',
      endpoint: '/dp/stagecoach',
      fields: [
        { key: 'edges', label: 'Busur berarah: asal tujuan biaya', type: 'graph', graphValues: 1, graphDirected: true, required: true, placeholder: '1 2 2\n1 3 4\n2 4 7' },
        { key: 'source', label: 'Node awal', type: 'text', required: true, placeholder: '1' },
        { key: 'target', label: 'Node akhir', type: 'text', required: true, placeholder: '10' },
        { key: 'sense', label: 'Tujuan', type: 'select', options: [{ value: 'min', label: 'Minimumkan total biaya' }, { value: 'max', label: 'Maksimumkan total' }] },
      ],
      theory: (
        <Theory formulas={[String.raw`f_n^*(s) = \min_{x_n} \{ c_{s x_n} + f_{n+1}^*(x_n) \}`]}>
          <p>
            Prinsip optimalitas: kebijakan optimal untuk tahap tersisa tidak bergantung pada keputusan tahap sebelumnya. Mulai dari
            tahap terakhir, hitung nilai optimal setiap state, lalu mundur sampai tahap pertama.
          </p>
        </Theory>
      ),
    },
    {
      id: 'resource-allocation',
      label: 'Alokasi sumber daya',
      endpoint: '/dp/resource-allocation',
      fields: [
        { key: 'total', label: 'Total unit sumber daya', type: 'integer', required: true, placeholder: '5' },
        { key: 'returns', label: 'Tabel hasil (baris = aktivitas, kolom = 0, 1, …, total unit)', type: 'matrix', required: true, placeholder: '0 45 70 90 105 120\n0 20 45 75 110 150\n0 50 70 80 100 130' },
        { key: 'activities', label: 'Nama aktivitas (opsional)', type: 'labels' },
        { key: 'combine', label: 'Penggabungan hasil', type: 'select', options: [{ value: 'sum', label: 'Jumlah (deterministik)' }, { value: 'product', label: 'Hasil kali (probabilistik, mis. peluang gagal)' }] },
        { key: 'sense', label: 'Tujuan', type: 'select', options: [{ value: 'max', label: 'Maksimumkan' }, { value: 'min', label: 'Minimumkan' }] },
      ],
      theory: (
        <Theory formulas={[String.raw`f_n^*(s) = \max_{0 \le x_n \le s} \{ p_n(x_n) + f_{n+1}^*(s - x_n) \}`]}>
          <p>
            Tahap = aktivitas, state = unit sumber daya yang masih tersedia, keputusan = unit yang diberikan ke aktivitas tahap ini.
            Versi probabilistik (Bab 11.4) mengalikan peluang, misalnya meminimumkan peluang semua tim riset gagal.
          </p>
        </Theory>
      ),
    },
    {
      id: 'probabilistic-allocation',
      label: 'Alokasi probabilistik',
      endpoint: '/dp/resource-allocation',
      fields: [
        { key: 'total', label: 'Total unit', type: 'integer', required: true },
        { key: 'returns', label: 'Peluang gagal (baris = tim, kolom = 0..total unit)', type: 'matrix', required: true },
        { key: 'activities', label: 'Nama (opsional)', type: 'labels' },
        { key: 'combine', label: 'Penggabungan', type: 'select', default: 'product', options: [{ value: 'product', label: 'Hasil kali' }] },
        { key: 'sense', label: 'Tujuan', type: 'select', default: 'min', options: [{ value: 'min', label: 'Minimumkan' }] },
      ],
      theory: <Theory><p>DP probabilistik: state berikutnya atau hasil tahap bergantung pada peluang; di sini tujuan = meminimumkan peluang semua tim gagal (hasil kali peluang gagal).</p></Theory>,
    },
    {
      id: 'knapsack',
      label: 'Knapsack',
      endpoint: '/dp/knapsack',
      fields: [
        { key: 'weights', label: 'Bobot barang (bilangan bulat)', type: 'numbers', required: true, placeholder: '3, 4, 2, 5' },
        { key: 'values', label: 'Nilai barang', type: 'numbers', required: true, placeholder: '4, 5, 3, 7' },
        { key: 'capacity', label: 'Kapasitas', type: 'integer', required: true, placeholder: '10' },
        { key: 'max_copies', label: 'Maksimum unit tiap barang (opsional, default 1)', type: 'numbers', placeholder: '2, 1, 3, 1' },
        { key: 'names', label: 'Nama barang (opsional)', type: 'labels' },
      ],
      theory: <Theory formulas={[String.raw`f_i^*(s) = \max_{x} \{ x v_i + f_{i+1}^*(s - x w_i) \}`]}><p>Setiap barang adalah satu tahap; state = sisa kapasitas.</p></Theory>,
    },
    {
      id: 'betting',
      label: 'DP probabilistik: taruhan',
      endpoint: '/dp/betting',
      fields: [
        { key: 'chips', label: 'Keping awal', type: 'integer', required: true, placeholder: '3' },
        { key: 'target', label: 'Target keping', type: 'integer', required: true, placeholder: '5' },
        { key: 'plays', label: 'Jumlah taruhan', type: 'integer', required: true, placeholder: '3' },
        { key: 'p_win', label: 'Peluang menang tiap taruhan', type: 'number', required: true, placeholder: '0.6667' },
      ],
      theory: <Theory formulas={[String.raw`f_n^*(s) = \max_x \{ p f_{n+1}^*(s+x) + (1-p) f_{n+1}^*(s-x) \}`]}><p>State berikutnya acak: menang (s + x) dengan peluang p atau kalah (s − x). Tujuannya memaksimumkan peluang mencapai target.</p></Theory>,
    },
  ],
}

export const ipConfig: VariantPageConfig = {
  title: 'Pemrograman Bilangan Bulat (Integer Programming, Bab 12)',
  subtitle: 'BIP & MIP dengan branch-and-bound (pohon visual) serta formulasi biner: fixed-charge, either-or, K dari N kendala.',
  exampleModule: 'or',
  variants: [
    {
      id: 'branch-and-bound',
      label: 'Branch-and-bound (BIP)',
      endpoint: '/ip/branch-and-bound',
      fields: [{ key: 'model', label: 'Model', type: 'textarea', required: true, placeholder: 'max Z = 9x1 + 5x2 + 6x3 + 4x4\n6x1 + 3x2 + 5x3 + 2x4 <= 10\nbin x1, x2, x3, x4', hint: LP_SYNTAX_HINT + ' Tambahkan baris “int x1, x2” atau “bin y1, y2”.' }],
      theory: (
        <Theory>
          <p>
            Branch-and-bound membagi masalah menjadi submasalah (branching), menghitung batas dengan relaksasi LP (bounding), dan
            membuang submasalah yang tidak mungkin lebih baik (fathoming): tidak layak, batasnya ≤ incumbent, atau solusinya sudah
            bulat. Solusi bulat terbaik yang ditemukan disebut incumbent.
          </p>
        </Theory>
      ),
    },
    {
      id: 'mip',
      label: 'Mixed integer (MIP)',
      endpoint: '/ip/branch-and-bound',
      fields: [{ key: 'model', label: 'Model', type: 'textarea', required: true, hint: 'Hanya variabel yang ditulis di baris “int …” yang harus bulat; sisanya kontinu.' }],
      theory: <Theory><p>Pada MIP hanya sebagian variabel yang harus bulat; pencabangan dilakukan hanya pada variabel tersebut, sedangkan variabel kontinu boleh pecahan.</p></Theory>,
    },
    {
      id: 'binary-formulation',
      label: 'Formulasi biner',
      endpoint: '/ip/binary-formulation',
      fields: [
        { key: 'model', label: 'Model dasar', type: 'textarea', required: true, hint: 'Kendala yang selalu berlaku. Boleh tanpa kendala bila semua ada di aturan.' },
        { key: 'rules', label: 'Aturan biner (satu per baris)', type: 'textarea', required: true, placeholder: 'either M=100: 3x1 + 2x2 <= 18 | x1 + 4x2 <= 16\nk=2 M=100: x1 <= 3 | x2 <= 2 | x1 + x2 <= 4\nfixed x1: biaya=5, maks=10', hint: 'either-or (salah satu kendala berlaku), k=… (K dari N kendala berlaku), fixed (biaya tetap bila variabel > 0).' },
      ],
      theory: (
        <Theory formulas={[String.raw`f_1(x) \le b_1 + My,\quad f_2(x) \le b_2 + M(1-y),\quad y \in \{0,1\}`]}>
          <p>
            Variabel biner memodelkan keputusan ya/tidak. Kendala alternatif (either-or) dan K dari N kendala memakai konstanta M yang
            sangat besar untuk “mematikan” kendala. Biaya tetap: biaya K dikenakan hanya bila x &gt; 0 melalui x ≤ U·y.
          </p>
        </Theory>
      ),
    },
  ],
}

export const nlpConfig: VariantPageConfig = {
  title: 'Pemrograman Nonlinear (Nonlinear Programming, Bab 13)',
  subtitle: 'Biseksi, Newton, gradient search, kondisi KKT, quadratic, separable, Frank-Wolfe, SUMT, dan multistart.',
  exampleModule: 'or',
  variants: [
    {
      id: 'one-variable',
      label: 'Biseksi (1 variabel)',
      endpoint: '/nlp/one-variable',
      fields: [
        { key: 'func', label: 'f(x)', type: 'text', required: true, placeholder: '12x - 3x^4 - 2x^6', hint: FUNC_HINT },
        { key: 'method', label: 'Metode', type: 'select', default: 'bisection', options: [{ value: 'bisection', label: 'Biseksi' }] },
        maximize,
        { key: 'lower', label: 'Batas bawah', type: 'number', required: true },
        { key: 'upper', label: 'Batas atas', type: 'number', required: true },
        { key: 'tol', label: 'Toleransi ε', type: 'number', default: '0.01' },
      ],
      theory: <Theory formulas={[String.raw`x' = \tfrac{\underline{x} + \bar{x}}{2}`]}><p>Untuk fungsi konkaf, f′ berubah tanda tepat sekali. Biseksi mempersempit interval berdasarkan tanda turunan di titik tengah.</p></Theory>,
    },
    {
      id: 'newton',
      label: 'Newton (1 variabel)',
      endpoint: '/nlp/one-variable',
      fields: [
        { key: 'func', label: 'f(x)', type: 'text', required: true, hint: FUNC_HINT },
        { key: 'method', label: 'Metode', type: 'select', default: 'newton', options: [{ value: 'newton', label: 'Newton' }] },
        maximize,
        { key: 'x0', label: 'Titik awal x₀', type: 'number', required: true },
        { key: 'tol', label: 'Toleransi ε', type: 'number', default: '0.00001' },
      ],
      theory: <Theory formulas={[String.raw`x_{i+1} = x_i - \frac{f'(x_i)}{f''(x_i)}`]}><p>Metode Newton memakai aproksimasi kuadratik sehingga konvergen sangat cepat di dekat optimum.</p></Theory>,
    },
    {
      id: 'gradient-search',
      label: 'Gradient search',
      endpoint: '/nlp/gradient',
      fields: [
        { key: 'func', label: 'f(x₁, x₂, …)', type: 'text', required: true, placeholder: '2x1*x2 + 2x2 - x1^2 - 2x2^2', hint: FUNC_HINT },
        { key: 'x0', label: 'Titik awal', type: 'numbers', required: true, placeholder: '0, 0' },
        maximize,
        { key: 'tol', label: 'Toleransi ε', type: 'number', default: '0.000001' },
      ],
      theory: <Theory formulas={[String.raw`\mathbf{x}' = \mathbf{x} + t^*\nabla f(\mathbf{x})`]}><p>Bergerak searah gradien (arah naik tercuram) dengan panjang langkah optimal dari line search.</p></Theory>,
    },
    {
      id: 'kkt',
      label: 'Kondisi KKT',
      endpoint: '/nlp/kkt',
      fields: [
        { key: 'func', label: 'f(x)', type: 'text', required: true, placeholder: 'ln(x1 + 1) + x2', hint: FUNC_HINT },
        { key: 'constraints', label: 'Kendala gᵢ(x) ≤ bᵢ (satu per baris)', type: 'textarea', required: true, placeholder: '2x1 + x2 <= 3' },
        maximize,
        { key: 'nonneg', label: 'Nonnegatif', type: 'boolean', default: 'true', placeholder: 'x ≥ 0' },
      ],
      theory: <Theory formulas={[String.raw`\frac{\partial f}{\partial x_j} - \sum_i u_i \frac{\partial g_i}{\partial x_j} \le 0,\quad u_i(g_i(\mathbf{x}) - b_i) = 0,\quad u_i \ge 0`]}><p>Kondisi Karush-Kuhn-Tucker adalah syarat perlu optimalitas; untuk masalah konveks juga syarat cukup.</p></Theory>,
    },
    {
      id: 'quadratic',
      label: 'Quadratic programming',
      endpoint: '/nlp/quadratic',
      fields: [
        { key: 'objective', label: 'Fungsi tujuan kuadratik (maks, konkaf)', type: 'text', required: true, placeholder: '15x1 + 30x2 + 4x1*x2 - 2x1^2 - 4x2^2', hint: FUNC_HINT },
        { key: 'constraints', label: 'Kendala linier ≤', type: 'textarea', required: true, placeholder: 'x1 + 2x2 <= 30' },
      ],
      theory: <Theory><p>QP konveks diselesaikan dengan simpleks termodifikasi (Wolfe): kondisi KKT linier + kendala komplementer xⱼyⱼ = 0, uᵢvᵢ = 0 dijaga lewat aturan masuk terbatas.</p></Theory>,
    },
    {
      id: 'separable',
      label: 'Separable programming',
      endpoint: '/nlp/separable',
      fields: [
        { key: 'terms', label: 'Fungsi per variabel (satu per baris)', type: 'textarea', required: true, placeholder: 'x1: 3x1 - x1^2 ; 0..3\nx2: 5x2 - x2^2 ; 0..5', hint: 'Format: nama: fungsi konkaf ; batas_bawah..batas_atas' },
        { key: 'constraints', label: 'Kendala linier', type: 'textarea', placeholder: 'x1 + x2 <= 4' },
        { key: 'segments', label: 'Jumlah segmen per fungsi', type: 'integer', default: '4' },
      ],
      theory: <Theory><p>Fungsi tujuan yang dapat dipisah f(x) = Σ fⱼ(xⱼ) dengan fⱼ konkaf didekati linier sepotong-sepotong, sehingga masalahnya menjadi LP.</p></Theory>,
    },
    {
      id: 'frank-wolfe',
      label: 'Frank-Wolfe',
      endpoint: '/nlp/frank-wolfe',
      fields: [
        { key: 'func', label: 'f(x)', type: 'text', required: true, placeholder: '5x1 - x1^2 + 8x2 - 2x2^2', hint: FUNC_HINT },
        { key: 'constraints', label: 'Kendala linier', type: 'textarea', required: true, placeholder: '3x1 + 2x2 <= 6' },
        { key: 'x0', label: 'Titik awal layak', type: 'numbers', required: true, placeholder: '0, 0' },
        maximize,
      ],
      theory: <Theory><p>Convex programming dengan kendala linier: setiap iterasi menyelesaikan LP dari aproksimasi linier f, lalu line search di antara titik saat ini dan solusi LP.</p></Theory>,
    },
    {
      id: 'sumt',
      label: 'SUMT (barrier)',
      endpoint: '/nlp/sumt',
      fields: [
        { key: 'func', label: 'f(x)', type: 'text', required: true, placeholder: 'x1*x2', hint: FUNC_HINT },
        { key: 'constraints', label: 'Kendala gᵢ(x) ≤ bᵢ', type: 'textarea', required: true, placeholder: 'x1^2 + x2 <= 3' },
        { key: 'x0', label: 'Titik awal interior', type: 'numbers', required: true, placeholder: '1, 1' },
        maximize,
        { key: 'r0', label: 'r awal', type: 'number', default: '1' },
        { key: 'theta', label: 'Faktor pengecil θ', type: 'number', default: '0.01' },
      ],
      theory: <Theory formulas={[String.raw`P(\mathbf{x}; r) = f(\mathbf{x}) - r\left(\sum \frac{1}{b_i - g_i(\mathbf{x})} + \sum \frac{1}{x_j}\right)`]}><p>Sequential Unconstrained Minimization Technique: kendala diganti fungsi barrier; maksimasi tanpa kendala diulang dengan r yang mengecil.</p></Theory>,
    },
    {
      id: 'multistart',
      label: 'Nonkonveks (multistart)',
      endpoint: '/nlp/multistart',
      fields: [
        { key: 'func', label: 'f(x)', type: 'text', required: true, hint: FUNC_HINT },
        { key: 'lower', label: 'Batas bawah tiap variabel', type: 'numbers', required: true, placeholder: '0' },
        { key: 'upper', label: 'Batas atas tiap variabel', type: 'numbers', required: true, placeholder: '31' },
        { key: 'starts', label: 'Jumlah titik awal', type: 'integer', default: '20' },
        maximize,
      ],
      theory: <Theory><p>Fungsi nonkonveks dapat memiliki banyak optimum lokal. Multistart menjalankan pencarian lokal dari banyak titik awal dan memilih hasil terbaik.</p></Theory>,
    },
  ],
}

const gameTheory = (
  <Theory formulas={[String.raw`\underline{v} = \max_i \min_j a_{ij} \le v \le \min_j \max_i a_{ij} = \bar{v}`]}>
    <p>
      Pada permainan dua pemain jumlah nol, pemain I memaksimumkan payoff minimum (maksimin), pemain II meminimumkan payoff
      maksimum (minimaks). Bila keduanya sama ada <strong>titik pelana</strong> dan strategi murni stabil. Bila tidak, gunakan
      strategi campuran; teorema minimaks menjamin nilai permainan ada dan dapat dihitung dengan LP (metode grafik untuk 2×n / m×2).
    </p>
  </Theory>
)

export const gameConfig: VariantPageConfig = {
  title: 'Teori Permainan (Game Theory, Bab 14)',
  subtitle: 'Permainan dua pemain jumlah nol: titik pelana, strategi dominan, strategi campuran, metode grafik, dan LP.',
  exampleModule: 'or',
  variants: [
    {
      id: 'zero-sum',
      label: 'Strategi campuran',
      endpoint: '/games/zero-sum',
      fields: [
        { key: 'payoff', label: 'Matriks payoff pemain I (baris = strategi I, kolom = strategi II)', type: 'matrix', required: true, placeholder: '0 -2 2\n5 4 -3\n2 3 -4' },
        { key: 'row_names', label: 'Nama strategi pemain I (opsional)', type: 'labels' },
        { key: 'col_names', label: 'Nama strategi pemain II (opsional)', type: 'labels' },
      ],
      theory: gameTheory,
    },
    {
      id: 'saddle-point',
      label: 'Titik pelana',
      endpoint: '/games/zero-sum',
      fields: [{ key: 'payoff', label: 'Matriks payoff pemain I', type: 'matrix', required: true }],
      theory: gameTheory,
    },
  ],
}
