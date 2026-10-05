import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Connection,
  type Edge,
  type Node,
  type NodeChange,
  applyNodeChanges,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Plus, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useIsDark } from '@/components/layout/useIsDark'
import { Button } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/textarea'
import { graphToText, layeredLayout, parseGraphText, type GraphEdge } from './graphText'

interface GraphEditorProps {
  id: string
  value: string
  onChange: (v: string) => void
  valueCount: number
  directed: boolean
  placeholder?: string
}

const VALUE_LABELS: Record<number, string[]> = { 1: ['Bobot / kapasitas'], 2: ['Biaya', 'Kapasitas'] }

/** Editor graf visual: teks busur tetap menjadi sumber data; kanvas React Flow untuk menggambar & mengedit. */
export function GraphEditor({ id, value, onChange, valueCount, directed, placeholder }: GraphEditorProps) {
  const dark = useIsDark()
  const parsed = useMemo(() => parseGraphText(value, valueCount), [value, valueCount])
  const [extraNodes, setExtraNodes] = useState<string[]>([])
  // State node lengkap (posisi + ukuran terukur) agar React Flow mode terkendali dapat menampilkan node.
  const [nodeState, setNodeState] = useState<Record<string, Node>>({})
  const [selected, setSelected] = useState<string | null>(null)
  const [newNode, setNewNode] = useState('')

  const allNodes = [...parsed.nodes, ...extraNodes.filter((n) => !parsed.nodes.includes(n))]
  const nodesKey = allNodes.join('\u0000')
  const auto = useMemo(() => layeredLayout(nodesKey ? nodesKey.split('\u0000') : [], parsed.edges), [nodesKey, parsed.edges])

  const nodes: Node[] = allNodes.map((n, i) => ({
    ...nodeState[n],
    id: n,
    position: nodeState[n]?.position ?? auto[n] ?? { x: i * 120, y: 0 },
    data: { label: n },
    style: { width: 44, height: 44, borderRadius: 22, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0, fontWeight: 600, background: 'var(--primary)', color: 'var(--primary-foreground)', border: '2px solid var(--card)' },
  }))
  const edges: Edge[] = parsed.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.values.join(' / '),
    selected: e.id === selected,
    markerEnd: directed ? { type: MarkerType.ArrowClosed } : undefined,
    style: { strokeWidth: e.id === selected ? 3 : 1.5 },
    labelBgStyle: { fill: 'var(--card)' },
    labelStyle: { fill: 'var(--foreground)', fontSize: 12 },
  }))

  const emit = (next: GraphEdge[]) => onChange(graphToText(next))
  const selectedEdge = parsed.edges.find((e) => e.id === selected)

  const onConnect = (c: Connection) => {
    if (!c.source || !c.target || c.source === c.target) return
    emit([...parsed.edges, { id: `new-${Date.now()}`, source: c.source, target: c.target, values: Array.from({ length: valueCount }, (_, k) => (k === 1 ? 'inf' : '1')) }])
  }

  const onNodesChange = (changes: NodeChange[]) => {
    const next = applyNodeChanges(changes, nodes)
    setNodeState(Object.fromEntries(next.map((n) => [n.id, n])))
  }

  const addNode = () => {
    const name = newNode.trim().replace(/\s+/g, '_')
    if (!name || allNodes.includes(name)) return
    setExtraNodes([...extraNodes, name])
    setNewNode('')
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="h-80 overflow-hidden rounded-md border bg-card" aria-label="Editor graf visual">
        <ReactFlow
          key={nodesKey}
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onConnect={onConnect}
          onEdgeClick={(_, e) => setSelected(e.id)}
          onPaneClick={() => setSelected(null)}
          fitView
          colorMode={dark ? 'dark' : 'light'}
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="flex flex-wrap items-end gap-2">
        <Input className="w-36" aria-label="Nama node baru" placeholder="Nama node baru" value={newNode} onChange={(e) => setNewNode(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addNode())} />
        <Button variant="outline" size="sm" onClick={addNode}>
          <Plus /> Node
        </Button>
        <span className="text-xs text-muted-foreground">Tarik dari tepi satu node ke node lain untuk membuat busur; klik busur untuk mengubah nilainya.</span>
      </div>
      {selectedEdge && (
        <div className="flex flex-wrap items-end gap-2 rounded-md border bg-muted p-2">
          <span className="text-sm font-medium">
            Busur {selectedEdge.source} {directed ? '→' : '–'} {selectedEdge.target}
          </span>
          {selectedEdge.values.map((v, k) => (
            <label key={k} className="flex flex-col gap-1 text-xs">
              {VALUE_LABELS[valueCount]?.[k] ?? `Nilai ${k + 1}`}
              <Input
                className="h-8 w-24"
                value={v}
                onChange={(e) => emit(parsed.edges.map((x) => (x.id === selectedEdge.id ? { ...x, values: x.values.map((y, kk) => (kk === k ? e.target.value.trim() || '0' : y)) } : x)))}
              />
            </label>
          ))}
          <Button variant="ghost" size="sm" onClick={() => (emit(parsed.edges.filter((x) => x.id !== selectedEdge.id)), setSelected(null))}>
            <Trash2 /> Hapus busur
          </Button>
        </div>
      )}
      <Textarea id={id} className="min-h-28" spellCheck={false} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} aria-label="Daftar busur (teks)" />
    </div>
  )
}
