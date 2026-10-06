import { describe, expect, it } from 'vitest'
import { buildBody, initialRaw, rawFromBody, type FieldDef, type RawValues } from '@/components/form/fields'

const fields: FieldDef[] = [
  { key: 'mode', label: 'Mode', type: 'select', virtual: true, options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }], infer: (b) => (b.x ? 'a' : 'b') },
  { key: 'x', label: 'X', type: 'numbers', required: true, showIf: (r) => r.mode === 'a' },
  { key: 'params.mu', label: 'μ', type: 'number', default: '0' },
  { key: 'table', label: 'Tabel', type: 'matrix' },
  { key: 'groups', label: 'Kelompok', type: 'groups', minItems: 2 },
  { key: 'cells', label: 'Sel', type: 'cells' },
  { key: 'alpha', label: 'α', type: 'alpha' },
]

describe('buildBody', () => {
  it('mengubah form menjadi body bersarang dan melewati field tersembunyi/virtual', () => {
    const raw: RawValues = { ...initialRaw(fields), mode: 'a', x: '1, 2, 3', table: '1 2\n3 4', cells: 'a1 | b1 | 1 2' }
    raw.groups = [{ name: 'G1', values: '1 2' }, { name: 'G2', values: '3 4' }]
    const { body, errors } = buildBody(fields, raw)
    expect(errors).toEqual([])
    expect(body).toEqual({
      x: [1, 2, 3],
      params: { mu: 0 },
      table: [[1, 2], [3, 4]],
      groups: [{ name: 'G1', data: [1, 2] }, { name: 'G2', data: [3, 4] }],
      cells: [{ a: 'a1', b: 'b1', data: [1, 2] }],
      alpha: 0.05,
    })
  })

  it('melaporkan error yang ramah', () => {
    const raw = { ...initialRaw(fields), mode: 'a', table: '1 2\n3', x: '' }
    const { errors } = buildBody(fields, raw)
    expect(errors).toContain('X wajib diisi.')
    expect(errors.some((e) => e.includes('jumlah kolom yang sama'))).toBe(true)
    expect(errors.some((e) => e.includes('belum berisi data'))).toBe(true)
  })

  it('rawFromBody adalah kebalikan buildBody', () => {
    const body = { x: [1, 2], params: { mu: 5 }, table: [[1, 2]], groups: [{ name: 'A', data: [1] }, { name: 'B', data: [2] }], cells: [{ a: 'p', b: 'q', data: [3, 4] }], alpha: 0.01 }
    const raw = rawFromBody(fields, body)
    expect(raw.mode).toBe('a')
    expect(buildBody(fields, raw).body).toEqual(body)
  })
})

describe('optimizer lines', () => {
  it('parse dan tulis ulang', async () => {
    const { parseOptimizerLines, optimizerLines } = await import('@/components/form/fields')
    const r = parseOptimizerLines('adamw lr=0.01 weight_decay=0\nsgd')
    expect(r).toEqual({ ok: true, value: [{ id: 'adamw', params: { lr: 0.01, weight_decay: 0 } }, { id: 'sgd', params: {} }] })
    if (r.ok) expect(optimizerLines(r.value)).toBe('adamw lr=0.01 weight_decay=0\nsgd')
    expect(parseOptimizerLines('adamw lr=abc').ok).toBe(false)
  })
})
