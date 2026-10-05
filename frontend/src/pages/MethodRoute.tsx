import { lazy, Suspense, type ComponentType } from 'react'
import { useParams } from 'react-router-dom'
import { findMethod } from '@/registry/modules'
import { ComingSoon } from './ComingSoon'
import { NotFound } from './NotFound'
import type { VariantPageConfig } from './VariantPage'

const variantPage = (load: () => Promise<VariantPageConfig>): ComponentType =>
  lazy(async () => {
    const [{ VariantPage }, config] = await Promise.all([import('./VariantPage'), load()])
    return { default: () => <VariantPage config={config} /> }
  })

/** Halaman yang sudah diimplementasikan, dengan kunci `${kategori}/${metode}`. */
const pages: Record<string, ComponentType> = {
  'stats/data-management': lazy(() => import('./stats/DataManagement').then((m) => ({ default: m.DataManagementPage }))),
  'stats/descriptive': variantPage(() => import('./stats/configs/descriptive').then((m) => m.descriptiveConfig)),
  'stats/distributions': variantPage(() => import('./stats/configs/distributions').then((m) => m.distributionsConfig)),
  'stats/inferential': variantPage(() => import('./stats/configs/inferential').then((m) => m.inferentialConfig)),
  'stats/anova': variantPage(() => import('./stats/configs/anova').then((m) => m.anovaConfig)),
  'stats/regression': variantPage(() => import('./stats/configs/regression').then((m) => m.regressionConfig)),
  'stats/nonparametric': variantPage(() => import('./stats/configs/nonparametric').then((m) => m.nonparametricConfig)),
  'stats/normality': variantPage(() => import('./stats/configs/normality').then((m) => m.normalityConfig)),
  'or/or-intro': lazy(() => import('./or/OrIntro').then((m) => ({ default: m.OrIntroPage }))),
  'or/lp-graphical': variantPage(() => import('./or/configs/lp').then((m) => m.lpGraphicalConfig)),
  'or/simplex': variantPage(() => import('./or/configs/lp').then((m) => m.simplexConfig)),
  'or/revised-simplex': variantPage(() => import('./or/configs/lp').then((m) => m.revisedSimplexConfig)),
  'or/duality': variantPage(() => import('./or/configs/lp').then((m) => m.dualityConfig)),
  'or/lp-other': variantPage(() => import('./or/configs/lp').then((m) => m.lpOtherConfig)),
  'or/transportation': variantPage(() => import('./or/configs/transport').then((m) => m.transportConfig)),
  'or/network': variantPage(() => import('./or/configs/network').then((m) => m.networkConfig)),
  'or/pert-cpm': variantPage(() => import('./or/configs/project').then((m) => m.projectConfig)),
}

export function MethodRoute() {
  const { categoryId = '', methodId = '' } = useParams()
  const found = findMethod(categoryId, methodId)
  if (!found) return <NotFound />
  const Page = pages[`${categoryId}/${methodId}`]
  if (!Page) return <ComingSoon {...found} />
  return (
    <Suspense fallback={<p className="py-10 text-center text-muted-foreground">Memuat…</p>}>
      <Page key={`${categoryId}/${methodId}`} />
    </Suspense>
  )
}
