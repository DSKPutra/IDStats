import { ArrowRight, Search } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/textarea'
import { categories, methodPath, searchMethods } from '@/registry/modules'

const totalMethods = categories.reduce((n, c) => n + c.methods.length, 0)
const availableMethods = categories.reduce((n, c) => n + c.methods.filter((m) => m.available).length, 0)

export function Dashboard() {
  const [query, setQuery] = useState('')
  const results = searchMethods(query)

  return (
    <div className="mx-auto max-w-6xl">
      <section
        className="relative mb-8 overflow-hidden rounded-2xl border border-[var(--line-inverse)] px-6 py-10 text-[var(--text-on-inverse-muted)] sm:px-10"
        style={{ background: 'var(--ink-gradient)' }}
      >
        <p className="eyebrow !text-[var(--text-on-inverse-muted)]">Modelling &amp; Optimization</p>
        <span className="streak mt-4 w-24 shadow-[var(--glow-green)]" aria-hidden="true" />
        <h1 className="mt-5 text-4xl !text-[var(--paper-050)] sm:text-6xl" style={{ fontWeight: 200 }}>
          IDStats
        </h1>
        <p className="mt-4 max-w-2xl leading-relaxed">
          Kalkulator dan modul belajar untuk mata kuliah <em>Modelling &amp; Optimization</em>: statistika, seluruh bab
          <em> Introduction to Operations Research</em> (Hillier &amp; Lieberman), dan optimasi untuk machine learning.
          Setiap metode menampilkan langkah penyelesaian bertahap.
        </p>
        <p className="mt-3 font-mono text-xs tracking-wide">
          {availableMethods === totalMethods
            ? `${totalMethods} metode tersedia`
            : `${availableMethods} dari ${totalMethods} metode tersedia`}
        </p>
      </section>
      <section>
        <label className="relative mb-6 block max-w-md">
          <span className="sr-only">Cari metode</span>
          <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Cari metode, mis. simpleks, antrian, ANOVA…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </section>

      {results.length === 0 ? (
        <p className="py-10 text-center text-muted-foreground">Tidak ada metode yang cocok dengan “{query}”.</p>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {results.map((c) => (
            <Card key={c.id}>
              <CardHeader>
                <CardTitle>{c.title}</CardTitle>
                <CardDescription>{c.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col">
                  {c.methods.map((m) => (
                    <li key={m.id}>
                      <Link
                        to={methodPath(c.id, m.id)}
                        className="group flex items-center justify-between gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                      >
                        <span>{m.title}</span>
                        {m.available ? (
                          <Badge tone="success">
                            Tersedia <ArrowRight className="ml-1 size-3" />
                          </Badge>
                        ) : (
                          <Badge>Fase {m.phase}</Badge>
                        )}
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
