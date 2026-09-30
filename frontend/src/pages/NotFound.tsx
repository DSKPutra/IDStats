import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export function NotFound() {
  return (
    <div className="mx-auto max-w-xl py-16 text-center">
      <h1 className="text-2xl font-semibold">Halaman tidak ditemukan</h1>
      <p className="mt-2 text-muted-foreground">Alamat yang Anda buka tidak ada di IDStats.</p>
      <Button asChild variant="outline" className="mt-6">
        <Link to="/">Kembali ke beranda</Link>
      </Button>
    </div>
  )
}
