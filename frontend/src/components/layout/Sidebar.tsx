import { NavLink } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { categories, methodPath } from '@/registry/modules'

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Navigasi metode" className="flex flex-col gap-5 p-4 text-sm">
      {categories.map((c) => (
        <div key={c.id}>
          <p className="eyebrow mb-1.5 px-2">{c.title}</p>
          <ul className="flex flex-col gap-0.5">
            {c.methods.map((m) => (
              <li key={m.id}>
                <NavLink
                  to={methodPath(c.id, m.id)}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center justify-between gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-muted',
                      isActive && 'bg-muted font-medium text-strong',
                      !m.available && 'text-muted-foreground',
                    )
                  }
                >
                  <span className="line-clamp-2">{m.title}</span>
                  {!m.available && <Badge>F{m.phase}</Badge>}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  )
}
