import type { SolverResponse } from './api'

export interface ReportPayload {
  pageTitle: string
  variantLabel: string
  input: Record<string, unknown>
  response: SolverResponse<unknown>
  createdAt: number
}

const KEY = 'idstats-report'

/** Simpan data laporan lalu buka halaman cetak (Simpan sebagai PDF lewat dialog cetak browser). */
export function openReport(payload: Omit<ReportPayload, 'createdAt'>) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify({ ...payload, createdAt: Date.now() }))
    localStorage.setItem(KEY, JSON.stringify({ ...payload, createdAt: Date.now() }))
  } catch {
    /* data terlalu besar untuk storage */
  }
  window.open('/laporan', '_blank', 'noopener')
}

export function readReport(): ReportPayload | null {
  try {
    const t = sessionStorage.getItem(KEY) ?? localStorage.getItem(KEY)
    return t ? (JSON.parse(t) as ReportPayload) : null
  } catch {
    return null
  }
}
