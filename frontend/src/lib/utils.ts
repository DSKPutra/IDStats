import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format angka untuk tampilan: maksimal `digits` desimal, tanpa nol berlebih. */
export function formatNumber(value: unknown, digits = 4): string {
  if (value === null || value === undefined) return '—'
  if (typeof value !== 'number') return String(value)
  if (!Number.isFinite(value)) return '—'
  if (Number.isInteger(value)) return value.toLocaleString('id-ID')
  // Nilai sangat kecil (mis. p-value) jangan dibulatkan menjadi 0.
  if (Math.abs(value) < 1e-4) return value.toExponential(3).replace('.', ',')
  return value.toLocaleString('id-ID', { maximumFractionDigits: digits })
}

export interface ParsedNumbers {
  values: number[]
  invalid: string[]
}

/**
 * Parse daftar angka dari teks bebas (hasil ketik atau salin dari Excel).
 * Pemisah: spasi, baris baru, tab, titik koma, atau koma. Desimal memakai titik.
 */
export function parseNumbers(text: string): ParsedNumbers {
  const tokens = text.split(/[\s;,]+/).filter(Boolean)
  const values: number[] = []
  const invalid: string[] = []
  for (const token of tokens) {
    const n = Number(token)
    if (Number.isFinite(n)) values.push(n)
    else invalid.push(token)
  }
  return { values, invalid }
}
