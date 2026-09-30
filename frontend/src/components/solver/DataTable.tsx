import { formatNumber } from '@/lib/utils'
import type { SolverTable } from '@/lib/api'

export function DataTable({ table, maxHeight = 320 }: { table: SolverTable; maxHeight?: number }) {
  return (
    <div className="overflow-auto rounded-md border" style={{ maxHeight }}>
      <table className="w-full text-sm tabular-nums">
        <thead className="sticky top-0 bg-muted">
          <tr>
            {table.columns.map((c) => (
              <th key={c} className="px-3 py-1.5 text-left font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, i) => (
            <tr key={i} className="border-t">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-1">
                  {formatNumber(cell, 6)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
