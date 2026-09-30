import { describe, expect, it } from 'vitest'
import { toCsv } from '@/lib/export'
import { parseNumbers } from '@/lib/utils'

describe('parseNumbers', () => {
  it('menerima berbagai pemisah', () => {
    expect(parseNumbers('1, 2;3\n4\t5  6.5').values).toEqual([1, 2, 3, 4, 5, 6.5])
  })
  it('melaporkan token yang bukan angka', () => {
    expect(parseNumbers('1 abc 2').invalid).toEqual(['abc'])
  })
})

describe('toCsv', () => {
  it('meng-escape sel yang mengandung koma', () => {
    expect(toCsv(['a', 'b'], [['x,y', 2]])).toBe('a,b\n"x,y",2')
  })
})
