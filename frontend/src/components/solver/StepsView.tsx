import type { SolverStep } from '@/lib/api'
import { DataTable } from './DataTable'
import { Latex } from './Latex'

function matrixLatex(m: number[][]) {
  const fmt = (v: number) => (Number.isInteger(v) ? String(v) : String(Number(v.toPrecision(6))))
  return String.raw`\begin{bmatrix}` + m.map((r) => r.map(fmt).join(' & ')).join(String.raw` \\ `) + String.raw`\end{bmatrix}`
}

export function StepsView({ steps }: { steps: SolverStep[] }) {
  return (
    <ol className="flex flex-col gap-4">
      {steps.map((s, i) => (
        <li key={i} className="rounded-xl border bg-card p-5">
          <h3 className="flex gap-2 font-semibold">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs text-accent-foreground">
              {i + 1}
            </span>
            {s.title}
          </h3>
          {s.explanation && <p className="mt-1 text-sm text-muted-foreground">{s.explanation}</p>}
          {s.latex && (
            <div className="mt-3">
              <Latex block>{s.latex}</Latex>
            </div>
          )}
          {s.matrix && (
            <div className="mt-3">
              <Latex block>{matrixLatex(s.matrix)}</Latex>
            </div>
          )}
          {s.table && (
            <div className="mt-3">
              <DataTable table={s.table} />
            </div>
          )}
        </li>
      ))}
    </ol>
  )
}
