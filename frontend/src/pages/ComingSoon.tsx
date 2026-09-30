import { Construction } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import type { CategoryInfo, MethodInfo } from '@/registry/modules'

export function ComingSoon({ category, method }: { category: CategoryInfo; method: MethodInfo }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center py-16 text-center">
      <Construction className="size-10 text-muted-foreground" />
      <p className="mt-4 text-sm text-muted-foreground">{category.title}</p>
      <h1 className="mt-1 text-2xl font-semibold">{method.title}</h1>
      <p className="mt-3 text-muted-foreground">
        Metode ini sedang dikembangkan dan dijadwalkan rilis pada <strong>Fase {method.phase}</strong>.
      </p>
      <Button asChild variant="outline" className="mt-6">
        <Link to="/">Kembali ke beranda</Link>
      </Button>
    </div>
  )
}
