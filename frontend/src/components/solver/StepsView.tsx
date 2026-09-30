import type { SolverStep } from '@/lib/api'
import { DataTable } from './DataTable'
import { Latex } from './Latex'

export function StepsView({ steps }: { steps: SolverStep[] }) {
  return (
    <ol className="flex flex-col gap-4">
      {steps.map((s, i) => (
        <li key={i} className="rounded-xl border bg-card p-5">
          <h3 className="font-semibold">{s.title}</h3>
          {s.explanation && <p className="mt-1 text-sm text-muted-foreground">{s.explanation}</p>}
          {s.latex && (
            <div className="mt-3">
              <Latex block>{s.latex}</Latex>
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
