import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const TAXONOMY = [
  {
    title: 'Optimizer berbasis gradien',
    color: 'border-indigo-400',
    groups: [
      { name: 'Dasar', items: ['SGD', 'SGD + Momentum'] },
      { name: 'Adaptif (keluarga Adam)', items: ['AdamW', 'AdamP', 'Adai', 'NAdam', 'Adamax', 'AMSGrad', 'RAdam', 'QHAdam'] },
      { name: 'Layer-wise / batch besar', items: ['LAMB', 'NovoGrad'] },
      { name: 'Berbasis tanda', items: ['LION'] },
      { name: 'Pembungkus', items: ['Lookahead'] },
    ],
    link: '/ml/gradient-playground',
  },
  {
    title: 'Metaheuristik berbasis populasi',
    color: 'border-amber-400',
    groups: [
      { name: 'Terinspirasi hewan', items: ['NOA', 'HHO', 'AVOA', 'IARO'] },
      { name: 'Matematika / fisika', items: ['EDO', 'AOA'] },
      { name: 'Evolution strategy', items: ['CMA-ES', 'LM-MA'] },
      { name: 'Pembanding klasik', items: ['PSO', 'GA', 'DE', 'SA'] },
    ],
    link: '/ml/metaheuristics',
  },
  {
    title: 'Bidang aplikasi',
    color: 'border-emerald-400',
    groups: [
      { name: 'Machine learning', items: ['Optimasi hyperparameter', 'Seleksi fitur', 'Pelatihan model'] },
      { name: 'Riset operasi', items: ['TSP', 'Knapsack', 'Penjadwalan'] },
      { name: 'Pengambilan keputusan berurutan', items: ['Reinforcement learning'] },
    ],
    link: '/ml/hyperparameter-optimization',
  },
]

const COMPARISON = [
  ['SGD / Momentum', 'Sederhana, generalisasi baik, memori kecil', 'Sensitif terhadap learning rate, lambat di lembah sempit'],
  ['AdamW', 'Konvergen cepat, weight decay terpisah sehingga regularisasi efektif', 'Memori 2× parameter; kadang generalisasi kalah dari SGD'],
  ['AdamP', 'Mencegah pertumbuhan norma bobot pada lapisan invarian skala', 'Tambahan komputasi proyeksi; manfaat terbatas tanpa normalisasi'],
  ['Adai', 'Inersia adaptif membantu lolos dari titik pelana, memilih minimum datar', 'Hiperparameter β₀ perlu disetel; belum banyak diuji luas'],
  ['NAdam', 'Momentum Nesterov memberi langkah “melihat ke depan”', 'Perbaikan atas Adam bersifat kecil pada banyak tugas'],
  ['LION', 'Hanya menyimpan momentum (hemat memori), langkah berbasis tanda', 'Butuh learning rate jauh lebih kecil; sensitif terhadap ukuran batch'],
  ['Lookahead', 'Mengurangi variansi, stabil, dapat membungkus optimizer apa pun', 'Menambah hiperparameter k dan α; konvergensi awal bisa lebih lambat'],
  ['NovoGrad / LAMB', 'Normalisasi per lapisan stabil untuk batch sangat besar', 'Keunggulan terutama pada model dan batch besar'],
  ['AMSGrad / RAdam', 'Memperbaiki masalah konvergensi/variansi awal Adam', 'Dalam praktik selisih dengan Adam sering kecil'],
  ['HHO / AVOA / NOA', 'Mekanisme eksplorasi–eksploitasi yang kaya; tanpa gradien', 'Banyak parameter acak; hasil bervariasi antarrun'],
  ['EDO / AOA', 'Sederhana dan cepat; sedikit parameter', 'Dapat konvergen prematur pada fungsi multimodal'],
  ['CMA-ES / LM-MA', 'Sangat kuat pada fungsi kontinu ill-conditioned; invarian rotasi', 'CMA-ES O(d²) memori; LM-MA lebih lambat beradaptasi untuk d kecil'],
]

const CHALLENGES = [
  { title: 'Skalabilitas', text: 'Model dan data yang makin besar menuntut optimizer yang hemat memori, dapat diparalelkan, dan stabil pada batch besar.' },
  { title: 'Sensitivitas hiperparameter', text: 'Kinerja sangat bergantung pada learning rate, β, ukuran populasi, dan sebagainya; diperlukan metode yang lebih tangguh atau penyetelan otomatis.' },
  { title: 'Teori vs praktik', text: 'Banyak jaminan konvergensi hanya berlaku untuk masalah konveks, sedangkan pelatihan jaringan saraf bersifat nonkonveks.' },
  { title: 'Generalisasi', text: 'Konvergen cepat pada data latih belum tentu memberi kinerja baik pada data uji; hubungan antara ketajaman minimum dan generalisasi masih diteliti.' },
  { title: 'Evaluasi yang adil', text: 'Perbandingan metaheuristik membutuhkan banyak run, anggaran evaluasi yang sama, dan uji statistik — bukan hanya satu angka terbaik.' },
  { title: 'Hibridisasi', text: 'Menggabungkan optimizer gradien dengan metaheuristik, atau metaheuristik dengan model pengganti (surrogate), merupakan arah yang menjanjikan.' },
]

export function MlReviewPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Tinjauan: Optimasi untuk Machine Learning</h1>
        <p className="mt-1 text-muted-foreground">
          Ringkasan taksonomi, perbandingan metode, serta tantangan dan arah riset berdasarkan <em>Recent Advances in Optimization
          Methods for Machine Learning: A Systematic Review</em> (Liu et al., Mathematics 2025, 13, 2210). Setiap metode dapat
          dicoba langsung di modul terkait.
        </p>
      </div>

      <section aria-labelledby="taksonomi">
        <h2 id="taksonomi" className="mb-3 text-lg font-semibold">Taksonomi metode</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {TAXONOMY.map((t) => (
            <Card key={t.title} className={`border-t-4 ${t.color}`}>
              <CardHeader>
                <CardTitle>{t.title}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm">
                {t.groups.map((g) => (
                  <div key={g.name}>
                    <p className="font-medium">{g.name}</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {g.items.map((i) => (
                        <span key={i} className="rounded-full bg-muted px-2 py-0.5 text-xs">
                          {i}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
                <Link to={t.link} className="mt-1 inline-flex items-center gap-1 text-primary hover:underline">
                  Coba di IDStats <ArrowRight className="size-4" />
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="perbandingan">
        <h2 id="perbandingan" className="mb-3 text-lg font-semibold">Kelebihan & kekurangan</h2>
        <div className="overflow-x-auto rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Metode</th>
                <th className="px-3 py-2 text-left font-medium">Kelebihan</th>
                <th className="px-3 py-2 text-left font-medium">Kekurangan</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map(([m, plus, minus]) => (
                <tr key={m} className="border-t align-top">
                  <td className="px-3 py-2 font-medium">{m}</td>
                  <td className="px-3 py-2">{plus}</td>
                  <td className="px-3 py-2 text-muted-foreground">{minus}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="tantangan">
        <h2 id="tantangan" className="mb-3 text-lg font-semibold">Tantangan & arah riset</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {CHALLENGES.map((c) => (
            <div key={c.title} className="rounded-xl border bg-card p-4">
              <h3 className="font-semibold">{c.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{c.text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
