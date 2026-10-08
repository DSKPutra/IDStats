import { Download, FileText, RotateCcw, Search, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/textarea'
import { useHistory } from '@/context/HistoryContext'
import { solve, ApiError } from '@/lib/api'
import { downloadText } from '@/lib/export'
import { openReport } from '@/lib/report'

export function HistoryPage({ reportMode = false }: { reportMode?: boolean }) {
  const { entries, remove, clear } = useHistory()
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const filtered = entries.filter((e) => `${e.pageTitle} ${e.variantLabel} ${e.conclusion ?? ''}`.toLowerCase().includes(q.toLowerCase()))

  const report = async (id: string) => {
    const e = entries.find((x) => x.id === id)
    if (!e) return
    setBusy(id)
    setError(null)
    try {
      if (!e.endpoint) throw new ApiError('Riwayat lama ini belum menyimpan endpoint. Buka perhitungan lalu klik “Laporan PDF”.')
      const res = await solve(e.endpoint, e.body)
      openReport({ pageTitle: e.pageTitle, variantLabel: e.variantLabel, input: e.body, response: res })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Gagal membuat laporan. Buka perhitungan lalu klik “Laporan PDF”.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{reportMode ? 'Ekspor Laporan PDF' : 'Riwayat Perhitungan (History)'}</h1>
        <p className="mt-1 text-muted-foreground">
          {reportMode
            ? 'Laporan berisi input, hasil, langkah penyelesaian, dan grafik — siap dicetak atau disimpan sebagai PDF untuk tugas kuliah. Klik “Laporan PDF” di halaman metode mana pun, atau pilih perhitungan dari riwayat di bawah.'
            : 'Setiap perhitungan yang berhasil tersimpan otomatis di browser Anda (maksimal 100 terakhir, tidak dikirim ke server). Buka kembali untuk melihat hasil atau mengubah input.'}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="relative w-full max-w-sm">
          <span className="sr-only">Cari riwayat</span>
          <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Cari judul atau kesimpulan…" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        {!reportMode && entries.length > 0 && (
          <>
            <Button variant="outline" size="sm" onClick={() => downloadText('idstats-riwayat.json', JSON.stringify(entries, null, 2), 'application/json')}>
              <Download /> Ekspor JSON
            </Button>
            <Button variant="ghost" size="sm" onClick={() => window.confirm('Hapus semua riwayat?') && clear()}>
              <Trash2 /> Hapus semua
            </Button>
          </>
        )}
      </div>
      {error && <p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
      {filtered.length === 0 ? (
        <p className="rounded-xl border bg-card p-8 text-center text-muted-foreground">
          {entries.length ? 'Tidak ada riwayat yang cocok.' : 'Belum ada perhitungan. Jalankan metode apa pun dan hasilnya akan muncul di sini.'}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {filtered.map((e) => (
            <li key={e.id} className="flex flex-col gap-2 rounded-xl border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="font-medium">
                  {e.pageTitle} <span className="text-muted-foreground">· {e.variantLabel}</span>
                </p>
                {e.conclusion && <p className="line-clamp-2 text-sm text-muted-foreground">{e.conclusion}</p>}
                <p className="text-xs text-muted-foreground">{new Date(e.at).toLocaleString('id-ID')}</p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button asChild variant="outline" size="sm">
                  <Link to={`${e.path}?metode=${encodeURIComponent(e.variantId)}&riwayat=${encodeURIComponent(e.id)}`}>
                    <RotateCcw /> Buka
                  </Link>
                </Button>
                <Button variant="outline" size="sm" disabled={busy === e.id} onClick={() => report(e.id)}>
                  <FileText /> PDF
                </Button>
                {!reportMode && (
                  <Button variant="ghost" size="icon" aria-label="Hapus" onClick={() => remove(e.id)}>
                    <Trash2 />
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
