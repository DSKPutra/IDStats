import { ArrowRight, BookOpenText, Loader2, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, postJson } from '@/lib/api'

export interface StoryResult {
  variant_id: string
  input: Record<string, unknown>
  formulation: string
  assumptions: string[]
  /** Field yang belum ditemukan di soal (harus diisi manual). */
  missing?: string[]
  complete?: boolean
  engine?: 'aturan' | 'ai'
  /** Halaman yang lebih cocok bila soal salah tempat. */
  suggestion?: { title: string; path: string } | null
}

export interface StoryVariant {
  id: string
  label: string
  fields: { key: string; label: string; type: string }[]
}

interface Props {
  pageTitle: string
  module: string
  variants: StoryVariant[]
  /** Terapkan hasil terjemahan ke formulir dan hitung. */
  onApply: (result: StoryResult, text: string) => void
  result: StoryResult | null
}

/** Input berbentuk soal cerita: teks diterjemahkan menjadi isian formulir, lalu dihitung solver IDStats. */
export function StoryInput({ pageTitle, module, variants, onApply, result }: Props) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const location = useLocation()

  const submit = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await postJson<StoryResult>('/story/interpret', { text, page_title: pageTitle, module, variants, page_path: location.pathname })
      onApply(res, text)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Gagal menerjemahkan soal cerita.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-lg border bg-card">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-5 py-3.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <BookOpenText className="size-5 shrink-0 text-muted-foreground" aria-hidden />
        <span className="flex-1">
          <span className="eyebrow block">Opsi input</span>
          <span className="font-medium text-strong">Masukkan dalam bentuk soal cerita</span>
        </span>
        <span className="text-xs text-muted-foreground">{open ? 'Tutup' : 'Buka'}</span>
      </button>
      {open && (
        <div className="flex flex-col gap-3 border-t px-5 py-4">
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Teks soal
            <Textarea
              className="min-h-36 font-sans"
              placeholder="Tempel soal cerita di sini, mis. “Sebuah pabrik memproduksi meja dan kursi. Setiap meja memberi laba Rp30.000 …”"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
          <p className="text-xs text-muted-foreground">
            Soal dibaca langsung oleh IDStats — angka, satuan, dan kata kunci seperti “tersedia”, “paling sedikit”,
            “keuntungan”, “taraf nyata” — lalu diubah menjadi persamaan/isian formulir dan metode yang sesuai. Tidak perlu
            akun atau API key. Data yang tidak ditemukan akan ditandai agar Anda lengkapi; periksa kembali hasilnya.
          </p>
          {error && <p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
          <div>
            <Button onClick={submit} disabled={loading || text.trim().length < 15}>
              {loading ? <Loader2 className="animate-spin" /> : <Wand2 />} Terjemahkan &amp; hitung
            </Button>
          </div>
        </div>
      )}
      {result && (
        <div className="border-t px-5 py-4 text-sm">
          <span className="streak mb-3 w-16" aria-hidden />
          <p className="eyebrow mb-1">Formulasi dari soal cerita</p>
          <p className="whitespace-pre-wrap leading-relaxed">{result.formulation}</p>
          {result.missing && result.missing.length > 0 && (
            <p className="mt-3 rounded-md bg-warning/10 px-3 py-2 text-[var(--ink-900)] dark:text-foreground">
              Lengkapi di formulir lalu klik Hitung: {result.missing.join(', ')}.
            </p>
          )}
          {result.suggestion && (
            <Link to={result.suggestion.path} className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-strong underline decoration-ring underline-offset-4">
              Soal ini tampaknya masalah {result.suggestion.title} — buka halamannya <ArrowRight className="size-4" />
            </Link>
          )}
          {result.assumptions.length > 0 && (
            <>
              <p className="eyebrow mb-1 mt-3">Asumsi / penafsiran</p>
              <ul className="list-disc pl-5 text-muted-foreground">
                {result.assumptions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  )
}
