export interface SolverTable {
  columns: string[]
  rows: unknown[][]
}

export interface SolverStep {
  title: string
  explanation: string
  latex?: string | null
  table?: SolverTable | null
  matrix?: number[][] | null
}

export interface SolverChart {
  id: string
  title: string
  spec: { data: unknown[]; layout?: Record<string, unknown>; frames?: unknown[] }
}

export interface SummaryItem {
  label: string
  value: unknown
}

export interface NamedTable extends SolverTable {
  title: string
}

export interface SolverResponse<R = Record<string, unknown>> {
  result: R
  steps: SolverStep[]
  charts: SolverChart[]
  warnings: string[]
  summary: SummaryItem[]
  tables: NamedTable[]
  conclusion?: string | null
}

export interface Example<I = Record<string, unknown>> {
  title: string
  description: string
  input: I
}

export class ApiError extends Error {}

const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  const isForm = init?.body instanceof FormData
  try {
    res = await fetch(`${API_BASE}/api${path}`, {
      ...init,
      headers: isForm ? init?.headers : { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError('Tidak dapat terhubung ke server. Periksa koneksi internet Anda.')
  }
  if (!res.ok) {
    let detail = `Server mengembalikan status ${res.status}.`
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* respons bukan JSON */
    }
    throw new ApiError(detail)
  }
  return (await res.json()) as T
}

export function solve<R = Record<string, unknown>>(path: string, body: unknown) {
  return request<SolverResponse<R>>(path, { method: 'POST', body: JSON.stringify(body) })
}

export function getExample<I = Record<string, unknown>>(module: string, method: string) {
  return request<Example<I>>(`/examples/${module}/${method}`)
}

export function getJson<T>(path: string) {
  return request<T>(path)
}

export function uploadFile<R = Record<string, unknown>>(path: string, file: File) {
  const body = new FormData()
  body.append('file', file)
  return request<SolverResponse<R>>(path, { method: 'POST', body })
}

export function postJson<T>(path: string, body: unknown) {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}
