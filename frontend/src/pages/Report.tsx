import { Printer } from 'lucide-react'
import { useEffect } from 'react'
import { ChartView } from '@/components/solver/ChartView'
import { ResultView } from '@/components/solver/ResultView'
import { StepsView } from '@/components/solver/StepsView'
import { Button } from '@/components/ui/button'
import { readReport } from '@/lib/report'

function formatInput(input: Record<string, unknown>) {
  return Object.entries(input).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)])
}

/** Laporan siap cetak: input, hasil, langkah, dan grafik. Gunakan “Simpan sebagai PDF” pada dialog cetak. */
export function ReportPage() {
  const report = readReport()
  useEffect(() => {
    document.documentElement.classList.remove('dark')
    if (!report) return
    const timer = window.setTimeout(() => window.print(), 2500) // beri waktu Plotly & KaTeX merender
    return () => window.clearTimeout(timer)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (!report) {
    return <p className="p-10 text-center">Tidak ada data laporan. Jalankan perhitungan lalu klik “Laporan PDF”.</p>
  }
  return (
    <div className="mx-auto max-w-4xl bg-white p-8 text-black print:p-0">
      <div className="mb-6 flex items-start justify-between gap-4 border-b pb-4">
        <div>
          <p className="eyebrow">IDStats — Modelling &amp; Optimization</p>
          <h1 className="text-2xl font-semibold">{report.pageTitle}</h1>
          <p className="text-gray-600">{report.variantLabel}</p>
          <p className="text-xs text-gray-500">Dibuat {new Date(report.createdAt).toLocaleString('id-ID')}</p>
        </div>
        <Button className="print:hidden" onClick={() => window.print()}>
          <Printer /> Cetak / Simpan PDF
        </Button>
      </div>
      <section className="mb-6 break-inside-avoid">
        <h2 className="mb-2 text-lg font-semibold">1. Input</h2>
        <table className="w-full border text-sm">
          <tbody>
            {formatInput(report.input).map(([k, v]) => (
              <tr key={k} className="border-t align-top">
                <th className="w-48 bg-gray-50 px-3 py-1.5 text-left font-medium">{k}</th>
                <td className="whitespace-pre-wrap break-all px-3 py-1.5 font-mono text-xs">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">2. Hasil</h2>
        <ResultView response={report.response} name={report.variantLabel} />
      </section>
      {report.response.steps.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2 text-lg font-semibold">3. Langkah penyelesaian</h2>
          <StepsView steps={report.response.steps} />
        </section>
      )}
      {report.response.charts.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2 text-lg font-semibold">4. Visualisasi</h2>
          <ChartView charts={report.response.charts.map((c) => ({ ...c, spec: { ...c.spec, frames: undefined } }))} />
        </section>
      )}
      <footer className="mt-10 border-t pt-4 text-xs text-gray-500">
        <span className="streak mb-4" aria-hidden="true" />
        <div className="flex items-center justify-between gap-4">
          <img src="/brand/logo-horizontal.jpg" alt="Dea Saka Kurnia Putra" className="h-12 w-auto mix-blend-multiply" />
          <p>© {new Date(report.createdAt).getFullYear()} Dea Saka Kurnia Putra. Hak cipta dilindungi undang-undang.</p>
        </div>
      </footer>
    </div>
  )
}
