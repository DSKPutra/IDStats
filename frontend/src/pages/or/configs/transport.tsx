import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from '@/pages/stats/configs/Theory'

export const transportConfig: VariantPageConfig = {
  title: 'Transportasi & Penugasan (Bab 8)',
  subtitle: 'Solusi awal NWC, biaya terkecil, Vogel (VAM); optimasi MODI/stepping stone; metode Hungaria.',
  exampleModule: 'or',
  variants: [
    {
      id: 'transportation',
      label: 'Masalah transportasi',
      endpoint: '/transport/transportation',
      fields: [
        { key: 'costs', label: 'Matriks biaya per unit (baris = sumber, kolom = tujuan)', type: 'matrix', required: true, placeholder: '464 513 654 867\n352 416 690 791\n995 682 388 685' },
        { key: 'supply', label: 'Penawaran tiap sumber', type: 'numbers', required: true, placeholder: '75, 125, 100' },
        { key: 'demand', label: 'Permintaan tiap tujuan', type: 'numbers', required: true, placeholder: '80, 65, 70, 85' },
        { key: 'sources', label: 'Nama sumber (opsional)', type: 'labels' },
        { key: 'destinations', label: 'Nama tujuan (opsional)', type: 'labels' },
        { key: 'method', label: 'Metode solusi awal', type: 'select', default: 'vam', options: [{ value: 'vam', label: 'Aproksimasi Vogel (VAM)' }, { value: 'least_cost', label: 'Biaya terkecil' }, { value: 'nwc', label: 'Pojok Barat Laut (NWC)' }] },
        { key: 'optimize', label: 'Optimasi', type: 'boolean', default: 'true', placeholder: 'Lanjutkan ke solusi optimal dengan metode MODI' },
      ],
      theory: (
        <Theory formulas={[String.raw`\min \sum_i\sum_j c_{ij}x_{ij}\quad\text{s.t.}\quad \sum_j x_{ij} = s_i,\ \sum_i x_{ij} = d_j,\ x_{ij}\ge 0`]}>
          <p>
            Tabel transportasi memiliki m + n − 1 sel basis. VAM biasanya memberi solusi awal paling dekat dengan optimum.
            Metode MODI menghitung uᵢ + vⱼ = cᵢⱼ pada sel basis; sel nonbasis dengan Δᵢⱼ = cᵢⱼ − uᵢ − vⱼ &lt; 0 dapat menurunkan
            biaya dan dimasukkan lewat lintasan tertutup (stepping stone).
          </p>
        </Theory>
      ),
    },
    {
      id: 'assignment',
      label: 'Penugasan (Hungaria)',
      endpoint: '/transport/assignment',
      fields: [
        { key: 'costs', label: 'Matriks biaya (baris = pekerja/mesin, kolom = tugas/lokasi)', type: 'matrix', required: true, placeholder: '13 16 12 11\n15 99 13 20\n5 7 10 6' },
        { key: 'rows', label: 'Nama baris (opsional)', type: 'labels' },
        { key: 'cols', label: 'Nama kolom (opsional)', type: 'labels' },
        { key: 'maximize', label: 'Maksimasi', type: 'boolean', placeholder: 'Maksimumkan (mis. keuntungan), bukan minimumkan biaya' },
      ],
      theory: (
        <Theory>
          <p>
            Metode Hungaria: reduksi baris dan kolom, lalu tutup semua nol dengan garis sesedikit mungkin. Bila jumlah garis
            &lt; n, kurangkan elemen terkecil yang tidak tertutup dari elemen tak tertutup dan tambahkan ke perpotongan garis.
            Gunakan biaya sangat besar (mis. 99) untuk penugasan yang tidak diizinkan.
          </p>
        </Theory>
      ),
    },
  ],
}
