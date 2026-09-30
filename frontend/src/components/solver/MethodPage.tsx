import { AlertTriangle, BookOpen, Calculator, ChartColumn, ListOrdered, Table2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { SolverResponse } from '@/lib/api'
import { ChartView } from './ChartView'
import { StepsView } from './StepsView'

interface MethodPageProps {
  title: string
  subtitle: string
  input: ReactNode
  result?: ReactNode
  response?: SolverResponse<unknown> | null
  theory: ReactNode
}

/** Kerangka standar setiap halaman metode: Input → Hasil → Langkah → Visualisasi → Teori. */
export function MethodPage({ title, subtitle, input, result, response, theory }: MethodPageProps) {
  const [tab, setTab] = useState('input')
  const hasResult = Boolean(response)

  // Pindah ke tab Hasil setiap kali respons baru datang.
  const [shownResponse, setShownResponse] = useState(response)
  if (response !== shownResponse) {
    setShownResponse(response)
    if (response) setTab('result')
  }

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-1 text-muted-foreground">{subtitle}</p>

      <Tabs value={tab} onValueChange={setTab} className="mt-6">
        <TabsList>
          <TabsTrigger value="input"><Calculator className="size-4" /> Input</TabsTrigger>
          <TabsTrigger value="result" disabled={!hasResult}><Table2 className="size-4" /> Hasil</TabsTrigger>
          <TabsTrigger value="steps" disabled={!hasResult}><ListOrdered className="size-4" /> Langkah-langkah</TabsTrigger>
          <TabsTrigger value="charts" disabled={!response?.charts.length}><ChartColumn className="size-4" /> Visualisasi</TabsTrigger>
          <TabsTrigger value="theory"><BookOpen className="size-4" /> Teori Singkat</TabsTrigger>
        </TabsList>

        {response && response.warnings.length > 0 && tab !== 'input' && (
          <div role="status" className="mt-4 flex gap-2 rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm">
            <AlertTriangle className="size-4 shrink-0 text-warning" />
            <ul>{response.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
          </div>
        )}

        <TabsContent value="input">{input}</TabsContent>
        <TabsContent value="result">{result}</TabsContent>
        <TabsContent value="steps">{response && <StepsView steps={response.steps} />}</TabsContent>
        <TabsContent value="charts">{response && <ChartView charts={response.charts} />}</TabsContent>
        <TabsContent value="theory">
          <div className="prose-sm flex flex-col gap-3 rounded-xl border bg-card p-5 text-sm leading-relaxed">{theory}</div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
