import { Printer } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import { ChartView } from '@/components/solver/ChartView'
import { ResultView } from '@/components/solver/ResultView'
import { StepsView } from '@/components/solver/StepsView'
import { Button } from '@/components/ui/button'
import { readReport } from '@/lib/report'

const COPYRIGHT = 'Dea Saka Kurnia Putra. Hak cipta dilindungi undang-undang.'

function formatInput(input: Record<string, unknown>) {
  return Object.entries(input).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)])
}

function Section({ no, title, children, avoidBreak = false }: { no: string; title: string; children: ReactNode; avoidBreak?: boolean }) {
  return (
    <section className={avoidBreak ? 'mb-8 break-inside-avoid' : 'mb-8'}>
      <p className="eyebrow">Bagian {no}</p>
      <h2 className="mb-3 mt-1 text-2xl">{title}</h2>
      {children}
    </section>
  )
}

/**
 * Laporan siap cetak bergaya Dea Saka Kurnia Putra Design System: input, hasil, langkah, dan grafik.
 * Gunakan “Simpan sebagai PDF” pada dialog cetak; footer hak cipta tercetak di setiap halaman.
 */
export function ReportPage() {
  const report = readReport()
  useEffect(() => {
    document.documentElement.classList.remove('dark')
    document.title = report ? `Laporan ${report.pageTitle} — Dea Saka Kurnia Putra` : 'Laporan IDStats'
    if (!report) return
    const timer = window.setTimeout(() => window.print(), 2500) // beri waktu Plotly & KaTeX merender
    return () => window.clearTimeout(timer)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (!report) {
    return <p className="p-10 text-center">Tidak ada data laporan. Jalankan perhitungan lalu klik “Laporan PDF”.</p>
  }
  const year = new Date(report.createdAt).getFullYear()
  let n = 0
  const no = () => String(++n).padStart(2, '0')

  return (
    <div className="report min-h-dvh bg-[var(--paper-100)] print:bg-white">
      {/* Footer berulang di setiap halaman cetak */}
      <div className="report-page-footer hidden print:flex">
        <span>IDStats · {report.pageTitle}</span>
        <span>
          © {year} {COPYRIGHT}
        </span>
      </div>

      <div className="mx-auto max-w-4xl bg-white px-10 py-10 text-[var(--ink-700)] shadow-sm print:max-w-none print:px-0 print:py-0 print:shadow-none">
        <header className="mb-8">
          <div className="flex items-center justify-between gap-4">
            <img src="/brand/logo-horizontal.jpg" alt="Dea Saka Kurnia Putra — A brighter tomorrow through meaningful work" className="h-16 w-auto mix-blend-multiply" />
            <Button className="print:hidden" onClick={() => window.print()}>
              <Printer /> Cetak / Simpan PDF
            </Button>
          </div>
          <span className="streak mt-5" aria-hidden="true" />
          <div className="mt-6 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
            <div>
              <p className="eyebrow">Laporan IDStats · Modelling &amp; Optimization</p>
              <h1 className="mt-2 text-4xl leading-tight" style={{ fontWeight: 200 }}>
                {report.pageTitle}
              </h1>
              <p className="mt-1 text-lg text-[var(--grey-600)]">{report.variantLabel}</p>
            </div>
            <dl className="font-mono text-xs text-[var(--grey-600)] sm:text-right">
              <dt className="eyebrow">Dibuat</dt>
              <dd>{new Date(report.createdAt).toLocaleString('id-ID')}</dd>
            </dl>
          </div>
          {report.response.conclusion && (
            <div className="mt-6 rounded-lg border border-[var(--paper-300)] bg-[var(--paper-050)] p-4">
              <p className="eyebrow">Kesimpulan</p>
              <p className="mt-1 text-[var(--ink-900)]">{report.response.conclusion}</p>
            </div>
          )}
        </header>

        {report.story && (
          <Section no={no()} title="Soal & formulasi" avoidBreak>
            <blockquote className="whitespace-pre-wrap border-l-2 border-[var(--paper-300)] pl-4 italic text-[var(--grey-600)]">{report.story.text}</blockquote>
            <p className="eyebrow mt-4">Formulasi</p>
            <p className="mt-1 whitespace-pre-wrap">{report.story.formulation}</p>
            {report.story.assumptions.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-sm text-[var(--grey-600)]">
                {report.story.assumptions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}
          </Section>
        )}

        <Section no={no()} title="Input" avoidBreak>
          <table className="w-full border border-[var(--paper-300)] text-sm">
            <tbody>
              {formatInput(report.input).map(([k, v]) => (
                <tr key={k} className="border-t border-[var(--paper-300)] align-top">
                  <th className="w-48 bg-[var(--paper-100)] px-3 py-1.5 text-left font-mono text-xs font-medium">{k}</th>
                  <td className="whitespace-pre-wrap break-all px-3 py-1.5 font-mono text-xs">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        <Section no={no()} title="Hasil">
          <ResultView response={report.response} name={report.variantLabel} />
        </Section>

        {report.response.steps.length > 0 && (
          <Section no={no()} title="Langkah penyelesaian">
            <StepsView steps={report.response.steps} />
          </Section>
        )}

        {report.response.charts.length > 0 && (
          <Section no={no()} title="Visualisasi">
            <ChartView charts={report.response.charts.map((c) => ({ ...c, spec: { ...c.spec, frames: undefined } }))} />
          </Section>
        )}

        <footer className="mt-12 break-inside-avoid">
          <span className="streak" aria-hidden="true" />
          <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <img src="/brand/mark-p.jpg" alt="" className="size-10 mix-blend-multiply" />
              <div>
                <p className="font-display text-sm font-light tracking-[0.34em] text-[var(--ink-900)]">DEA SAKA KURNIA PUTRA</p>
                <p className="text-[10px] uppercase tracking-[0.22em] text-[var(--grey-600)]">A brighter tomorrow through meaningful work</p>
              </div>
            </div>
            <p className="text-xs text-[var(--grey-600)]">
              © {year} {COPYRIGHT}
            </p>
          </div>
        </footer>
      </div>
    </div>
  )
}
