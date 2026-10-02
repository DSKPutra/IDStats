import { ArrowRight, ClipboardList, FlaskConical, Lightbulb, Rocket, Search, Sigma } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Latex } from '@/components/solver/Latex'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const PHASES = [
  { icon: Search, title: 'Definisikan masalah & kumpulkan data', text: 'Tentukan tujuan, alternatif keputusan, batasan, dan pihak yang berkepentingan. Kumpulkan data yang relevan.' },
  { icon: Sigma, title: 'Formulasikan model matematis', text: 'Nyatakan keputusan sebagai variabel, ukuran kinerja sebagai fungsi tujuan, dan batasan sebagai kendala.' },
  { icon: Lightbulb, title: 'Kembangkan prosedur solusi', text: 'Pilih algoritma (mis. simpleks) atau heuristik untuk mencari solusi optimal / cukup baik, lengkap dengan analisis pasca-optimal.' },
  { icon: FlaskConical, title: 'Uji model (validasi)', text: 'Bandingkan hasil model dengan kondisi nyata atau data historis (retrospective test); perbaiki model bila perlu.' },
  { icon: ClipboardList, title: 'Siapkan penerapan berkelanjutan', text: 'Bangun sistem pendukung keputusan agar model dapat dipakai berulang dengan data terbaru.' },
  { icon: Rocket, title: 'Implementasi', text: 'Terapkan hasil di organisasi, latih pengguna, pantau kinerja, dan umpan balik untuk revisi model.' },
]

export function OrIntroPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Pengantar & Pendekatan Pemodelan OR (Bab 1–2)</h1>
        <p className="mt-1 text-muted-foreground">
          Riset Operasi (Operations Research) adalah penerapan metode ilmiah untuk mengambil keputusan terbaik dalam
          mengoperasikan sistem dengan sumber daya terbatas.
        </p>
      </div>

      <section aria-labelledby="alur">
        <h2 id="alur" className="mb-3 text-lg font-semibold">Alur pemodelan OR</h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {PHASES.map((p, i) => (
            <li key={p.title} className="relative rounded-xl border bg-card p-4">
              <div className="flex items-center gap-2">
                <span className="flex size-7 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">{i + 1}</span>
                <p.icon className="size-4 text-primary" aria-hidden />
              </div>
              <h3 className="mt-2 font-semibold">{p.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{p.text}</p>
            </li>
          ))}
        </ol>
        <p className="mt-2 text-sm text-muted-foreground">Fase-fase ini bersifat iteratif: hasil uji dan implementasi sering mengharuskan kembali ke fase sebelumnya.</p>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Contoh: dari masalah nyata ke model</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm leading-relaxed">
          <p>
            <strong>Wyndor Glass Co.</strong> ingin meluncurkan pintu kaca (x₁ batch/minggu) dan jendela (x₂). Keuntungan per
            batch 3 dan 5 (ribu dolar). Pabrik 1, 2, 3 masing-masing punya sisa kapasitas 4, 12, 18 jam/minggu.
          </p>
          <Latex block>{String.raw`\begin{aligned}&\max\ Z = 3x_1 + 5x_2\\ &x_1 \le 4 \quad(\text{pabrik 1})\\ &2x_2 \le 12 \quad(\text{pabrik 2})\\ &3x_1 + 2x_2 \le 18 \quad(\text{pabrik 3})\\ &x_1, x_2 \ge 0\end{aligned}`}</Latex>
          <div className="flex flex-wrap gap-2">
            <Link to="/or/lp-graphical" className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 hover:bg-muted">
              Selesaikan dengan metode grafik <ArrowRight className="size-4" />
            </Link>
            <Link to="/or/simplex" className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 hover:bg-muted">
              Selesaikan dengan simpleks <ArrowRight className="size-4" />
            </Link>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Konsep penting</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm leading-relaxed">
            <li><strong>Model deterministik vs stokastik</strong> — LP, IP, NLP (Bab 3–13) mengasumsikan parameter pasti; Bab 15–22 menangani ketidakpastian.</li>
            <li><strong>Solusi optimal vs memuaskan (satisficing)</strong> — dalam praktik, solusi yang cukup baik dan cepat sering lebih berguna.</li>
            <li><strong>Analisis pasca-optimal</strong> — analisis sensitivitas dan what-if untuk memahami ketangguhan solusi.</li>
            <li><strong>Validasi model</strong> — model yang valid memprediksi dampak relatif keputusan alternatif dengan cukup akurat.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
