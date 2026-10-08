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
  'ml/gradient-playground': variantPage(() => import('./ml/configs/gradient').then((m) => m.playgroundConfig)),
  'ml/metaheuristics': variantPage(() => import('./ml/configs/meta').then((m) => m.populationConfig)),
  'ml/metaheuristic-benchmark': variantPage(() => import('./ml/configs/meta').then((m) => m.benchmarkConfig)),
  'ml/hyperparameter-optimization': variantPage(() => import('./ml/configs/meta').then((m) => m.hpoConfig)),
  'ml/feature-selection': variantPage(() => import('./ml/configs/meta').then((m) => m.featureConfig)),
  'ml/metaheuristic-or': variantPage(() => import('./ml/configs/meta').then((m) => m.metaOrConfig)),
  'ml/reinforcement-learning': variantPage(() => import('./ml/configs/meta').then((m) => m.rlConfig)),
  'ml/ml-review': lazy(() => import('./ml/MlReview').then((m) => ({ default: m.MlReviewPage }))),
  'ml/gradient-training': variantPage(() => import('./ml/configs/gradient').then((m) => m.trainingConfig)),
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
  'or/dynamic-programming': variantPage(() => import('./or/configs/advanced').then((m) => m.dpConfig)),
  'or/integer-programming': variantPage(() => import('./or/configs/advanced').then((m) => m.ipConfig)),
  'or/nonlinear-programming': variantPage(() => import('./or/configs/advanced').then((m) => m.nlpConfig)),
  'or/game-theory': variantPage(() => import('./or/configs/advanced').then((m) => m.gameConfig)),
  'or/decision-analysis': variantPage(() => import('./or/configs/stochastic').then((m) => m.decisionConfig)),
  'or/markov-chains': variantPage(() => import('./or/configs/stochastic').then((m) => m.markovConfig)),
  'or/queueing': variantPage(() => import('./or/configs/stochastic').then((m) => m.queueConfig)),
  'or/inventory': variantPage(() => import('./or/configs/stochastic').then((m) => m.inventoryConfig)),
  'or/forecasting': variantPage(() => import('./or/configs/stochastic').then((m) => m.forecastConfig)),
  'or/mdp': variantPage(() => import('./or/configs/stochastic').then((m) => m.mdpConfig)),
  'or/simulation': variantPage(() => import('./or/configs/stochastic').then((m) => m.simulationConfig)),
  'general/history': lazy(() => import('./general/History').then((m) => ({ default: () => <m.HistoryPage /> }))),
  'general/pdf-report': lazy(() => import('./general/History').then((m) => ({ default: () => <m.HistoryPage reportMode /> }))),
  'general/practice': lazy(() => import('./general/Practice').then((m) => ({ default: m.PracticePage }))),
  'or/appendix': variantPage(() => import('./or/configs/stochastic').then((m) => m.appendixConfig)),
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
