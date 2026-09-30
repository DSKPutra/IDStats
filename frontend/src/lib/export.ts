function csvCell(value: unknown): string {
  const s = value === null || value === undefined ? '' : Array.isArray(value) ? value.join(' ') : String(value)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv(columns: string[], rows: unknown[][]): string {
  return [columns, ...rows].map((r) => r.map(csvCell).join(',')).join('\n')
}

export function downloadText(filename: string, content: string, type = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(new Blob(['﻿', content], { type }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
