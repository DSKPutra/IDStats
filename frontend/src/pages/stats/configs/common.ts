import type { FieldDef, RawValues } from '@/components/form/fields'

export const alpha: FieldDef = { key: 'alpha', label: 'Taraf signifikansi α', type: 'alpha', hint: 'Umumnya 0.05 atau 0.01.' }
export const alternative: FieldDef = { key: 'alternative', label: 'Arah uji (hipotesis alternatif)', type: 'alternative' }

const isData = (r: RawValues) => r.input_mode === 'data'
const isSummary = (r: RawValues) => r.input_mode === 'summary'

/** Pilihan input: data mentah atau ringkasan (n, x̄, s). */
export function sampleFields(opts: { sd?: boolean } = {}): FieldDef[] {
  return [
    {
      key: 'input_mode',
      label: 'Bentuk input',
      type: 'select',
      virtual: true,
      options: [
        { value: 'data', label: 'Data mentah' },
        { value: 'summary', label: 'Ringkasan (n, rata-rata' + (opts.sd ? ', s)' : ')') },
      ],
      infer: (b) => (b.data ? 'data' : 'summary'),
    },
    { key: 'data', label: 'Data sampel', type: 'numbers', required: true, showIf: isData, placeholder: 'Contoh: 12.1, 11.8, 12.5, 12.0' },
    { key: 'n', label: 'Ukuran sampel n', type: 'integer', required: true, showIf: isSummary },
    { key: 'mean', label: 'Rata-rata sampel x̄', type: 'number', required: true, showIf: isSummary },
    ...(opts.sd ? [{ key: 'sd', label: 'Simpangan baku sampel s', type: 'number', required: true, showIf: isSummary } as FieldDef] : []),
  ]
}

export const twoSamples: FieldDef[] = [
  { key: 'x', label: 'Sampel 1', type: 'numbers', required: true },
  { key: 'y', label: 'Sampel 2', type: 'numbers', required: true },
]

export const groups: FieldDef = { key: 'groups', label: 'Data per kelompok', type: 'groups', itemLabel: 'Kelompok', minItems: 2 }
