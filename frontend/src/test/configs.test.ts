import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { anovaConfig } from '@/pages/stats/configs/anova'
import { descriptiveConfig } from '@/pages/stats/configs/descriptive'
import { distributionsConfig } from '@/pages/stats/configs/distributions'
import { inferentialConfig } from '@/pages/stats/configs/inferential'
import { nonparametricConfig } from '@/pages/stats/configs/nonparametric'
import { normalityConfig } from '@/pages/stats/configs/normality'
import { regressionConfig } from '@/pages/stats/configs/regression'

const configs = [descriptiveConfig, distributionsConfig, inferentialConfig, anovaConfig, regressionConfig, nonparametricConfig, normalityConfig]
const examplesDir = resolve(import.meta.dirname, '../../../backend/app/examples/stats')

describe('konfigurasi halaman statistik', () => {
  const variants = configs.flatMap((c) => c.variants)

  it('id varian unik', () => {
    const ids = variants.map((v) => v.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it.each(variants.map((v) => [v.id]))('varian %s punya contoh soal di backend', (id) => {
    expect(existsSync(resolve(examplesDir, `${id}.json`))).toBe(true)
  })
})
