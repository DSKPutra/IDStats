import { lazy, Suspense, type ComponentType } from 'react'
import { useParams } from 'react-router-dom'
import { findMethod } from '@/registry/modules'
import { ComingSoon } from './ComingSoon'
import { NotFound } from './NotFound'

/** Halaman yang sudah diimplementasikan, dengan kunci `${kategori}/${metode}`. */
const pages: Record<string, ComponentType> = {
  'stats/descriptive': lazy(() => import('./stats/Descriptive').then((m) => ({ default: m.DescriptivePage }))),
}

export function MethodRoute() {
  const { categoryId = '', methodId = '' } = useParams()
  const found = findMethod(categoryId, methodId)
  if (!found) return <NotFound />
  const Page = pages[`${categoryId}/${methodId}`]
  if (!Page) return <ComingSoon {...found} />
  return (
    <Suspense fallback={<p className="py-10 text-center text-muted-foreground">Memuat…</p>}>
      <Page />
    </Suspense>
  )
}
