import { describe, expect, it } from 'vitest'
import { graphToText, layeredLayout, parseGraphText } from '@/components/form/graphText'

describe('graphText', () => {
  it('parse dan tulis ulang busur secara konsisten', () => {
    const g = parseGraphText('O A 2\nA, B, 3\n# komentar\nB -> T 1', 1)
    expect(g.nodes).toEqual(['O', 'A', 'B', 'T'])
    expect(graphToText(g.edges)).toBe('O A 2\nA B 3\nB T 1')
  })

  it('mengisi nilai default untuk busur dua nilai', () => {
    expect(parseGraphText('A B 4', 2).edges[0].values).toEqual(['4', 'inf'])
  })

  it('tata letak berlapis dari node pertama', () => {
    const g = parseGraphText('O A 1\nO B 1\nA T 1', 1)
    const pos = layeredLayout(g.nodes, g.edges)
    expect(pos.O.x).toBe(0)
    expect(pos.A.x).toBe(160)
    expect(pos.T.x).toBe(320)
  })
})
