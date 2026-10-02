import type { FieldDef } from '@/components/form/fields'

export const LP_SYNTAX_HINT =
  'Baris 1: fungsi tujuan (max/min). Baris berikutnya: satu kendala per baris dengan ≤ (<=), ≥ (>=), atau =. ' +
  'Variabel ≥ 0 secara default; tulis “x3 free” untuk bebas tanda atau “nonpos x2” untuk ≤ 0. Pecahan boleh (1/3).'

export function lpModelField(placeholder = 'max Z = 3x1 + 5x2\nx1 <= 4\n2x2 <= 12\n3x1 + 2x2 <= 18'): FieldDef {
  return { key: 'model', label: 'Model linear programming', type: 'textarea', required: true, placeholder, hint: LP_SYNTAX_HINT }
}
