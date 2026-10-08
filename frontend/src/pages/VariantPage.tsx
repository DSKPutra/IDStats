import { Info, Loader2, RotateCcw, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { FieldInput } from '@/components/form/FieldInput'
import { buildBody, initialRaw, isVisible, rawFromBody, type FieldDef, type RawValues } from '@/components/form/fields'
import { MethodPage } from '@/components/solver/MethodPage'
import { ResultView } from '@/components/solver/ResultView'
import { Button } from '@/components/ui/button'
import { useDataset, type Dataset } from '@/context/DatasetContext'
import { useHistory } from '@/context/HistoryContext'
import { ApiError, getExample, solve, type Example, type SolverResponse } from '@/lib/api'
import { openReport } from '@/lib/report'
import { cn } from '@/lib/utils'

export interface Variant {
  /** Juga dipakai sebagai id contoh soal: GET /api/examples/<module>/<id>. */
  id: string
  label: string
  endpoint: string
  fields: FieldDef[]
  theory: ReactNode
  description?: string
  /** Ubah body sebelum dikirim (mis. sisipkan dataset aktif). */
  prepareBody?: (body: Record<string, unknown>, ctx: { dataset: Dataset | null }) => Record<string, unknown> | string
}

export interface VariantPageConfig {
  title: string
  subtitle: string
  variants: Variant[]
  exampleModule?: string
}

/** Halaman metode generik: pilih varian → isi form → kirim ke API → tampilkan hasil standar. */
export function VariantPage({ config }: { config: VariantPageConfig }) {
  const [params, setParams] = useSearchParams()
  const variant = config.variants.find((v) => v.id === params.get('metode')) ?? config.variants[0]
  const [rawByVariant, setRawByVariant] = useState<Record<string, RawValues>>({})
  const [response, setResponse] = useState<SolverResponse<unknown> | null>(null)
  const [errors, setErrors] = useState<string[]>([])
  const [example, setExample] = useState<Example | null>(null)
  const [loading, setLoading] = useState(false)
  const { dataset } = useDataset()
  const history = useHistory()
  const location = useLocation()
  const [lastBody, setLastBody] = useState<Record<string, unknown> | null>(null)

  const raw = rawByVariant[variant.id] ?? initialRaw(variant.fields)
  const setRaw = (next: RawValues) => setRawByVariant((prev) => ({ ...prev, [variant.id]: next }))

  const selectVariant = (id: string) => {
    setParams({ metode: id }, { replace: true })
    setResponse(null)
    setErrors([])
    setExample(null)
  }

  const run = async (rawValues: RawValues = raw, target: Variant = variant, record = true) => {
    const built = buildBody(target.fields, rawValues)
    const errs = [...built.errors]
    let body: Record<string, unknown> = built.body
    if (!errs.length && target.prepareBody) {
      const prepared = target.prepareBody(body, { dataset })
      if (typeof prepared === 'string') errs.push(prepared)
      else body = prepared
    }
    setErrors(errs)
    if (errs.length) return
    setLoading(true)
    try {
      const res = await solve(target.endpoint, body)
      setResponse(res)
      setLastBody(body)
      // baris dataset tidak disimpan di riwayat (bisa besar); dataset aktif dipakai lagi saat dipulihkan
      const { rows: _rows, columns: _cols, ...lean } = body
      if (record) history.add({ path: location.pathname, pageTitle: config.title, variantId: target.id, variantLabel: target.label, endpoint: target.endpoint, raw: rawValues, body: lean, conclusion: res.conclusion ?? null })
    } catch (e) {
      setErrors([e instanceof ApiError ? e.message : 'Terjadi kesalahan tak terduga.'])
    } finally {
      setLoading(false)
    }
  }

  // Pulihkan perhitungan dari halaman Riwayat (?riwayat=<id>)
  const restored = useRef<string | null>(null)
  const restoreId = params.get('riwayat')
  useEffect(() => {
    if (!restoreId || restored.current === restoreId) return
    restored.current = restoreId
    const entry = history.get(restoreId)
    const target = entry && config.variants.find((v) => v.id === entry.variantId)
    if (!entry || !target) return
    // eslint-disable-next-line react/set-state-in-effect -- sinkron satu kali dari parameter URL
    setRawByVariant((prev) => ({ ...prev, [target.id]: entry.raw }))
    setParams({ metode: target.id }, { replace: true })
    void run(entry.raw, target, false)
  }, [restoreId]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadExample = async () => {
    setErrors([])
    try {
      const ex = await getExample(config.exampleModule ?? 'stats', variant.id)
      setExample(ex)
      setRaw(rawFromBody(variant.fields, ex.input))
    } catch (e) {
      setErrors([e instanceof ApiError ? e.message : 'Gagal memuat contoh soal.'])
    }
  }

  const reset = () => {
    setRaw(initialRaw(variant.fields))
    setExample(null)
    setErrors([])
  }

  const visible = variant.fields.filter((f) => isVisible(f, raw))
  const seen = new Set<string>()
  const fields = visible.filter((f) => (seen.has(f.key) ? false : (seen.add(f.key), true)))

  const input = (
    <div className="flex flex-col gap-4">
      {config.variants.length > 1 && (
        <div role="radiogroup" aria-label="Pilih metode" className="flex flex-wrap gap-2">
          {config.variants.map((v) => (
            <button
              key={v.id}
              role="radio"
              aria-checked={v.id === variant.id}
              onClick={() => selectVariant(v.id)}
              className={cn(
                'rounded-full border px-3 py-1.5 text-sm transition-colors',
                v.id === variant.id ? 'border-primary bg-primary text-primary-foreground' : 'bg-card hover:bg-muted',
              )}
            >
              {v.label}
            </button>
          ))}
        </div>
      )}
      <div className="flex flex-col gap-4 rounded-xl border bg-card p-5">
        {variant.description && <p className="text-sm text-muted-foreground">{variant.description}</p>}
        {example && (
          <div className="flex gap-2 rounded-lg bg-muted p-3 text-sm">
            <Info className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
            <div>
              <p className="font-medium">{example.title}</p>
              <p className="text-muted-foreground">{example.description}</p>
            </div>
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          {fields.map((f) => (
            <FieldInput key={f.key} field={f} value={raw[f.key]} raw={raw} onChange={(v) => setRaw({ ...raw, [f.key]: v })} />
          ))}
        </div>
        {errors.length > 0 && (
          <ul role="alert" className="flex flex-col gap-1 rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">
            {errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => run()} disabled={loading}>
            {loading && <Loader2 className="animate-spin" />} Hitung
          </Button>
          <Button variant="outline" onClick={loadExample}>
            <Sparkles /> Muat Contoh Soal
          </Button>
          <Button variant="ghost" onClick={reset}>
            <RotateCcw /> Kosongkan
          </Button>
        </div>
      </div>
    </div>
  )

  return (
    <MethodPage
      title={config.title}
      subtitle={config.subtitle}
      input={input}
      result={response && <ResultView response={response} name={variant.label} />}
      response={response}
      theory={variant.theory}
      onReport={response ? () => openReport({ pageTitle: config.title, variantLabel: variant.label, input: lastBody ?? {}, response }) : undefined}
    />
  )
}
