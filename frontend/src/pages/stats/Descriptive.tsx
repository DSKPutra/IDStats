import { FileDown, Loader2, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Latex } from '@/components/solver/Latex'
import { MethodPage } from '@/components/solver/MethodPage'
import { ApiError, getExample, solve, type SolverResponse } from '@/lib/api'
import { downloadText, toCsv } from '@/lib/export'
import { formatNumber, parseNumbers } from '@/lib/utils'

interface DescriptiveResult {
  n: number
  sum: number
  mean: number
  median: number
  modes: number[]
  variance: number
  std: number
  min: number
  max: number
  range: number
  q1: number
  q2: number
  q3: number
  iqr: number
  skewness: number | null
  kurtosis: number | null
  standard_error: number
  coefficient_of_variation: number | null
}

const ROWS: [keyof DescriptiveResult, string][] = [
  ['n', 'Banyak data (n)'],
  ['sum', 'Jumlah (Σx)'],
  ['mean', 'Rata-rata (Mean)'],
  ['median', 'Median'],
  ['modes', 'Modus (Mode)'],
  ['variance', 'Varians sampel (s²)'],
  ['std', 'Simpangan baku (s)'],
  ['standard_error', 'Galat baku rata-rata (SE)'],
  ['coefficient_of_variation', 'Koefisien variasi (CV)'],
  ['min', 'Minimum'],
  ['max', 'Maksimum'],
  ['range', 'Jangkauan (Range)'],
  ['q1', 'Kuartil 1 (Q1)'],
  ['q2', 'Kuartil 2 (Q2)'],
  ['q3', 'Kuartil 3 (Q3)'],
  ['iqr', 'Jangkauan antarkuartil (IQR)'],
  ['skewness', 'Kemencengan (Skewness)'],
  ['kurtosis', 'Keruncingan (Excess Kurtosis)'],
]

function display(value: DescriptiveResult[keyof DescriptiveResult]) {
  if (Array.isArray(value)) return value.length ? value.map((v) => formatNumber(v)).join(', ') : 'Tidak ada'
  return formatNumber(value)
}

export function DescriptivePage() {
  const [text, setText] = useState('')
  const [response, setResponse] = useState<SolverResponse<DescriptiveResult> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const parsed = parseNumbers(text)

  const run = async () => {
    setError(null)
    if (parsed.invalid.length) {
      setError(`Nilai berikut bukan angka: ${parsed.invalid.slice(0, 5).join(', ')}. Gunakan titik untuk desimal.`)
      return
    }
    if (parsed.values.length < 2) {
      setError('Masukkan minimal 2 data.')
      return
    }
    setLoading(true)
    try {
      setResponse(await solve<DescriptiveResult>('/descriptive/summary', { data: parsed.values }))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Terjadi kesalahan tak terduga.')
    } finally {
      setLoading(false)
    }
  }

  const loadExample = async () => {
    setError(null)
    try {
      const ex = await getExample<{ data: number[] }>('stats', 'descriptive')
      setText(ex.input.data.join(', '))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Gagal memuat contoh soal.')
    }
  }

  const exportCsv = () => {
    if (!response) return
    downloadText('idstats-statistik-deskriptif.csv', toCsv(['Ukuran', 'Nilai'], ROWS.map(([k, label]) => [label, display(response.result[k])])))
  }

  const input = (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-5">
      <label htmlFor="data" className="text-sm font-medium">
        Data sampel
      </label>
      <Textarea
        id="data"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Contoh: 72, 85, 64, 90, 78 — atau tempel satu kolom dari Excel"
        aria-describedby="data-hint"
      />
      <p id="data-hint" className="text-xs text-muted-foreground">
        Pisahkan dengan koma, spasi, titik koma, atau baris baru. Gunakan titik (.) untuk desimal.
        {text && ` Terbaca ${parsed.values.length} angka.`}
      </p>
      {error && (
        <p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button onClick={run} disabled={loading}>
          {loading && <Loader2 className="animate-spin" />} Hitung
        </Button>
        <Button variant="outline" onClick={loadExample}>
          <Sparkles /> Muat Contoh Soal
        </Button>
      </div>
    </div>
  )

  const result = response && (
    <div className="rounded-xl border bg-card">
      <div className="flex items-center justify-between p-4">
        <h2 className="font-semibold">Ringkasan statistik</h2>
        <Button variant="outline" size="sm" onClick={exportCsv}>
          <FileDown /> CSV
        </Button>
      </div>
      <table className="w-full text-sm tabular-nums">
        <tbody>
          {ROWS.map(([key, label]) => (
            <tr key={key} className="border-t">
              <th scope="row" className="px-4 py-2 text-left font-normal text-muted-foreground">{label}</th>
              <td className="px-4 py-2 text-right font-medium">{display(response.result[key])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  const theory = (
    <>
      <p>
        <strong>Statistik deskriptif</strong> meringkas data menjadi ukuran <em>pemusatan</em> (mean, median, modus),
        <em> penyebaran</em> (varians, simpangan baku, IQR), dan <em>bentuk</em> distribusi (skewness, kurtosis).
      </p>
      <p>Varians sampel memakai pembagi n − 1 (koreksi Bessel) agar menjadi penduga tak bias bagi varians populasi:</p>
      <Latex block>{String.raw`s^2 = \frac{1}{n-1}\sum_{i=1}^{n}(x_i-\bar{x})^2`}</Latex>
      <p>
        Skewness positif berarti ekor kanan lebih panjang; excess kurtosis positif berarti ekor lebih tebal daripada
        distribusi normal. Q-Q plot yang titik-titiknya mengikuti garis lurus mengindikasikan data mendekati normal.
      </p>
    </>
  )

  return (
    <MethodPage
      title="Statistik Deskriptif (Descriptive Statistics)"
      subtitle="Ukuran pemusatan, penyebaran, dan bentuk distribusi — lengkap dengan histogram, boxplot, dan Q-Q plot."
      input={input}
      result={result}
      response={response}
      theory={theory}
    />
  )
}
