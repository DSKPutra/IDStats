import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from '@/pages/stats/configs/Theory'

const PARK = 'O A 2\nO B 5\nO C 4\nA B 2\nA D 7\nB C 1\nB D 4\nB E 3\nC E 4\nD E 1\nD T 5\nE T 7'
const ARCS = 'A B 2 10\nA C 4 inf\nA D 9 inf\nB C 3 inf\nC E 1 80\nD E 3 inf\nE D 2 inf'
const flowFields = [
  { key: 'arcs', label: 'Busur: asal tujuan biaya kapasitas', type: 'graph' as const, graphValues: 2, graphDirected: true, required: true, placeholder: ARCS, hint: 'Kapasitas “inf” = tak terbatas.' },
  { key: 'supplies', label: 'Penawaran (+) / permintaan (−) node', type: 'textarea' as const, required: true, placeholder: 'A 50\nB 40\nD -30\nE -60' },
]

export const networkConfig: VariantPageConfig = {
  title: 'Optimasi Jaringan (Network Optimization, Bab 9)',
  subtitle: 'Lintasan terpendek, pohon rentang minimum, aliran maksimum, aliran biaya minimum, dan simpleks jaringan dengan editor graf visual.',
  exampleModule: 'or',
  variants: [
    {
      id: 'shortest-path',
      label: 'Lintasan terpendek',
      endpoint: '/network/shortest-path',
      fields: [
        { key: 'edges', label: 'Busur: node node jarak', type: 'graph', graphValues: 1, graphDirected: (r) => r.directed === 'true', required: true, placeholder: PARK },
        { key: 'source', label: 'Node asal', type: 'text', required: true, placeholder: 'O' },
        { key: 'target', label: 'Node tujuan', type: 'text', required: true, placeholder: 'T' },
        { key: 'directed', label: 'Berarah', type: 'boolean', placeholder: 'Busur berarah (satu arah)' },
      ],
      theory: (
        <Theory>
          <p>
            Algoritma Bab 9.3 (setara Dijkstra): pada iterasi ke-n, cari node terdekat ke-n dari asal di antara tetangga
            node-node yang sudah terpecahkan. Berlaku untuk jarak nonnegatif.
          </p>
        </Theory>
      ),
    },
    {
      id: 'minimum-spanning-tree',
      label: 'Pohon rentang minimum',
      endpoint: '/network/minimum-spanning-tree',
      fields: [
        { key: 'edges', label: 'Busur: node node panjang', type: 'graph', graphValues: 1, required: true, placeholder: PARK },
        { key: 'algorithm', label: 'Algoritma', type: 'select', options: [{ value: 'prim', label: 'Prim (Bab 9.4)' }, { value: 'kruskal', label: 'Kruskal' }] },
      ],
      theory: (
        <Theory>
          <p>
            Pohon rentang minimum menghubungkan semua n node dengan n − 1 busur dan total panjang terkecil, tanpa siklus.
            Prim menumbuhkan satu pohon dari node awal; Kruskal memilih busur terpendek secara global selama tidak membentuk siklus.
          </p>
        </Theory>
      ),
    },
    {
      id: 'max-flow',
      label: 'Aliran maksimum',
      endpoint: '/network/max-flow',
      fields: [
        { key: 'edges', label: 'Busur berarah: asal tujuan kapasitas', type: 'graph', graphValues: 1, graphDirected: true, required: true, placeholder: 'O A 5\nO B 7\nO C 4\nA B 1\nA D 3\nB C 2\nB D 4\nB E 5\nC E 4\nD T 9\nE D 1\nE T 6' },
        { key: 'source', label: 'Sumber (source)', type: 'text', required: true, placeholder: 'O' },
        { key: 'sink', label: 'Tujuan (sink)', type: 'text', required: true, placeholder: 'T' },
      ],
      theory: (
        <Theory>
          <p>
            Algoritma lintasan augmentasi (Ford-Fulkerson): selama ada lintasan dari sumber ke tujuan di jaringan residual,
            alirkan sebesar kapasitas residual terkecilnya. Teorema max-flow min-cut: aliran maksimum = kapasitas potongan minimum.
          </p>
        </Theory>
      ),
    },
    {
      id: 'min-cost-flow',
      label: 'Aliran biaya minimum',
      endpoint: '/network/min-cost-flow',
      fields: flowFields,
      theory: (
        <Theory formulas={[String.raw`\min \sum c_{ij}x_{ij}\quad\text{s.t.}\quad \sum_j x_{ij} - \sum_j x_{ji} = b_i,\ 0 \le x_{ij} \le u_{ij}`]}>
          <p>
            Masalah aliran biaya minimum mencakup transportasi, penugasan, lintasan terpendek, dan aliran maksimum sebagai kasus
            khusus. Metode successive shortest path mengirim aliran berturut-turut lewat lintasan termurah di jaringan residual.
          </p>
        </Theory>
      ),
    },
    {
      id: 'network-simplex',
      label: 'Simpleks jaringan',
      endpoint: '/network/network-simplex',
      fields: flowFields,
      theory: (
        <Theory>
          <p>
            Simpleks jaringan adalah metode simpleks yang memanfaatkan struktur jaringan: solusi basis = pohon rentang.
            Busur nonbasis dengan biaya tereduksi negatif masuk, membentuk siklus; aliran digeser di siklus itu hingga satu busur
            keluar. Jauh lebih cepat daripada simpleks umum.
          </p>
        </Theory>
      ),
    },
  ],
}
