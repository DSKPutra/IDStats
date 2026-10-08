import { CheckCircle2, RefreshCw, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { DataTable } from '@/components/solver/DataTable'
import { Latex } from '@/components/solver/Latex'
import { ResultView } from '@/components/solver/ResultView'
import { StepsView } from '@/components/solver/StepsView'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/textarea'
import { ApiError, getJson, solve, type SolverResponse, type SolverTable } from '@/lib/api'

interface Topic {
  id: string
  title: string
}
interface Question {
  topic: string
  title: string
  seed: number
  prompt: string
  latex: string | null
  table: SolverTable | null
  fields: { key: string; label: string }[]
}
interface CheckResult {
  correct: boolean
  results: { key: string; label: string; given: number | null; expected: number; correct: boolean; tolerance: number }[]
  solution: SolverResponse<unknown>
}

const selectClass = 'h-9 rounded-md border bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50'
const newSeed = () => Math.floor(Math.random() * 1_000_000)
const fmt = (v: number) => (Math.abs(v) >= 1e4 || Number.isInteger(v) ? v.toLocaleString('id-ID') : v.toLocaleString('id-ID', { maximumFractionDigits: 4 }))

export function PracticePage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [topic, setTopic] = useState('')
  const [question, setQuestion] = useState<Question | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [check, setCheck] = useState<CheckResult | null>(null)
  const [score, setScore] = useState({ right: 0, total: 0 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async (t: string) => {
    setLoading(true)
    setError(null)
    setCheck(null)
    setAnswers({})
    try {
      setQuestion(await getJson<Question>(`/practice/question/${t}?seed=${newSeed()}`))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Gagal memuat soal.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    getJson<Topic[]>('/practice/topics')
      .then((ts) => {
        setTopics(ts)
        if (ts[0]) {
          setTopic(ts[0].id)
          void load(ts[0].id)
        }
      })
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : 'Gagal memuat topik.'))
  }, [])

  const submit = async () => {
    if (!question) return
    const parsed: Record<string, number | null> = {}
    for (const f of question.fields) {
      const t = (answers[f.key] ?? '').trim().replace(',', '.')
      parsed[f.key] = t === '' || Number.isNaN(Number(t)) ? null : Number(t)
    }
    setLoading(true)
    setError(null)
    try {
      const res = (await solve('/practice/check', { topic: question.topic, seed: question.seed, answers: parsed })) as unknown as CheckResult
      if (!check) setScore((s) => ({ right: s.right + (res.correct ? 1 : 0), total: s.total + 1 }))
      setCheck(res)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Gagal memeriksa jawaban.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Mode Latihan (Practice Mode)</h1>
        <p className="mt-1 text-muted-foreground">
          Soal dibuat acak dengan angka berbeda setiap kali. Kerjakan secara manual, masukkan jawaban, lalu periksa — pembahasan
          langkah demi langkah ditampilkan setelahnya. Toleransi pembulatan 1%.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Topik
          <select
            className={selectClass}
            value={topic}
            onChange={(e) => {
              setTopic(e.target.value)
              void load(e.target.value)
            }}
          >
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </label>
        <Button variant="outline" disabled={!topic || loading} onClick={() => load(topic)}>
          <RefreshCw /> Soal baru
        </Button>
        <p className="ml-auto text-sm text-muted-foreground" aria-live="polite">
          Skor: <span className="font-semibold text-foreground">{score.right}</span> / {score.total}
        </p>
      </div>
      {error && <p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
      {question && (
        <Card>
          <CardHeader>
            <CardTitle>{question.title}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p>{question.prompt}</p>
            {question.latex && <Latex block>{question.latex}</Latex>}
            {question.table && <DataTable table={question.table} />}
            <form
              className="flex flex-wrap items-end gap-3"
              onSubmit={(e) => {
                e.preventDefault()
                void submit()
              }}
            >
              {question.fields.map((f) => (
                <label key={f.key} className="flex flex-col gap-1 text-sm font-medium">
                  {f.label}
                  <Input
                    inputMode="decimal"
                    className="w-44"
                    value={answers[f.key] ?? ''}
                    onChange={(e) => setAnswers((a) => ({ ...a, [f.key]: e.target.value }))}
                  />
                </label>
              ))}
              <Button type="submit" disabled={loading}>
                Periksa jawaban
              </Button>
            </form>
          </CardContent>
        </Card>
      )}
      {check && (
        <>
          <div
            className={`flex flex-col gap-2 rounded-xl border p-4 ${check.correct ? 'border-success/50 bg-success/10' : 'border-danger/50 bg-danger/10'}`}
          >
            <p className="flex items-center gap-2 font-semibold">
              {check.correct ? <CheckCircle2 className="size-5 text-success" /> : <XCircle className="size-5 text-danger" />}
              {check.correct ? 'Benar! Kerja bagus.' : 'Belum tepat. Pelajari pembahasan di bawah.'}
            </p>
            <ul className="text-sm">
              {check.results.map((r) => (
                <li key={r.key}>
                  {r.label}: jawaban Anda <b>{r.given === null ? '—' : fmt(r.given)}</b>, kunci <b>{fmt(r.expected)}</b>{' '}
                  {r.correct ? '✓' : '✗'}
                </li>
              ))}
            </ul>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Pembahasan</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              <ResultView response={check.solution} name={question?.title ?? 'pembahasan'} />
              <StepsView steps={check.solution.steps} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
