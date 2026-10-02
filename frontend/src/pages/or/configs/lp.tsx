import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from '@/pages/stats/configs/Theory'
import { lpModelField } from './common'

export const lpGraphicalConfig: VariantPageConfig = {
  title: 'Metode Grafik LP (Graphical Method, Bab 3)',
  subtitle: 'Formulasi LP dua variabel, daerah layak, titik sudut, garis isoprofit, dan titik optimum.',
  exampleModule: 'or',
  variants: [
    {
      id: 'lp-graphical',
      label: 'Metode grafik',
      endpoint: '/lp/graphical',
      fields: [lpModelField()],
      theory: (
        <Theory formulas={[String.raw`\max\ Z = c_1x_1 + c_2x_2 \quad \text{s.t.}\quad a_{i1}x_1 + a_{i2}x_2 \le b_i,\ x_1, x_2 \ge 0`]}>
          <p>
            Model LP terdiri atas <strong>variabel keputusan</strong>, <strong>fungsi tujuan</strong> linier, dan
            <strong> kendala</strong> linier. Untuk dua variabel, setiap kendala adalah setengah bidang; irisannya adalah
            daerah layak berbentuk poligon konveks.
          </p>
          <p>
            Bila solusi optimal ada, salah satunya pasti di <em>titik sudut</em> (corner-point feasible solution).
            Garis isoprofit Z = k digeser sejajar ke arah perbaikan; titik terakhir yang disentuh adalah optimum.
            Asumsi LP: proporsionalitas, aditivitas, divisibilitas, dan kepastian.
          </p>
        </Theory>
      ),
    },
  ],
}

const simplexTheory = (
  <Theory formulas={[String.raw`\text{Uji rasio minimum: } \min_i \left\{ \frac{b_i}{a_{ie}} : a_{ie} > 0 \right\}`]}>
    <p>
      Simpleks bergerak dari satu titik sudut ke titik sudut tetangga yang lebih baik. Setiap iterasi: (1) pilih variabel
      masuk dengan koefisien baris 0 paling negatif, (2) uji rasio minimum untuk menentukan variabel keluar, (3) eliminasi
      Gauss-Jordan pada elemen pivot. Berhenti bila semua koefisien baris 0 ≥ 0.
    </p>
    <p>
      Kendala ≥ dan = membutuhkan <strong>variabel artifisial</strong>. <strong>Big-M</strong> memberi penalti −M pada
      fungsi tujuan; <strong>Dua Fase</strong> lebih dulu meminimumkan jumlah artifisial (Fase 1), lalu mengoptimalkan
      tujuan asli (Fase 2). Aturan Bland dipakai otomatis bila iterasi terlalu banyak untuk mencegah siklus.
    </p>
  </Theory>
)

export const simplexConfig: VariantPageConfig = {
  title: 'Metode Simpleks (Simplex Method, Bab 4)',
  subtitle: 'Tabel simpleks iterasi demi iterasi dengan pecahan eksak, Big-M, Dua Fase, dan analisis pasca-optimal.',
  exampleModule: 'or',
  variants: [
    { id: 'simplex', label: 'Simpleks (≤)', endpoint: '/lp/simplex', fields: [lpModelField(), { key: 'method', label: 'Metode', type: 'select', default: 'auto', options: [{ value: 'auto', label: 'Otomatis' }, { value: 'bigm', label: 'Big-M' }, { value: 'twophase', label: 'Dua Fase' }] }], theory: simplexTheory },
    { id: 'big-m', label: 'Big-M', endpoint: '/lp/simplex', fields: [lpModelField('min Z = 0.4x1 + 0.5x2\n0.3x1 + 0.1x2 <= 2.7\n0.5x1 + 0.5x2 = 6\n0.6x1 + 0.4x2 >= 6'), { key: 'method', label: 'Metode', type: 'select', default: 'bigm', options: [{ value: 'bigm', label: 'Big-M' }] }], theory: simplexTheory },
    { id: 'two-phase', label: 'Dua Fase', endpoint: '/lp/simplex', fields: [lpModelField('min Z = 0.4x1 + 0.5x2\n0.3x1 + 0.1x2 <= 2.7\n0.5x1 + 0.5x2 = 6\n0.6x1 + 0.4x2 >= 6'), { key: 'method', label: 'Metode', type: 'select', default: 'twophase', options: [{ value: 'twophase', label: 'Dua Fase' }] }], theory: simplexTheory },
  ],
}

export const revisedSimplexConfig: VariantPageConfig = {
  title: 'Simpleks Direvisi (Revised Simplex, Bab 5)',
  subtitle: 'Simpleks dalam bentuk matriks: B⁻¹, x_B = B⁻¹b, c_B B⁻¹, dan wawasan fundamental.',
  exampleModule: 'or',
  variants: [
    {
      id: 'revised-simplex',
      label: 'Simpleks direvisi',
      endpoint: '/lp/revised-simplex',
      fields: [lpModelField()],
      theory: (
        <Theory formulas={[String.raw`\mathbf{x}_B = \mathbf{B}^{-1}\mathbf{b},\quad Z = \mathbf{c}_B\mathbf{B}^{-1}\mathbf{b},\quad \bar{c}_j = \mathbf{c}_B\mathbf{B}^{-1}\mathbf{A}_j - c_j`]}>
          <p>
            Simpleks direvisi hanya menyimpan B⁻¹ (bukan seluruh tabel) sehingga lebih efisien untuk masalah besar.
            <strong> Wawasan fundamental</strong>: tabel akhir dapat dihitung dari tabel awal — baris 0 akhir = baris 0 awal +
            y*·(baris kendala awal), dan baris kendala akhir = S*·(baris kendala awal) dengan y* = c_B B⁻¹ dan S* = B⁻¹.
          </p>
        </Theory>
      ),
    },
  ],
}

export const dualityConfig: VariantPageConfig = {
  title: 'Dualitas & Analisis Sensitivitas (Bab 6)',
  subtitle: 'Konversi primal → dual, harga bayangan, rentang optimalitas & kelayakan, dan analisis what-if.',
  exampleModule: 'or',
  variants: [
    {
      id: 'duality',
      label: 'Dual & sensitivitas',
      endpoint: '/lp/sensitivity',
      fields: [
        lpModelField(),
        { key: 'what_if_rhs', label: 'What-if: ruas kanan baru (opsional)', type: 'numbers', placeholder: '4, 13, 18', hint: 'Satu nilai untuk setiap kendala, berurutan.' },
        { key: 'what_if_obj', label: 'What-if: koefisien tujuan baru (opsional)', type: 'numbers', placeholder: '3, 5', hint: 'Satu nilai untuk setiap variabel (urutan nama variabel).' },
      ],
      theory: (
        <Theory formulas={[String.raw`\text{Primal: } \max \mathbf{cx},\ \mathbf{Ax}\le\mathbf{b},\ \mathbf{x}\ge 0 \quad\Longleftrightarrow\quad \text{Dual: } \min \mathbf{yb},\ \mathbf{yA}\ge\mathbf{c},\ \mathbf{y}\ge 0`]}>
          <p>
            Setiap LP (primal) memiliki pasangan <strong>dual</strong>. Teorema dualitas kuat: bila primal optimal, nilai
            optimal dual sama. Solusi dual y* adalah <strong>harga bayangan</strong> — nilai marjinal tiap sumber daya.
          </p>
          <p>
            Aturan SOB untuk kendala/variabel “tidak wajar”: kendala ≥ pada maksimasi → yᵢ ≤ 0; kendala = → yᵢ bebas tanda.
            Analisis sensitivitas menentukan seberapa jauh bᵢ atau cⱼ boleh berubah tanpa mengubah basis optimal.
          </p>
        </Theory>
      ),
    },
  ],
}

export const lpOtherConfig: VariantPageConfig = {
  title: 'Algoritma LP Lain (Bab 7)',
  subtitle: 'Dual simpleks, LP parametrik, teknik batas atas, titik interior (affine scaling), dan goal programming.',
  exampleModule: 'or',
  variants: [
    {
      id: 'dual-simplex',
      label: 'Dual simpleks',
      endpoint: '/lp/dual-simplex',
      fields: [lpModelField('min W = 4y1 + 12y2 + 18y3\ny1 + 3y3 >= 3\n2y2 + 2y3 >= 5')],
      theory: (
        <Theory>
          <p>
            Dual simpleks bekerja pada tabel yang sudah optimal (baris 0 ≥ 0) tetapi belum layak (ada RHS negatif). Variabel
            keluar = baris dengan RHS paling negatif; variabel masuk dipilih dengan uji rasio pada baris 0. Sangat berguna
            setelah menambah kendala baru pada analisis sensitivitas.
          </p>
        </Theory>
      ),
    },
    {
      id: 'parametric',
      label: 'LP parametrik',
      endpoint: '/lp/parametric',
      fields: [
        lpModelField(),
        { key: 'kind', label: 'Yang berubah', type: 'select', options: [{ value: 'objective', label: 'Koefisien tujuan c(θ) = c + αθ' }, { value: 'rhs', label: 'Ruas kanan b(θ) = b + αθ' }] },
        { key: 'direction', label: 'Vektor arah α', type: 'numbers', required: true, placeholder: '2, -1' },
        { key: 'theta_max', label: 'θ maksimum', type: 'number', default: '10' },
      ],
      theory: (
        <Theory formulas={[String.raw`Z^*(\theta)\ \text{linier sepotong-sepotong}`]}>
          <p>
            Pemrograman parametrik menyelidiki solusi optimal ketika beberapa parameter berubah bersamaan secara linier
            terhadap θ. Untuk setiap basis optimal dicari rentang θ yang mempertahankannya; Z*(θ) linier di setiap rentang.
          </p>
        </Theory>
      ),
    },
    {
      id: 'upper-bound',
      label: 'Teknik batas atas',
      endpoint: '/lp/upper-bound',
      fields: [lpModelField('max Z = 3x1 + 5x2\nx1 <= 4\nx2 <= 6\n3x1 + 2x2 <= 18')],
      theory: (
        <Theory formulas={[String.raw`x_j = u_j - x_j'`]}>
          <p>
            Kendala batas atas 0 ≤ xⱼ ≤ uⱼ tidak dimasukkan ke tabel (mengurangi ukuran tabel). Uji rasio diperluas: variabel
            masuk bisa mencapai batas atasnya, atau variabel basis bisa naik sampai batas atasnya; saat itu dilakukan substitusi
            xⱼ = uⱼ − xⱼ′.
          </p>
        </Theory>
      ),
    },
    {
      id: 'interior-point',
      label: 'Titik interior',
      endpoint: '/lp/interior-point',
      fields: [
        lpModelField('max Z = x1 + 2x2\nx1 + x2 <= 8'),
        { key: 'start', label: 'Titik awal (opsional)', type: 'numbers', placeholder: '2, 2', hint: 'Harus memenuhi semua kendala secara ketat. Kosongkan untuk otomatis.' },
        { key: 'alpha', label: 'Ukuran langkah α', type: 'number', default: '0.5' },
      ],
      theory: (
        <Theory>
          <p>
            Algoritma titik interior (Karmarkar, 1984) bergerak melalui bagian dalam daerah layak. Varian affine scaling:
            skala ulang titik menjadi (1, …, 1), proyeksikan gradien ke ruang nol kendala, lalu melangkah sebesar α dari batas.
            Untuk masalah sangat besar, jumlah iterasinya bertambah sangat lambat dibanding simpleks.
          </p>
        </Theory>
      ),
    },
    {
      id: 'goal-programming',
      label: 'Goal programming',
      endpoint: '/lp/goal-programming',
      fields: [
        { key: 'mode', label: 'Jenis', type: 'select', options: [{ value: 'weighted', label: 'Berbobot (weighted)' }, { value: 'preemptive', label: 'Preemptive (prioritas)' }] },
        {
          key: 'goals',
          label: 'Tujuan (satu per baris)',
          type: 'textarea',
          required: true,
          placeholder: 'P1, w=5: 12x1 + 9x2 + 15x3 >= 125\nP2, w-=4, w+=2: 5x1 + 3x2 + 4x3 = 40\nP3, w=3: 5x1 + 7x2 + 8x3 <= 55',
          hint: 'Format: P<prioritas>, w=<bobot>: ekspresi ≥/≤/= target. Untuk “=” boleh bobot berbeda: w-=… (kurang), w+=… (lebih).',
        },
        { key: 'constraints', label: 'Kendala keras (opsional)', type: 'textarea', placeholder: 'x1 + x2 + x3 <= 15' },
      ],
      theory: (
        <Theory formulas={[String.raw`\sum_j a_{ij}x_j + d_i^- - d_i^+ = t_i,\quad \min \sum_i (w_i^- d_i^- + w_i^+ d_i^+)`]}>
          <p>
            Goal programming menangani beberapa tujuan yang saling bertentangan. Setiap tujuan diberi variabel deviasi
            d⁻ (kurang) dan d⁺ (lebih). Versi <strong>berbobot</strong> meminimumkan total penalti; versi
            <strong> preemptive</strong> menyelesaikan prioritas satu per satu tanpa mengorbankan prioritas yang lebih tinggi.
          </p>
        </Theory>
      ),
    },
  ],
}
