import { useEffect, useState } from 'react'
import { Latex } from '@/components/solver/Latex'
import { Input } from '@/components/ui/textarea'
import { getJson } from '@/lib/api'
import { cn } from '@/lib/utils'
import { optimizerLines, parseOptimizerLines, type OptimizerChoice } from './fields'

interface CatalogItem {
  id: string
  title: string
  formula: string
  defaults: Record<string, number>
  notes: string
}

let catalogPromise: Promise<CatalogItem[]> | undefined

/** Pilih optimizer (centang) dan atur hiperparameternya; nilai disimpan sebagai baris teks. */
export function OptimizerPicker({ id, value, onChange, max }: { id: string; value: string; onChange: (v: string) => void; max: number }) {
  const [catalog, setCatalog] = useState<CatalogItem[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    catalogPromise ??= getJson<CatalogItem[]>('/ml/optimizers')
    catalogPromise.then(setCatalog).catch(() => setError('Gagal memuat daftar optimizer.'))
  }, [])
  const parsed = parseOptimizerLines(value)
  const chosen: OptimizerChoice[] = parsed.ok ? parsed.value : []
  const byId = new Map(chosen.map((c) => [c.id, c]))
  const update = (next: OptimizerChoice[]) => onChange(optimizerLines(next))

  return (
    <div id={id} className="flex flex-col gap-2">
      {error && <p className="text-sm text-danger">{error}</p>}
      <p className="text-xs text-muted-foreground">
        Dipilih {chosen.length} dari maksimal {max}. Hiperparameter yang tidak diubah memakai nilai default.
      </p>
      <div className="grid gap-2 lg:grid-cols-2">
        {catalog.map((o) => {
          const sel = byId.get(o.id)
          return (
            <div key={o.id} className={cn('rounded-lg border p-3', sel && 'border-primary bg-accent/40')}>
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  type="checkbox"
                  className="size-4 accent-primary"
                  checked={Boolean(sel)}
                  disabled={!sel && chosen.length >= max}
                  onChange={(e) => update(e.target.checked ? [...chosen, { id: o.id, params: { lr: o.defaults.lr } }] : chosen.filter((c) => c.id !== o.id))}
                />
                {o.title}
              </label>
              {sel && (
                <div className="mt-2 flex flex-col gap-2">
                  <div className="overflow-x-auto text-xs">
                    <Latex>{o.formula}</Latex>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(o.defaults).map(([k, def]) => (
                      <label key={k} className="flex flex-col gap-0.5 text-[11px] text-muted-foreground">
                        {k}
                        <Input
                          className="h-7 px-2 text-xs"
                          inputMode="decimal"
                          defaultValue={String(sel.params[k] ?? def)}
                          onBlur={(e) => {
                            const n = Number(e.target.value)
                            if (!Number.isFinite(n)) return
                            const params = { ...sel.params }
                            if (n === def && k !== 'lr') delete params[k]
                            else params[k] = n
                            update(chosen.map((c) => (c.id === o.id ? { ...c, params } : c)))
                          }}
                        />
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
