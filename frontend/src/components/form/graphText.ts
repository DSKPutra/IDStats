/** Konversi dua arah antara teks busur (“A B 7”) dan struktur graf untuk editor visual. */

export interface GraphEdge {
  id: string
  source: string
  target: string
  values: string[]
}

export interface ParsedGraph {
  nodes: string[]
  edges: GraphEdge[]
}

export function parseGraphText(text: string, valueCount: number): ParsedGraph {
  const nodes: string[] = []
  const edges: GraphEdge[] = []
  text.split('\n').forEach((raw, i) => {
    const line = raw.split('#')[0].trim()
    if (!line) return
    const parts = line.split(/[\s,;|]+|->/).filter(Boolean)
    if (parts.length < 2) return
    const [source, target, ...rest] = parts
    for (const n of [source, target]) if (!nodes.includes(n)) nodes.push(n)
    const values = Array.from({ length: valueCount }, (_, k) => rest[k] ?? (k === 1 ? 'inf' : '1'))
    edges.push({ id: `e${i}-${source}-${target}`, source, target, values })
  })
  return { nodes, edges }
}

export function graphToText(edges: GraphEdge[]): string {
  return edges.map((e) => [e.source, e.target, ...e.values].join(' ')).join('\n')
}

/** Tata letak berlapis (BFS dari node pertama) — sama dengan gambar hasil di backend. */
export function layeredLayout(nodes: string[], edges: GraphEdge[]): Record<string, { x: number; y: number }> {
  const adj = new Map<string, Set<string>>(nodes.map((n) => [n, new Set()]))
  for (const e of edges) {
    adj.get(e.source)?.add(e.target)
    adj.get(e.target)?.add(e.source)
  }
  const layer = new Map<string, number>()
  if (nodes.length) {
    layer.set(nodes[0], 0)
    const queue = [nodes[0]]
    while (queue.length) {
      const x = queue.shift()!
      for (const y of adj.get(x) ?? []) {
        if (!layer.has(y)) {
          layer.set(y, layer.get(x)! + 1)
          queue.push(y)
        }
      }
    }
  }
  const extra = Math.max(0, ...layer.values()) + 1
  const groups = new Map<number, string[]>()
  for (const n of nodes) {
    const l = layer.get(n) ?? extra
    groups.set(l, [...(groups.get(l) ?? []), n])
  }
  const pos: Record<string, { x: number; y: number }> = {}
  for (const [l, members] of groups) members.forEach((n, i) => (pos[n] = { x: l * 160, y: (i - (members.length - 1) / 2) * 110 }))
  return pos
}
