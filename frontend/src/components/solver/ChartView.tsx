import { Download } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import type { SolverChart } from '@/lib/api'

type PlotlyModule = typeof import('plotly.js-dist-min').default
let plotlyPromise: Promise<PlotlyModule> | undefined
const loadPlotly = () => (plotlyPromise ??= import('plotly.js-dist-min').then((m) => m.default))

function themedLayout(layout: Record<string, unknown> = {}) {
  const style = getComputedStyle(document.documentElement)
  const fg = style.getPropertyValue('--foreground').trim()
  const grid = style.getPropertyValue('--border').trim()
  const card = style.getPropertyValue('--card').trim()
  // Label anotasi berlatar (mis. bobot busur) mengikuti warna kartu agar terbaca di mode gelap.
  const annotations = Array.isArray(layout.annotations)
    ? (layout.annotations as Record<string, unknown>[]).map((a) => (a.bgcolor ? { ...a, bgcolor: card, font: { ...(a.font as object), color: (a.font as { color?: string } | undefined)?.color ?? fg } } : a))
    : layout.annotations
  return {
    ...layout,
    annotations,
    autosize: true,
    margin: { t: 48, r: 16, b: 48, l: 56 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: fg, family: 'Manrope, Helvetica Neue, Arial, sans-serif' },
    // Palet brand: hijau streak dulu, lalu ink/abu dan warna status agar seri tetap terbedakan.
    colorway: document.documentElement.classList.contains('dark')
      ? ['#21D138', '#D8D8D3', '#E0B04A', '#F2857D', '#6BE87F', '#7C807D', '#5FB3A6']
      : ['#12A227', '#343A38', '#B5820C', '#B3261E', '#0B6B1C', '#A5A8A5', '#2F7F73'],
    xaxis: { gridcolor: grid, zerolinecolor: grid, ...(layout.xaxis as object) },
    yaxis: { gridcolor: grid, zerolinecolor: grid, ...(layout.yaxis as object) },
  }
}

function Chart({ chart }: { chart: SolverChart }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let cancelled = false
    const draw = () =>
      loadPlotly().then((Plotly) => {
        if (!cancelled)
          Plotly.react(el, { data: chart.spec.data, layout: themedLayout(chart.spec.layout), frames: chart.spec.frames, config: { responsive: true, displaylogo: false } })
      })
    draw()
    const observer = new MutationObserver(draw)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => {
      cancelled = true
      observer.disconnect()
      loadPlotly().then((Plotly) => Plotly.purge(el))
    }
  }, [chart])

  const download = () => {
    if (ref.current) loadPlotly().then((Plotly) => Plotly.downloadImage(ref.current!, { format: 'png', filename: `idstats-${chart.id}` }))
  }

  return (
    <div className="rounded-xl border bg-card p-3">
      <div className="flex justify-end">
        <Button variant="ghost" size="sm" onClick={download}>
          <Download /> PNG
        </Button>
      </div>
      <div ref={ref} className="w-full" style={{ height: Number(chart.spec.layout?.height) || 320 }} role="img" aria-label={chart.title} />
    </div>
  )
}

export function ChartView({ charts }: { charts: SolverChart[] }) {
  return (
    <div className={charts.length > 1 ? 'grid gap-4 xl:grid-cols-2' : 'grid gap-4'}>
      {charts.map((c) => (
        <Chart key={c.id} chart={c} />
      ))}
    </div>
  )
}
