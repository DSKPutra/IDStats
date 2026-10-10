import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import * as advanced from '@/pages/or/configs/advanced'
import * as lp from '@/pages/or/configs/lp'
import * as mlGradient from '@/pages/ml/configs/gradient'
import * as mlMeta from '@/pages/ml/configs/meta'
import * as stochastic from '@/pages/or/configs/stochastic'
import { networkConfig } from '@/pages/or/configs/network'
import { projectConfig } from '@/pages/or/configs/project'
import { transportConfig } from '@/pages/or/configs/transport'
import { anovaConfig } from '@/pages/stats/configs/anova'
import { descriptiveConfig } from '@/pages/stats/configs/descriptive'
import { distributionsConfig } from '@/pages/stats/configs/distributions'
import { inferentialConfig } from '@/pages/stats/configs/inferential'
import { nonparametricConfig } from '@/pages/stats/configs/nonparametric'
import { normalityConfig } from '@/pages/stats/configs/normality'
import { regressionConfig } from '@/pages/stats/configs/regression'
import type { VariantPageConfig } from '@/pages/VariantPage'

const configs: VariantPageConfig[] = [
  descriptiveConfig, distributionsConfig, inferentialConfig, anovaConfig, regressionConfig, nonparametricConfig, normalityConfig,
  ...Object.values(lp), transportConfig, networkConfig, projectConfig, ...Object.values(advanced), ...Object.values(stochastic), ...Object.values(mlGradient), ...Object.values(mlMeta),
]
const examplesRoot = resolve(import.meta.dirname, '../../../backend/app/examples')

describe('konfigurasi halaman metode', () => {
  const variants = configs.flatMap((c) => c.variants.map((v) => ({ ...v, module: c.exampleModule ?? 'stats' })))

  it('id varian unik', () => {
    const ids = variants.map((v) => `${v.module}/${v.id}`)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it.each(variants.map((v) => [`${v.module}/${v.id}`, v]))('%s punya contoh soal dengan endpoint yang sama', (_, v) => {
    const file = resolve(examplesRoot, v.module, `${v.id}.json`)
    expect(existsSync(file)).toBe(true)
    expect(JSON.parse(readFileSync(file, 'utf-8')).endpoint).toBe(v.endpoint)
  })
})

describe('fixture soal cerita backend (tests/story_pages.json)', () => {
  const fixture = JSON.parse(readFileSync(resolve(import.meta.dirname, '../../../backend/tests/story_pages.json'), 'utf-8')) as Record<
    string,
    { title: string; variants: { id: string; fields: { key: string; type: string }[] }[] }
  >

  it.each(Object.values(fixture).map((p) => [p.title, p]))('%s sinkron dengan konfigurasi halaman', (title, page) => {
    const config = configs.find((c) => c.title === title)
    expect(config).toBeDefined()
    const actual = config!.variants.map((v) => ({ id: v.id, fields: v.fields.filter((f) => !f.virtual).map((f) => ({ key: f.key, type: f.type })) }))
    expect(page.variants.map((v) => ({ id: v.id, fields: v.fields.map((f) => ({ key: f.key, type: f.type })) }))).toEqual(actual)
  })
})
