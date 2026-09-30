import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

export type Cell = string | number | boolean | null

export interface Dataset {
  name: string
  columns: string[]
  rows: Cell[][]
}

interface DatasetContextValue {
  dataset: Dataset | null
  setDataset: (d: Dataset | null) => void
  numericColumns: string[]
  columnValues: (column: string) => number[]
}

const KEY = 'idstats-dataset'
const MAX_STORED_CHARS = 1_000_000
const DatasetContext = createContext<DatasetContextValue | null>(null)

function load(): Dataset | null {
  try {
    const text = localStorage.getItem(KEY)
    return text ? (JSON.parse(text) as Dataset) : null
  } catch {
    return null
  }
}

function isNumeric(v: Cell): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

/** Dataset aktif dipakai bersama semua halaman (tombol "Isi dari kolom dataset"). */
export function DatasetProvider({ children }: { children: ReactNode }) {
  const [dataset, setState] = useState<Dataset | null>(load)

  const setDataset = useCallback((d: Dataset | null) => {
    setState(d)
    try {
      const text = d ? JSON.stringify(d) : ''
      if (d && text.length <= MAX_STORED_CHARS) localStorage.setItem(KEY, text)
      else localStorage.removeItem(KEY)
    } catch {
      /* penyimpanan diblokir: dataset tetap ada selama sesi */
    }
  }, [])

  const value = useMemo<DatasetContextValue>(() => {
    const numericColumns = dataset
      ? dataset.columns.filter((_, j) => {
          const filled = dataset.rows.map((r) => r[j]).filter((v) => v !== null && v !== '')
          return filled.length > 0 && filled.every(isNumeric)
        })
      : []
    const columnValues = (column: string) => {
      const j = dataset?.columns.indexOf(column) ?? -1
      return j < 0 || !dataset ? [] : dataset.rows.map((r) => r[j]).filter(isNumeric)
    }
    return { dataset, setDataset, numericColumns, columnValues }
  }, [dataset, setDataset])

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDataset() {
  const ctx = useContext(DatasetContext)
  if (!ctx) throw new Error('useDataset harus dipakai di dalam DatasetProvider')
  return ctx
}
