import { CheckCircle2, FileDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { SolverResponse } from '@/lib/api'
import { downloadText, toCsv } from '@/lib/export'
import { formatNumber } from '@/lib/utils'
import { DataTable } from './DataTable'
import { Latex } from './Latex'

function slug(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

function SummaryValue({ value }: { value: unknown }) {
  if (typeof value === 'string' && value.includes('\\')) return <Latex>{value}</Latex>
  if (typeof value === 'boolean') return <>{value ? 'Ya' : 'Tidak'}</>
  return <>{formatNumber(value, 6)}</>
}

export function ResultView({ response, name }: { response: SolverResponse<unknown>; name: string }) {
  const exportSummary = () =>
    downloadText(
      `idstats-${slug(name)}-ringkasan.csv`,
      toCsv(['Ukuran', 'Nilai'], response.summary.map((s) => [s.label, s.value])),
    )
  return (
    <div className="flex flex-col gap-4">
      {response.conclusion && (
        <div className="flex gap-3 rounded-xl border border-primary/30 bg-accent p-4 text-sm text-accent-foreground">
          <CheckCircle2 className="mt-0.5 size-5 shrink-0" aria-hidden />
          <div>
            <p className="font-semibold">Kesimpulan</p>
            <p className="mt-0.5">{response.conclusion}</p>
          </div>
        </div>
      )}
      {response.summary.length > 0 && (
        <div className="rounded-xl border bg-card">
          <div className="flex items-center justify-between p-4">
            <h2 className="font-semibold">Ringkasan hasil</h2>
            <Button variant="outline" size="sm" onClick={exportSummary}>
              <FileDown /> CSV
            </Button>
          </div>
          <table className="w-full text-sm tabular-nums">
            <tbody>
              {response.summary.map((s) => (
                <tr key={s.label} className="border-t">
                  <th scope="row" className="px-4 py-2 text-left font-normal text-muted-foreground">
                    {s.label}
                  </th>
                  <td className="px-4 py-2 text-right font-medium">
                    <SummaryValue value={s.value} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {response.tables.map((t) => (
        <div key={t.title} className="rounded-xl border bg-card">
          <div className="flex items-center justify-between p-4">
            <h2 className="font-semibold">{t.title}</h2>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadText(`idstats-${slug(name)}-${slug(t.title)}.csv`, toCsv(t.columns, t.rows))}
            >
              <FileDown /> CSV
            </Button>
          </div>
          <div className="px-4 pb-4">
            <DataTable table={t} maxHeight={480} />
          </div>
        </div>
      ))}
    </div>
  )
}
