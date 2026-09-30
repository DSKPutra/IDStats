import { Check, ClipboardPaste, FileDown, Loader2, Plus, Sparkles, Upload, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { EditableTable } from '@/components/solver/EditableTable'
import { MethodPage } from '@/components/solver/MethodPage'
import { ResultView } from '@/components/solver/ResultView'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useDataset, type Cell } from '@/context/DatasetContext'
import { ApiError, solve, uploadFile, type SolverResponse } from '@/lib/api'
import { downloadText, toCsv } from '@/lib/export'
import { Theory } from './configs/Theory'

interface DatasetResult {
  columns: string[]
  rows: Cell[][]
  n_rows: number
}

const EXAMPLE_CSV = `nama,jam_belajar,nilai,kehadiran
Andi,5,72,90
Budi,7,85,95
Citra,3,,80
Dewi,8,90,100
Eka,6,78,
Fajar,4,64,85
Gita,9,95,98
Hadi,2,210,70
Intan,6,80,92
Joko,5,74,88`

const selectClass = 'h-9 rounded-md border bg-card px-3 text-sm'

export function DataManagementPage() {
  const { dataset, setDataset, numericColumns } = useDataset()
  const [response, setResponse] = useState<SolverResponse<DatasetResult> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [pasteText, setPasteText] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const [missing, setMissing] = useState('none')
  const [outlier, setOutlier] = useState('none')
  const [outlierAction, setOutlierAction] = useState('flag')
  const [transformMethod, setTransformMethod] = useState('zscore')
  const [targets, setTargets] = useState<string[]>([])

  const call = async (fn: () => Promise<SolverResponse<DatasetResult>>, name: string, applyNow: boolean) => {
    setError(null)
    setBusy(true)
    try {
      const res = await fn()
      setResponse(res)
      if (applyNow) setDataset({ name, columns: res.result.columns, rows: res.result.rows })
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Terjadi kesalahan tak terduga.')
    } finally {
      setBusy(false)
    }
  }

  const uploadBlob = (file: File) => call(() => uploadFile<DatasetResult>('/data/upload', file), file.name, true)

  const selectedTargets = targets.filter((t) => numericColumns.includes(t))
  const body = () => ({ columns: dataset!.columns, rows: dataset!.rows })

  const input = (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 rounded-xl border bg-card p-5">
        <h2 className="font-semibold">1. Muat data</h2>
        <div className="flex flex-wrap gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.txt,.tsv,.xlsx,.xls"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) uploadBlob(f)
              e.target.value = ''
            }}
          />
          <Button onClick={() => fileRef.current?.click()} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" /> : <Upload />} Unggah CSV / XLSX
          </Button>
          <Button variant="outline" onClick={() => setPasteOpen((o) => !o)}>
            <ClipboardPaste /> Tempel data
          </Button>
          <Button variant="outline" onClick={() => uploadBlob(new File([EXAMPLE_CSV], 'contoh-nilai-mahasiswa.csv'))}>
            <Sparkles /> Muat Contoh Soal
          </Button>
          {dataset && (
            <Button variant="ghost" onClick={() => setDataset(null)}>
              <X /> Hapus dataset
            </Button>
          )}
        </div>
        {pasteOpen && (
          <div className="flex flex-col gap-2">
            <Textarea
              aria-label="Tempel data dengan baris judul"
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder={'Baris pertama = nama kolom. Salin langsung dari Excel atau CSV.\nnama\tnilai\nAndi\t72'}
            />
            <Button
              className="self-start"
              disabled={!pasteText.trim() || busy}
              onClick={() => uploadBlob(new File([pasteText], 'tempel.csv'))}
            >
              <Check /> Gunakan data ini
            </Button>
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          Dataset aktif dapat dipakai di semua halaman statistik lewat tombol “Isi dari kolom dataset”. Data hanya disimpan
          di browser Anda.
        </p>
        {error && (
          <p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}
      </div>

      {dataset && (
        <>
          <div className="flex flex-col gap-3 rounded-xl border bg-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">
                2. Dataset aktif: {dataset.name}{' '}
                <span className="font-normal text-muted-foreground">
                  ({dataset.rows.length} baris × {dataset.columns.length} kolom)
                </span>
              </h2>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setDataset({ ...dataset, rows: [...dataset.rows, dataset.columns.map(() => null)] })}>
                  <Plus /> Baris
                </Button>
                <Button variant="outline" size="sm" onClick={() => downloadText(`${dataset.name.replace(/\.\w+$/, '')}.csv`, toCsv(dataset.columns, dataset.rows))}>
                  <FileDown /> CSV
                </Button>
              </div>
            </div>
            <EditableTable dataset={dataset} onChange={setDataset} />
          </div>

          <div className="flex flex-col gap-4 rounded-xl border bg-card p-5">
            <h2 className="font-semibold">3. Olah data</h2>
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-1 text-sm font-medium">Kolom numerik yang diproses</legend>
              <div className="flex flex-wrap gap-3">
                {numericColumns.map((c) => (
                  <label key={c} className="flex items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      className="size-4 accent-primary"
                      checked={selectedTargets.includes(c)}
                      onChange={(e) => setTargets(e.target.checked ? [...selectedTargets, c] : selectedTargets.filter((t) => t !== c))}
                    />
                    {c}
                  </label>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">Tidak dicentang = semua kolom numerik (untuk pembersihan).</p>
            </fieldset>

            <div className="grid gap-3 sm:grid-cols-3">
              <label className="flex flex-col gap-1.5 text-sm font-medium">
                Nilai kosong (missing)
                <select className={selectClass} value={missing} onChange={(e) => setMissing(e.target.value)}>
                  <option value="none">Biarkan</option>
                  <option value="drop">Hapus baris</option>
                  <option value="mean">Isi rata-rata</option>
                  <option value="median">Isi median</option>
                  <option value="mode">Isi modus</option>
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-sm font-medium">
                Deteksi outlier
                <select className={selectClass} value={outlier} onChange={(e) => setOutlier(e.target.value)}>
                  <option value="none">Tidak</option>
                  <option value="iqr">IQR (1,5 × IQR)</option>
                  <option value="zscore">z-score (|z| &gt; 3)</option>
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-sm font-medium">
                Tindakan outlier
                <select className={selectClass} value={outlierAction} onChange={(e) => setOutlierAction(e.target.value)} disabled={outlier === 'none'}>
                  <option value="flag">Tandai saja</option>
                  <option value="remove">Hapus baris</option>
                  <option value="winsorize">Winsorisasi</option>
                </select>
              </label>
            </div>
            <Button
              className="self-start"
              disabled={busy}
              onClick={() =>
                call(
                  () =>
                    solve<DatasetResult>('/data/clean', {
                      ...body(),
                      missing,
                      outlier,
                      outlier_action: outlierAction,
                      target_columns: selectedTargets.length ? selectedTargets : null,
                    }),
                  dataset.name,
                  false,
                )
              }
            >
              Bersihkan data
            </Button>

            <div className="flex flex-wrap items-end gap-3 border-t pt-4">
              <label className="flex flex-col gap-1.5 text-sm font-medium">
                Transformasi
                <select className={selectClass} value={transformMethod} onChange={(e) => setTransformMethod(e.target.value)}>
                  <option value="zscore">Standardisasi (z-score)</option>
                  <option value="minmax">Normalisasi min-max</option>
                  <option value="log">Logaritma natural</option>
                  <option value="log10">Logaritma basis 10</option>
                  <option value="sqrt">Akar kuadrat</option>
                </select>
              </label>
              <Button
                disabled={busy || !selectedTargets.length}
                onClick={() => call(() => solve<DatasetResult>('/data/transform', { ...body(), targets: selectedTargets, method: transformMethod }), dataset.name, false)}
              >
                Transformasi kolom terpilih
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )

  const result = response && (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-card p-4">
        <p className="text-sm">
          Hasil: <strong>{response.result.n_rows}</strong> baris × <strong>{response.result.columns.length}</strong> kolom.
        </p>
        <Button onClick={() => setDataset({ name: dataset?.name ?? 'dataset', columns: response.result.columns, rows: response.result.rows })}>
          <Check /> Terapkan ke dataset aktif
        </Button>
      </div>
      <ResultView response={response} name="data" />
    </div>
  )

  return (
    <MethodPage
      title="Manajemen Data (Data Management)"
      subtitle="Unggah CSV/Excel, edit tabel, tangani nilai kosong & outlier, dan transformasi variabel."
      input={input}
      result={result}
      response={response}
      theory={
        <Theory formulas={[String.raw`\text{Outlier (IQR): } x < Q_1 - 1{,}5\,IQR \ \text{atau}\ x > Q_3 + 1{,}5\,IQR`, String.raw`z = \frac{x-\bar{x}}{s}`]}>
          <p>
            <strong>Nilai kosong</strong> bisa dihapus (listwise deletion) atau diisi (imputasi). Imputasi rata-rata
            menjaga ukuran sampel tetapi mengecilkan varians. <strong>Outlier</strong> dideteksi dengan aturan IQR (tahan
            terhadap outlier itu sendiri) atau z-score. Winsorisasi memotong outlier ke batas wajar tanpa membuang baris.
          </p>
          <p>
            <strong>Transformasi</strong>: standardisasi membuat rata-rata 0 dan simpangan baku 1; log atau akar kuadrat
            mengurangi kemencengan positif.
          </p>
        </Theory>
      }
    />
  )
}
