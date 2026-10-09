import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table'
import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { useMemo } from 'react'
import { Button } from '@/components/ui/button'
import type { Cell, Dataset } from '@/context/DatasetContext'

function parseCell(text: string): Cell {
  const t = text.trim()
  if (t === '') return null
  const n = Number(t)
  return Number.isFinite(n) ? n : t
}

/** Tabel data yang bisa diedit langsung (TanStack Table), dengan paginasi 25 baris. */
export function EditableTable({ dataset, onChange }: { dataset: Dataset; onChange: (d: Dataset) => void }) {
  const columns = useMemo<ColumnDef<Cell[]>[]>(
    () => [
      {
        id: '__row',
        header: '#',
        cell: ({ row }) => <span className="px-2 text-xs text-muted-foreground">{row.index + 1}</span>,
      },
      ...dataset.columns.map<ColumnDef<Cell[]>>((name, j) => ({
        id: `c${j}`,
        header: name,
        accessorFn: (r) => r[j],
        cell: ({ row, getValue }) => {
          const v = getValue() as Cell
          return (
            <input
              aria-label={`${name} baris ${row.index + 1}`}
              defaultValue={v === null ? '' : String(v)}
              key={`${row.index}-${String(v)}`}
              className="w-full min-w-20 bg-transparent px-2 py-1 tabular-nums focus:bg-card focus:outline-none focus:ring-2 focus:ring-ring"
              onBlur={(e) => {
                const next = parseCell(e.target.value)
                if (next === v) return
                const rows = dataset.rows.map((r, i) => (i === row.index ? r.map((c, k) => (k === j ? next : c)) : r))
                onChange({ ...dataset, rows })
              }}
            />
          )
        },
      })),
      {
        id: '__delete',
        header: '',
        cell: ({ row }) => (
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            aria-label={`Hapus baris ${row.index + 1}`}
            onClick={() => onChange({ ...dataset, rows: dataset.rows.filter((_, i) => i !== row.index) })}
          >
            <Trash2 />
          </Button>
        ),
      },
    ],
    [dataset, onChange],
  )

  // Proyek tidak memakai React Compiler, jadi peringatan memoisasi TanStack tidak berlaku.
  // oxlint-disable-next-line react/incompatible-library
  const table = useReactTable({
    data: dataset.rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    autoResetPageIndex: false,
    initialState: { pagination: { pageSize: 25 } },
  })

  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id} className="px-2 py-1.5 text-left font-medium">
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((r) => (
              <tr key={r.id} className="border-t">
                {r.getVisibleCells().map((c) => (
                  <td key={c.id} className="p-0">
                    {flexRender(c.column.columnDef.cell, c.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <Button variant="outline" size="icon" className="size-8" aria-label="Halaman sebelumnya" disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()}>
            <ChevronLeft />
          </Button>
          <span className="tabular-nums">
            Halaman {table.getState().pagination.pageIndex + 1} dari {table.getPageCount()}
          </span>
          <Button variant="outline" size="icon" className="size-8" aria-label="Halaman berikutnya" disabled={!table.getCanNextPage()} onClick={() => table.nextPage()}>
            <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  )
}
