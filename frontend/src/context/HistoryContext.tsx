import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { RawValues } from '@/components/form/fields'

export interface HistoryEntry {
  id: string
  at: number
  /** Rute halaman, mis. /stats/inferential */
  path: string
  pageTitle: string
  variantId: string
  variantLabel: string
  /** Endpoint API, agar laporan dapat dibuat ulang dari riwayat. */
  endpoint?: string
  raw: RawValues
  body: Record<string, unknown>
  conclusion: string | null
}

interface HistoryValue {
  entries: HistoryEntry[]
  add: (e: Omit<HistoryEntry, 'id' | 'at'>) => void
  remove: (id: string) => void
  clear: () => void
  get: (id: string) => HistoryEntry | undefined
}

const KEY = 'idstats-history'
const MAX = 100
const HistoryContext = createContext<HistoryValue | null>(null)

function load(): HistoryEntry[] {
  try {
    const t = localStorage.getItem(KEY)
    return t ? (JSON.parse(t) as HistoryEntry[]) : []
  } catch {
    return []
  }
}

function save(entries: HistoryEntry[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(entries))
  } catch {
    /* penyimpanan penuh/diblokir: riwayat hanya bertahan selama sesi */
  }
}

/** Riwayat perhitungan disimpan di browser pengguna (tidak dikirim ke server). */
export function HistoryProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<HistoryEntry[]>(load)
  const update = useCallback((fn: (prev: HistoryEntry[]) => HistoryEntry[]) => {
    setEntries((prev) => {
      const next = fn(prev)
      save(next)
      return next
    })
  }, [])
  const value = useMemo<HistoryValue>(
    () => ({
      entries,
      add: (e) => update((prev) => [{ ...e, id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, at: Date.now() }, ...prev].slice(0, MAX)),
      remove: (id) => update((prev) => prev.filter((x) => x.id !== id)),
      clear: () => update(() => []),
      get: (id) => entries.find((x) => x.id === id),
    }),
    [entries, update],
  )
  return <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useHistory() {
  const ctx = useContext(HistoryContext)
  if (!ctx) throw new Error('useHistory harus dipakai di dalam HistoryProvider')
  return ctx
}
