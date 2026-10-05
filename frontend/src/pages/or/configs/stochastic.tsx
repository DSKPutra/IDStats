import type { FieldDef } from '@/components/form/fields'
import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from '@/pages/stats/configs/Theory'

const FUNC_HINT = 'Gunakan ^ untuk pangkat dan * untuk perkalian antarvariabel (x1*x2).'
const payoffFields: FieldDef[] = [
  { key: 'payoff', label: 'Tabel payoff (baris = alternatif, kolom = keadaan alam)', type: 'matrix', required: true, placeholder: '700 -100\n90 90' },
  { key: 'prior', label: 'Peluang prior tiap keadaan alam', type: 'numbers', required: true, placeholder: '0.25, 0.75' },
  { key: 'actions', label: 'Nama alternatif (opsional)', type: 'labels', placeholder: 'Bor, Jual' },
  { key: 'states', label: 'Nama keadaan alam (opsional)', type: 'labels', placeholder: 'Ada minyak, Kering' },
]
const MDP_HINT = 'Satu baris per pasangan state–keputusan: state | keputusan | biaya | peluang transisi ke setiap state (urut kemunculan state; pecahan seperti 7/8 boleh).'
const series: FieldDef = { key: 'data', label: 'Deret waktu (urut dari periode 1)', type: 'numbers', required: true }
const horizon: FieldDef = { key: 'horizon', label: 'Jumlah periode yang diramal', type: 'integer', default: '3' }
const lamMu: FieldDef[] = [
  { key: 'lam', label: 'λ (laju kedatangan)', type: 'number', required: true },
  { key: 'mu', label: 'μ (laju pelayanan per server)', type: 'number', required: true },
]
const queueTheory = (
  <Theory formulas={[String.raw`L = \lambda W,\quad L_q = \lambda W_q,\quad W = W_q + \tfrac{1}{\mu},\quad \rho = \tfrac{\lambda}{s\mu}`]}>
    <p>
      Notasi Kendall A/B/s/K/N: distribusi antarkedatangan / waktu layanan / jumlah server / kapasitas / populasi (M = eksponensial,
      D = konstan, Eₖ = Erlang, G = umum). Model M/M/s adalah proses kelahiran-kematian; ukuran kinerja dihubungkan oleh rumus Little.
      Sistem stabil bila ρ &lt; 1.
    </p>
  </Theory>
)

export const decisionConfig: VariantPageConfig = {
  title: 'Analisis Keputusan (Decision Analysis, Bab 15)',
  subtitle: 'Kriteria tanpa eksperimen, aturan Bayes, posterior, EVPI & EVSI, pohon keputusan, dan teori utilitas.',
  exampleModule: 'or',
  variants: [
    {
      id: 'decision-criteria', label: 'Kriteria keputusan', endpoint: '/decision/criteria', fields: payoffFields,
      theory: <Theory formulas={[String.raw`E[\text{payoff}(a_i)] = \sum_j p_j a_{ij}`]}><p>Kriteria maksimin (pesimistis), likelihood maksimum, dan aturan keputusan Bayes (payoff harapan dengan peluang prior). Aturan Bayes paling banyak dipakai karena memanfaatkan seluruh informasi peluang.</p></Theory>,
    },
    {
      id: 'decision-experiment', label: 'Dengan eksperimen (EVPI, EVSI)', endpoint: '/decision/experimentation',
      fields: [
        ...payoffFields,
        { key: 'likelihood', label: 'Likelihood P(temuan | keadaan) — baris = keadaan, kolom = temuan', type: 'matrix', required: true, placeholder: '0.6 0.4\n0.2 0.8' },
        { key: 'findings', label: 'Nama temuan (opsional)', type: 'labels' },
        { key: 'cost', label: 'Biaya eksperimen', type: 'number', default: '0' },
      ],
      theory: <Theory formulas={[String.raw`P(S_j \mid F_k) = \frac{P(F_k \mid S_j)P(S_j)}{\sum_i P(F_k \mid S_i)P(S_i)},\quad EVSI = EP_{\text{eksperimen}} - EP_{\text{tanpa}}`]}><p>EVPI adalah batas atas nilai informasi apa pun. Eksperimen (mis. survei seismik) layak bila EVSI melebihi biayanya.</p></Theory>,
    },
    {
      id: 'decision-tree', label: 'Pohon keputusan', endpoint: '/decision/tree',
      fields: [{ key: 'tree', label: 'Pohon keputusan', type: 'textarea', required: true, placeholder: '[D] Pilih\n  A -> [C] Untung?\n    Ya (p=0.4) = 100\n    Tidak (p=0.6) = -20\n  B (biaya=5) = 30', hint: '[D] = keputusan, [C] = peluang, “= nilai” = hasil. Opsi cabang: (p=…, biaya=…). Indentasi menunjukkan anak.' }],
      theory: <Theory><p>Pohon keputusan dievaluasi dengan rollback dari kanan ke kiri: simpul peluang diganti nilai harapannya, simpul keputusan memilih cabang terbaik.</p></Theory>,
    },
    {
      id: 'utility', label: 'Teori utilitas', endpoint: '/decision/utility',
      fields: [
        ...payoffFields,
        { key: 'kind', label: 'Fungsi utilitas', type: 'select', options: [{ value: 'exponential', label: 'Eksponensial u(M) = R(1 − e^(−M/R))' }, { value: 'table', label: 'Tabel (interpolasi linier)' }] },
        { key: 'risk_r', label: 'Toleransi risiko R', type: 'number', placeholder: '250', showIf: (r) => r.kind === 'exponential' },
        { key: 'table', label: 'Tabel utilitas: nilai_uang utilitas', type: 'textarea', placeholder: '-100 -150\n0 0\n90 90\n700 580', showIf: (r) => r.kind === 'table' },
      ],
      theory: <Theory><p>Pengambil keputusan yang menghindari risiko memaksimumkan utilitas harapan, bukan payoff harapan. Fungsi utilitas konkaf mencerminkan sikap menghindari risiko.</p></Theory>,
    },
  ],
}

export const markovConfig: VariantPageConfig = {
  title: 'Rantai Markov (Markov Chains, Bab 16)',
  subtitle: 'Chapman-Kolmogorov, klasifikasi state, steady-state, waktu first passage, state penyerap, dan CTMC.',
  exampleModule: 'or',
  variants: [
    {
      id: 'markov-chain', label: 'Analisis rantai Markov', endpoint: '/markov/analyze',
      fields: [
        { key: 'matrix', label: 'Matriks transisi P (setiap baris berjumlah 1)', type: 'matrix', required: true },
        { key: 'names', label: 'Nama state (opsional)', type: 'labels' },
        { key: 'steps', label: 'n langkah', type: 'integer', default: '4' },
        { key: 'initial', label: 'Distribusi awal (opsional)', type: 'numbers' },
      ],
      theory: <Theory formulas={[String.raw`P^{(n)} = P^n,\quad \pi_j = \sum_i \pi_i p_{ij},\ \sum_j \pi_j = 1,\quad \mu_{ij} = 1 + \sum_{k \ne j} p_{ik}\mu_{kj}`]}><p>Rantai Markov memiliki sifat tanpa memori: state berikutnya hanya bergantung pada state sekarang. Rantai ergodik memiliki distribusi steady-state yang tidak bergantung pada state awal.</p></Theory>,
    },
    {
      id: 'absorbing', label: 'State penyerap', endpoint: '/markov/analyze',
      fields: [
        { key: 'matrix', label: 'Matriks transisi P', type: 'matrix', required: true },
        { key: 'names', label: 'Nama state (opsional)', type: 'labels' },
        { key: 'steps', label: 'n langkah', type: 'integer', default: '5' },
      ],
      theory: <Theory formulas={[String.raw`N = (I - Q)^{-1},\quad B = NR`]}><p>State penyerap (pᵢᵢ = 1) tidak dapat ditinggalkan. Matriks fundamental N memberi jumlah kunjungan harapan; B memberi peluang diserap di tiap state penyerap.</p></Theory>,
    },
    {
      id: 'ctmc', label: 'Waktu kontinu (CTMC)', endpoint: '/markov/ctmc',
      fields: [
        { key: 'rates', label: 'Matriks laju qᵢⱼ (diagonal diabaikan)', type: 'matrix', required: true },
        { key: 'names', label: 'Nama state (opsional)', type: 'labels' },
      ],
      theory: <Theory><p>Pada rantai Markov waktu kontinu, waktu tinggal di setiap state berdistribusi eksponensial. Steady-state diperoleh dari persamaan keseimbangan: laju keluar = laju masuk.</p></Theory>,
    },
  ],
}

export const queueConfig: VariantPageConfig = {
  title: 'Teori Antrian (Queueing Theory, Bab 17–18)',
  subtitle: 'M/M/s, M/M/s/K, populasi terbatas, M/G/1, M/D/s, M/Eₖ/s, prioritas, jaringan Jackson, dan jumlah server optimal.',
  exampleModule: 'or',
  variants: [
    { id: 'mms', label: 'M/M/s', endpoint: '/queue/mms', fields: [...lamMu, { key: 's', label: 'Jumlah server s', type: 'integer', default: '1' }], theory: queueTheory },
    { id: 'mmsk', label: 'M/M/s/K', endpoint: '/queue/mmsk', fields: [...lamMu, { key: 's', label: 'Jumlah server s', type: 'integer', default: '1' }, { key: 'k', label: 'Kapasitas sistem K', type: 'integer', required: true }], theory: queueTheory },
    { id: 'finite-source', label: 'Populasi terbatas', endpoint: '/queue/finite-source', fields: [{ key: 'lam', label: 'λ per anggota populasi', type: 'number', required: true }, { key: 'mu', label: 'μ per server', type: 'number', required: true }, { key: 's', label: 'Jumlah server s', type: 'integer', default: '1' }, { key: 'population', label: 'Ukuran populasi N', type: 'integer', required: true }], theory: queueTheory },
    { id: 'mg1', label: 'M/G/1', endpoint: '/queue/mg1', fields: [...lamMu, { key: 'sigma', label: 'σ waktu layanan', type: 'number', required: true }], theory: <Theory formulas={[String.raw`L_q = \frac{\lambda^2\sigma^2 + \rho^2}{2(1-\rho)}`]}><p>Rumus Pollaczek-Khintchine berlaku untuk sembarang distribusi waktu layanan.</p></Theory> },
    { id: 'mds', label: 'M/D/s & M/Eₖ/s', endpoint: '/queue/mgs', fields: [...lamMu, { key: 's', label: 'Jumlah server s', type: 'integer', default: '1' }, { key: 'model', label: 'Distribusi layanan', type: 'select', options: [{ value: 'MD', label: 'Konstan (D)' }, { value: 'MEk', label: 'Erlang-k (Eₖ)' }] }, { key: 'k', label: 'k (Erlang)', type: 'integer', default: '2', showIf: (r) => r.model === 'MEk' }], theory: queueTheory },
    { id: 'priority', label: 'Disiplin prioritas', endpoint: '/queue/priority', fields: [{ key: 'lam', label: 'λ tiap kelas (kelas 1 = prioritas tertinggi)', type: 'numbers', required: true }, { key: 'mu', label: 'μ', type: 'number', required: true }, { key: 's', label: 'Jumlah server', type: 'integer', default: '1' }, { key: 'preemptive', label: 'Preemptive', type: 'boolean', placeholder: 'Preemptive (pelayanan dapat disela)' }], theory: queueTheory },
    { id: 'jackson', label: 'Jaringan Jackson', endpoint: '/queue/jackson', fields: [{ key: 'external', label: 'Kedatangan eksternal tiap stasiun', type: 'numbers', required: true }, { key: 'routing', label: 'Matriks perutean pᵢⱼ', type: 'matrix', required: true }, { key: 'servers', label: 'Jumlah server tiap stasiun', type: 'numbers', required: true }, { key: 'mu', label: 'μ tiap stasiun', type: 'numbers', required: true }, { key: 'names', label: 'Nama stasiun (opsional)', type: 'labels' }], theory: queueTheory },
    { id: 'queue-cost', label: 'Optimasi biaya', endpoint: '/queue/cost', fields: [...lamMu, { key: 'server_cost', label: 'Biaya per server per satuan waktu', type: 'number', required: true }, { key: 'wait_cost', label: 'Biaya menunggu per pelanggan per satuan waktu', type: 'number', required: true }], theory: <Theory formulas={[String.raw`E[TC] = C_s s + C_w L`]}><p>Model keputusan Bab 18: pilih jumlah server yang meminimumkan biaya layanan + biaya menunggu.</p></Theory> },
  ],
}

export const inventoryConfig: VariantPageConfig = {
  title: 'Teori Persediaan (Inventory Theory, Bab 19)',
  subtitle: 'EOQ, backorder, diskon kuantitas, EPQ, Wagner-Whitin, (R, Q) stokastik, newsvendor, dan (s, S).',
  exampleModule: 'or',
  variants: [
    { id: 'eoq', label: 'EOQ', endpoint: '/inventory/eoq', fields: [{ key: 'demand', label: 'Laju permintaan d', type: 'number', required: true }, { key: 'setup', label: 'Biaya setup/pesan K', type: 'number', required: true }, { key: 'holding', label: 'Biaya simpan h per unit per satuan waktu', type: 'number', required: true }, { key: 'unit_cost', label: 'Harga per unit c', type: 'number', default: '0' }, { key: 'lead_time', label: 'Lead time (opsional)', type: 'number', default: '0' }], theory: <Theory formulas={[String.raw`Q^* = \sqrt{\frac{2dK}{h}}`]}><p>Model EOQ menyeimbangkan biaya pemesanan dan biaya penyimpanan.</p></Theory> },
    { id: 'eoq-backorder', label: 'EOQ + backorder', endpoint: '/inventory/eoq', fields: [{ key: 'demand', label: 'Laju permintaan d', type: 'number', required: true }, { key: 'setup', label: 'Biaya setup K', type: 'number', required: true }, { key: 'holding', label: 'Biaya simpan h', type: 'number', required: true }, { key: 'unit_cost', label: 'Harga per unit c', type: 'number', default: '0' }, { key: 'shortage', label: 'Biaya kekurangan p per unit per satuan waktu', type: 'number', required: true }], theory: <Theory formulas={[String.raw`Q^* = \sqrt{\frac{2dK}{h}}\sqrt{\frac{p+h}{p}}`]}><p>Kekurangan terencana diizinkan dan dipenuhi kemudian (backorder).</p></Theory> },
    { id: 'quantity-discount', label: 'Diskon kuantitas', endpoint: '/inventory/discount', fields: [{ key: 'demand', label: 'Permintaan d', type: 'number', required: true }, { key: 'setup', label: 'Biaya pesan K', type: 'number', required: true }, { key: 'holding_rate', label: 'Biaya simpan sebagai fraksi harga (i)', type: 'number', required: true }, { key: 'breaks', label: 'Tingkat harga: kuantitas_minimum harga', type: 'matrix', required: true, placeholder: '0 10\n100 9.5\n500 9' }], theory: <Theory><p>Bandingkan biaya total (termasuk biaya pembelian) pada setiap tingkat harga.</p></Theory> },
    { id: 'epq', label: 'EPQ', endpoint: '/inventory/epq', fields: [{ key: 'demand', label: 'Laju permintaan d', type: 'number', required: true }, { key: 'production_rate', label: 'Laju produksi r', type: 'number', required: true }, { key: 'setup', label: 'Biaya setup K', type: 'number', required: true }, { key: 'holding', label: 'Biaya simpan h', type: 'number', required: true }], theory: <Theory formulas={[String.raw`Q^* = \sqrt{\frac{2dK}{h(1 - d/r)}}`]}><p>Produksi bertahap: persediaan naik dengan laju r − d selama produksi.</p></Theory> },
    { id: 'wagner-whitin', label: 'Wagner-Whitin', endpoint: '/inventory/wagner-whitin', fields: [{ key: 'demands', label: 'Permintaan tiap periode', type: 'numbers', required: true }, { key: 'setup', label: 'Biaya setup K', type: 'number', required: true }, { key: 'holding', label: 'Biaya simpan per unit per periode', type: 'number', required: true }, { key: 'unit_cost', label: 'Biaya per unit (opsional)', type: 'number', default: '0' }], theory: <Theory><p>Model periodik deterministik diselesaikan dengan DP; produksi hanya saat persediaan nol.</p></Theory> },
    { id: 'rq', label: '(R, Q) stokastik', endpoint: '/inventory/rq', fields: [{ key: 'demand_rate', label: 'Laju permintaan rata-rata d', type: 'number', required: true }, { key: 'setup', label: 'Biaya pesan K', type: 'number', required: true }, { key: 'holding', label: 'Biaya simpan h', type: 'number', required: true }, { key: 'lead_mean', label: 'Rata-rata permintaan selama lead time', type: 'number', required: true }, { key: 'lead_sd', label: 'Simpangan baku permintaan selama lead time', type: 'number', required: true }, { key: 'service', label: 'Tingkat layanan', type: 'number', default: '0.95' }], theory: <Theory formulas={[String.raw`R = \mu_L + z\sigma_L`]}><p>Titik pemesanan kembali dengan stok pengaman untuk tingkat layanan tertentu.</p></Theory> },
    { id: 'newsvendor', label: 'Newsvendor', endpoint: '/inventory/newsvendor', fields: [{ key: 'price', label: 'Harga jual', type: 'number', required: true }, { key: 'cost', label: 'Biaya beli per unit', type: 'number', required: true }, { key: 'salvage', label: 'Nilai sisa per unit', type: 'number', default: '0' }, { key: 'shortage_penalty', label: 'Penalti kekurangan per unit', type: 'number', default: '0' }, { key: 'dist', label: 'Distribusi permintaan', type: 'select', options: [{ value: 'normal', label: 'Normal (μ, σ)' }, { value: 'uniform', label: 'Seragam (a, b)' }, { value: 'discrete', label: 'Diskrit (nilai, peluang, …)' }] }, { key: 'params', label: 'Parameter distribusi', type: 'numbers', required: true, placeholder: '100, 20' }], theory: <Theory formulas={[String.raw`F(Q^*) = \frac{c_u}{c_u + c_o}`]}><p>Model satu periode untuk barang mudah rusak: pesan sampai peluang permintaan ≤ Q sama dengan rasio kritis.</p></Theory> },
    { id: 'periodic-review', label: '(s, S) periodik', endpoint: '/inventory/periodic', fields: [{ key: 'demand_mean', label: 'Rata-rata permintaan per satuan waktu', type: 'number', required: true }, { key: 'demand_sd', label: 'Simpangan baku permintaan per satuan waktu', type: 'number', required: true }, { key: 'review', label: 'Periode peninjauan R', type: 'number', default: '1' }, { key: 'lead', label: 'Lead time L', type: 'number', default: '0' }, { key: 'setup', label: 'Biaya pesan K', type: 'number', required: true }, { key: 'holding', label: 'Biaya simpan h', type: 'number', required: true }, { key: 'service', label: 'Tingkat layanan', type: 'number', default: '0.95' }], theory: <Theory><p>Kebijakan (s, S): pesan sampai S bila posisi persediaan ≤ s saat peninjauan. Gunakan modul Simulasi untuk mengevaluasi biayanya.</p></Theory> },
  ],
}

export const forecastConfig: VariantPageConfig = {
  title: 'Peramalan (Forecasting, Bab 20)',
  subtitle: 'Last value, rata-rata bergerak, exponential smoothing, musiman, Holt, regresi, Box-Jenkins ARIMA, dan ukuran galat.',
  exampleModule: 'or',
  variants: [
    { id: 'last-value', label: 'Last value', endpoint: '/forecast/last-value', fields: [series, horizon], theory: <Theory><p>Ramalan = nilai terakhir. Pembanding paling sederhana.</p></Theory> },
    { id: 'moving-average', label: 'Rata-rata bergerak', endpoint: '/forecast/moving-average', fields: [series, { key: 'n', label: 'n periode', type: 'integer', default: '3' }, horizon], theory: <Theory><p>Rata-rata n periode terakhir; cocok untuk deret yang relatif stabil.</p></Theory> },
    { id: 'exp-smoothing', label: 'Exponential smoothing', endpoint: '/forecast/exp-smoothing', fields: [series, { key: 'alpha', label: 'α', type: 'number', default: '0.3' }, { key: 'initial', label: 'Ramalan awal (opsional)', type: 'number' }, horizon], theory: <Theory formulas={[String.raw`F_{t+1} = \alpha y_t + (1-\alpha)F_t`]}><p>α besar → respons cepat terhadap perubahan; α kecil → ramalan lebih halus.</p></Theory> },
    { id: 'holt', label: 'Holt (tren)', endpoint: '/forecast/holt', fields: [series, { key: 'alpha', label: 'α', type: 'number', default: '0.3' }, { key: 'beta', label: 'β', type: 'number', default: '0.3' }, horizon], theory: <Theory><p>Exponential smoothing dengan komponen tren yang diperbarui terpisah.</p></Theory> },
    { id: 'seasonal', label: 'Penyesuaian musiman', endpoint: '/forecast/seasonal', fields: [series, { key: 'season', label: 'Panjang musim', type: 'integer', default: '4' }, { key: 'method', label: 'Metode dasar', type: 'select', options: [{ value: 'smoothing', label: 'Exponential smoothing' }, { value: 'last', label: 'Last value' }] }, { key: 'alpha', label: 'α', type: 'number', default: '0.3' }, horizon], theory: <Theory><p>Hilangkan pola musiman dengan faktor musiman, ramalkan deret tersesuaikan, lalu kembalikan faktor musimnya.</p></Theory> },
    { id: 'trend-regression', label: 'Regresi linier', endpoint: '/forecast/regression', fields: [series, { key: 'x', label: 'Variabel penjelas x (opsional; kosong = tren waktu)', type: 'numbers' }, { key: 'future_x', label: 'Nilai x untuk diramal (opsional)', type: 'numbers' }, horizon], theory: <Theory><p>Regresi linier kausal: y diramal dari variabel penjelas x atau dari waktu (tren).</p></Theory> },
    { id: 'arima', label: 'Box-Jenkins ARIMA', endpoint: '/forecast/arima', fields: [series, { key: 'p', label: 'p (AR)', type: 'integer', default: '1' }, { key: 'd', label: 'd (diferensiasi)', type: 'integer', default: '0' }, { key: 'q', label: 'q (MA)', type: 'integer', default: '0' }, horizon], theory: <Theory><p>Metode Box-Jenkins: identifikasi (ACF/PACF), estimasi parameter, diagnostik residual, lalu peramalan.</p></Theory> },
  ],
}

export const mdpConfig: VariantPageConfig = {
  title: 'Proses Keputusan Markov (MDP, Bab 21)',
  subtitle: 'Formulasi MDP, solusi dengan LP, policy improvement, dan value iteration dengan diskon.',
  exampleModule: 'or',
  variants: [
    { id: 'policy-improvement', label: 'Policy improvement', endpoint: '/mdp/policy-improvement', fields: [{ key: 'mdp', label: 'Data MDP', type: 'textarea', required: true, hint: MDP_HINT }, { key: 'discount', label: 'Faktor diskon α (kosong = biaya rata-rata jangka panjang)', type: 'number' }], theory: <Theory formulas={[String.raw`g + v_i = C_{ik} + \sum_j p_{ij}(k)v_j`]}><p>Bergantian antara penentuan nilai kebijakan dan perbaikan kebijakan sampai kebijakan tidak berubah.</p></Theory> },
    { id: 'value-iteration', label: 'Value iteration', endpoint: '/mdp/value-iteration', fields: [{ key: 'mdp', label: 'Data MDP', type: 'textarea', required: true, hint: MDP_HINT }, { key: 'discount', label: 'Faktor diskon α', type: 'number', default: '0.9' }, { key: 'iterations', label: 'Iterasi maksimum', type: 'integer', default: '200' }, { key: 'tol', label: 'Toleransi', type: 'number', default: '0.000001' }], theory: <Theory><p>Successive approximations dengan faktor diskon konvergen ke nilai optimal.</p></Theory> },
    { id: 'mdp-lp', label: 'Formulasi LP', endpoint: '/mdp/lp', fields: [{ key: 'mdp', label: 'Data MDP', type: 'textarea', required: true, hint: MDP_HINT }], theory: <Theory><p>Variabel yᵢₖ = peluang steady-state berada di state i dan memilih keputusan k; solusi basis optimal memberi kebijakan deterministik.</p></Theory> },
  ],
}

export const simulationConfig: VariantPageConfig = {
  title: 'Simulasi (Simulation, Bab 22)',
  subtitle: 'LCG, inverse transform, acceptance-rejection, Monte Carlo, simulasi antrian & persediaan, reduksi variansi, dan interval kepercayaan.',
  exampleModule: 'or',
  variants: [
    { id: 'lcg', label: 'Bilangan acak (LCG)', endpoint: '/simulation/lcg', fields: [{ key: 'a', label: 'Pengali a', type: 'integer', required: true }, { key: 'c', label: 'Penambah c', type: 'integer', required: true }, { key: 'm', label: 'Modulus m', type: 'integer', required: true }, { key: 'seed', label: 'Seed x₀', type: 'integer', required: true }, { key: 'n', label: 'Jumlah bilangan', type: 'integer', default: '20' }], theory: <Theory formulas={[String.raw`x_{n+1} = (ax_n + c) \bmod m`]}><p>Bilangan acak semu: deterministik tetapi lolos uji statistik keseragaman.</p></Theory> },
    { id: 'inverse-transform', label: 'Inverse transform', endpoint: '/simulation/variates', fields: [{ key: 'method', label: 'Metode', type: 'select', default: 'inverse', options: [{ value: 'inverse', label: 'Inverse transform' }] }, { key: 'dist', label: 'Distribusi', type: 'select', options: [{ value: 'exponential', label: 'Eksponensial (λ)' }, { value: 'uniform', label: 'Seragam (a, b)' }, { value: 'triangular', label: 'Segitiga (a, mode, b)' }, { value: 'discrete', label: 'Diskrit (x1, p1, …)' }] }, { key: 'params', label: 'Parameter', type: 'numbers', required: true }, { key: 'n', label: 'Jumlah sampel', type: 'integer', default: '1000' }, { key: 'seed', label: 'Seed', type: 'integer', default: '1' }], theory: <Theory formulas={[String.raw`x = F^{-1}(u)`]}><p>Ubah bilangan acak seragam menjadi variabel acak dengan distribusi yang diinginkan.</p></Theory> },
    { id: 'acceptance-rejection', label: 'Acceptance-rejection', endpoint: '/simulation/variates', fields: [{ key: 'method', label: 'Metode', type: 'select', default: 'rejection', options: [{ value: 'rejection', label: 'Acceptance-rejection' }] }, { key: 'pdf', label: 'f(x)', type: 'text', required: true, hint: FUNC_HINT }, { key: 'lower', label: 'Batas bawah', type: 'number', required: true }, { key: 'upper', label: 'Batas atas', type: 'number', required: true }, { key: 'n', label: 'Jumlah sampel', type: 'integer', default: '1000' }, { key: 'seed', label: 'Seed', type: 'integer', default: '1' }], theory: <Theory><p>Bangkitkan kandidat seragam, terima dengan peluang f(x)/M. Berguna bila F⁻¹ sulit dihitung.</p></Theory> },
    { id: 'monte-carlo', label: 'Monte Carlo', endpoint: '/simulation/monte-carlo', fields: [{ key: 'variables', label: 'Variabel acak (satu per baris)', type: 'textarea', required: true, placeholder: 'D ~ normal(100, 15)\nP ~ uniform(8, 12)', hint: 'Distribusi: normal, uniform, exponential, poisson, triangular, binomial, constant.' }, { key: 'output', label: 'Ekspresi output', type: 'text', required: true, placeholder: 'D*P - 600' }, { key: 'n', label: 'Jumlah replikasi', type: 'integer', default: '10000' }, { key: 'seed', label: 'Seed', type: 'integer', default: '1' }, { key: 'antithetic', label: 'Antithetic', type: 'boolean', placeholder: 'Bandingkan dengan antithetic variates (reduksi variansi)' }], theory: <Theory><p>Estimasi nilai harapan dengan replikasi acak; interval kepercayaan menyatakan ketelitian estimasi.</p></Theory> },
    { id: 'queue-simulation', label: 'Simulasi antrian', endpoint: '/simulation/queue', fields: [...lamMu, { key: 's', label: 'Jumlah server', type: 'integer', default: '1' }, { key: 'customers', label: 'Pelanggan per replikasi', type: 'integer', default: '2000' }, { key: 'replications', label: 'Replikasi', type: 'integer', default: '20' }, { key: 'seed', label: 'Seed', type: 'integer', default: '1' }], theory: <Theory><p>Simulasi kejadian diskret; hasil dibandingkan dengan rumus M/M/s.</p></Theory> },
    { id: 'inventory-simulation', label: 'Simulasi persediaan', endpoint: '/simulation/inventory', fields: [{ key: 'small_s', label: 's', type: 'number', required: true }, { key: 'big_s', label: 'S', type: 'number', required: true }, { key: 'demand_values', label: 'Nilai permintaan', type: 'numbers', required: true }, { key: 'demand_probs', label: 'Peluang permintaan', type: 'numbers', required: true }, { key: 'periods', label: 'Periode per replikasi', type: 'integer', default: '100' }, { key: 'replications', label: 'Replikasi', type: 'integer', default: '20' }, { key: 'order_cost', label: 'Biaya pesan', type: 'number', default: '0' }, { key: 'unit_cost', label: 'Biaya per unit', type: 'number', default: '0' }, { key: 'holding', label: 'Biaya simpan per unit', type: 'number', default: '0' }, { key: 'shortage', label: 'Penalti kekurangan per unit', type: 'number', default: '0' }, { key: 'seed', label: 'Seed', type: 'integer', default: '1' }], theory: <Theory><p>Evaluasi biaya rata-rata kebijakan (s, S) dengan permintaan acak.</p></Theory> },
  ],
}

export const appendixConfig: VariantPageConfig = {
  title: 'Konveksitas, Optimasi Klasik & Matriks (Appendix)',
  subtitle: 'Uji konveksitas lewat Hessian, titik stasioner & pengali Lagrange, serta kalkulator matriks.',
  exampleModule: 'or',
  variants: [
    { id: 'convexity', label: 'Konveksitas', endpoint: '/appendix/convexity', fields: [{ key: 'func', label: 'f(x)', type: 'text', required: true, hint: FUNC_HINT }, { key: 'lower', label: 'Batas bawah tiap variabel', type: 'numbers', required: true }, { key: 'upper', label: 'Batas atas tiap variabel', type: 'numbers', required: true }], theory: <Theory><p>f konveks bila Hessian semidefinit positif; konkaf bila semidefinit negatif.</p></Theory> },
    { id: 'classical-optimization', label: 'Optimasi klasik / Lagrange', endpoint: '/appendix/classical', fields: [{ key: 'func', label: 'f(x)', type: 'text', required: true, hint: FUNC_HINT }, { key: 'constraints', label: 'Kendala persamaan (opsional, satu per baris)', type: 'textarea', placeholder: 'x1 + x2 = 10' }, { key: 'search_lo', label: 'Rentang pencarian bawah', type: 'number', default: '-10' }, { key: 'search_hi', label: 'Rentang pencarian atas', type: 'number', default: '10' }], theory: <Theory formulas={[String.raw`\nabla f = \sum_i \lambda_i \nabla g_i,\quad g_i(\mathbf{x}) = b_i`]}><p>Titik stasioner tanpa kendala: ∇f = 0. Dengan kendala persamaan: metode pengali Lagrange.</p></Theory> },
    { id: 'matrix', label: 'Kalkulator matriks', endpoint: '/appendix/matrix', fields: [{ key: 'operation', label: 'Operasi', type: 'select', default: 'inverse', options: [{ value: 'inverse', label: 'Invers' }, { value: 'determinant', label: 'Determinan' }, { value: 'eigen', label: 'Nilai & vektor eigen' }, { value: 'multiply', label: 'Perkalian AB' }, { value: 'transpose', label: 'Transpose' }] }, { key: 'a', label: 'Matriks A', type: 'matrix', required: true }, { key: 'b', label: 'Matriks B', type: 'matrix', showIf: (r) => r.operation === 'multiply' }], theory: <Theory><p>Operasi matriks dasar yang dipakai di seluruh buku (mis. B⁻¹ pada simpleks direvisi). Determinan dan invers ditampilkan dengan langkah eliminasi Gauss(-Jordan) dalam pecahan eksak.</p></Theory> },
  ],
}
