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
  return {
    ...layout,
    autosize: true,
    margin: { t: 48, r: 16, b: 48, l: 56 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: fg, family: 'Inter, system-ui, sans-serif' },
    colorway: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#06b6d4', '#a855f7'],
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
        if (!cancelled) Plotly.react(el, chart.spec.data, themedLayout(chart.spec.layout), { responsive: true, displaylogo: false })
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
