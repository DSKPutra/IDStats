import { parseNumbers } from '@/lib/utils'

/** Satu kelompok/variabel pada input dinamis (nama + daftar angka mentah). */
export interface GroupRaw {
  name: string
  values: string
}

export type RawValue = string | GroupRaw[]
export type RawValues = Record<string, RawValue>

export type FieldType =
  | 'numbers' // daftar angka → number[]
  | 'number'
  | 'integer'
  | 'text'
  | 'select'
  | 'alternative' // arah uji hipotesis
  | 'alpha'
  | 'boolean'
  | 'matrix' // baris per baris → number[][]
  | 'labels' // "a, b, c" → string[]
  | 'groups' // [{name, data}]
  | 'variables' // {name: number[]}
  | 'cells' // baris "A | B | nilai…" → [{a, b, data}]
  | 'textarea' // teks bebas multi-baris (mis. model LP) → string

export interface Option {
  value: string
  label: string
}

export interface FieldDef {
  /** Kunci pada body request. Titik membuat objek bersarang (mis. `params.n`). */
  key: string
  label: string
  type: FieldType
  required?: boolean
  placeholder?: string
  hint?: string
  options?: Option[]
  default?: RawValue
  /** Tidak dikirim ke API (mis. pilihan mode input). */
  virtual?: boolean
  /** Untuk field virtual: tebak nilainya dari body contoh soal. */
  infer?: (body: Record<string, unknown>) => string
  showIf?: (raw: RawValues) => boolean
  /** Label default kelompok untuk tipe groups/variables. */
  itemLabel?: string
  minItems?: number
}

export const ALTERNATIVE_OPTIONS: Option[] = [
  { value: 'two-sided', label: 'Dua sisi (≠)' },
  { value: 'less', label: 'Sisi kiri (<)' },
  { value: 'greater', label: 'Sisi kanan (>)' },
]

export function defaultRaw(field: FieldDef): RawValue {
  if (field.default !== undefined) return field.default
  switch (field.type) {
    case 'alpha':
      return '0.05'
    case 'alternative':
      return 'two-sided'
    case 'boolean':
      return 'false'
    case 'select':
      return field.options?.[0]?.value ?? ''
    case 'groups':
    case 'variables': {
      const n = field.minItems ?? 2
      return Array.from({ length: n }, (_, i) => ({ name: `${field.itemLabel ?? 'Kelompok'} ${i + 1}`, values: '' }))
    }
    default:
      return ''
  }
}

export function initialRaw(fields: FieldDef[]): RawValues {
  const raw: RawValues = {}
  for (const f of fields) if (!(f.key in raw)) raw[f.key] = defaultRaw(f)
  return raw
}

export function isVisible(field: FieldDef, raw: RawValues) {
  return field.showIf ? field.showIf(raw) : true
}

type Parsed = { value?: unknown; error?: string }

function parseNumberList(label: string, text: string): Parsed {
  const { values, invalid } = parseNumbers(text)
  if (invalid.length) return { error: `${label}: “${invalid.slice(0, 3).join('”, “')}” bukan angka (gunakan titik untuk desimal).` }
  return values.length ? { value: values } : {}
}

export function parseField(field: FieldDef, raw: RawValue): Parsed {
  const label = field.label
  if (Array.isArray(raw)) {
    const items: { name: string; data: number[] }[] = []
    for (const g of raw) {
      const name = g.name.trim()
      const parsed = parseNumberList(`${label} “${name || '(tanpa nama)'}”`, g.values)
      if (parsed.error) return parsed
      if (!name) return { error: `${label}: setiap ${field.itemLabel?.toLowerCase() ?? 'kelompok'} harus diberi nama.` }
      if (!parsed.value) return { error: `${label}: “${name}” belum berisi data.` }
      items.push({ name, data: parsed.value as number[] })
    }
    if (new Set(items.map((i) => i.name)).size !== items.length) return { error: `${label}: nama tidak boleh sama.` }
    if (items.length < (field.minItems ?? 1)) return { error: `${label}: minimal ${field.minItems} isian.` }
    return { value: field.type === 'variables' ? Object.fromEntries(items.map((i) => [i.name, i.data])) : items }
  }

  const text = raw.trim()
  if (!text) return {}
  switch (field.type) {
    case 'numbers':
      return parseNumberList(label, text)
    case 'number':
    case 'alpha':
    case 'integer': {
      const n = Number(text)
      if (!Number.isFinite(n)) return { error: `${label} harus berupa angka.` }
      if (field.type === 'integer' && !Number.isInteger(n)) return { error: `${label} harus bilangan bulat.` }
      return { value: n }
    }
    case 'boolean':
      return { value: text === 'true' }
    case 'labels':
      return { value: text.split(',').map((s) => s.trim()).filter(Boolean) }
    case 'matrix': {
      const rows: number[][] = []
      for (const [i, line] of text.split('\n').entries()) {
        if (!line.trim()) continue
        const parsed = parseNumberList(`${label} baris ${i + 1}`, line)
        if (parsed.error) return parsed
        rows.push(parsed.value as number[])
      }
      if (new Set(rows.map((r) => r.length)).size > 1) return { error: `${label}: setiap baris harus memiliki jumlah kolom yang sama.` }
      return { value: rows }
    }
    case 'cells': {
      const cells: { a: string; b: string; data: number[] }[] = []
      for (const [i, line] of text.split('\n').entries()) {
        if (!line.trim()) continue
        const parts = line.split('|').map((s) => s.trim())
        if (parts.length !== 3) return { error: `${label} baris ${i + 1}: gunakan format “level A | level B | nilai…”.` }
        const parsed = parseNumberList(`${label} baris ${i + 1}`, parts[2])
        if (parsed.error) return parsed
        if (!parsed.value) return { error: `${label} baris ${i + 1}: belum ada nilai.` }
        cells.push({ a: parts[0], b: parts[1], data: parsed.value as number[] })
      }
      return { value: cells }
    }
    case 'textarea':
      return { value: raw.replace(/\r/g, '') }
    default:
      return { value: text }
  }
}

function setPath(target: Record<string, unknown>, path: string, value: unknown) {
  const keys = path.split('.')
  let obj = target
  for (const k of keys.slice(0, -1)) {
    obj[k] ??= {}
    obj = obj[k] as Record<string, unknown>
  }
  obj[keys[keys.length - 1]] = value
}

function getPath(source: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((o, k) => (o && typeof o === 'object' ? (o as Record<string, unknown>)[k] : undefined), source)
}

/** Ubah nilai mentah form menjadi body request. Mengembalikan daftar error bila ada. */
export function buildBody(fields: FieldDef[], raw: RawValues): { body: Record<string, unknown>; errors: string[] } {
  const body: Record<string, unknown> = {}
  const errors: string[] = []
  const seen = new Set<string>()
  for (const f of fields) {
    if (f.virtual || !isVisible(f, raw) || seen.has(f.key)) continue
    seen.add(f.key)
    const { value, error } = parseField(f, raw[f.key] ?? defaultRaw(f))
    if (error) errors.push(error)
    else if (value === undefined) {
      if (f.required) errors.push(`${f.label} wajib diisi.`)
    } else setPath(body, f.key, value)
  }
  return { body, errors }
}

/** Kebalikan dari buildBody: isi form dari body contoh soal. */
export function rawFromBody(fields: FieldDef[], body: Record<string, unknown>): RawValues {
  const raw = initialRaw(fields)
  for (const f of fields) {
    if (f.virtual) {
      if (f.infer) raw[f.key] = f.infer(body)
      continue
    }
    const v = getPath(body, f.key)
    if (v === undefined || v === null) continue
    raw[f.key] = toRaw(f, v)
  }
  return raw
}

export function toRaw(field: FieldDef, v: unknown): RawValue {
  switch (field.type) {
    case 'numbers':
      return (v as number[]).join(', ')
    case 'labels':
      return (v as string[]).join(', ')
    case 'matrix':
      return (v as number[][]).map((r) => r.join(' ')).join('\n')
    case 'groups':
      return (v as { name: string; data: number[] }[]).map((g) => ({ name: g.name, values: g.data.join(', ') }))
    case 'variables':
      return Object.entries(v as Record<string, number[]>).map(([name, data]) => ({ name, values: data.join(', ') }))
    case 'cells':
      return (v as { a: string; b: string; data: number[] }[]).map((c) => `${c.a} | ${c.b} | ${c.data.join(' ')}`).join('\n')
    default:
      return String(v)
  }
}
