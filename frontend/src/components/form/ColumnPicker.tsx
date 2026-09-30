import { Database } from 'lucide-react'
import { useDataset } from '@/context/DatasetContext'

/** Dropdown kecil untuk mengisi input angka dari satu kolom dataset aktif. */
export function ColumnPicker({ onPick, label = 'Isi dari kolom dataset' }: { onPick: (values: number[], column: string) => void; label?: string }) {
  const { dataset, numericColumns, columnValues } = useDataset()
  if (!dataset || numericColumns.length === 0) return null
  return (
    <label className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <Database className="size-3.5" aria-hidden />
      <span className="sr-only">{label}</span>
      <select
        className="h-7 rounded-md border bg-card px-2 text-xs text-foreground"
        value=""
        onChange={(e) => e.target.value && onPick(columnValues(e.target.value), e.target.value)}
      >
        <option value="">{label}…</option>
        {numericColumns.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
    </label>
  )
}
