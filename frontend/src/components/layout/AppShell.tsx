import { Menu, Moon, Sun, X } from 'lucide-react'
import { useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Sidebar } from './Sidebar'
import { SiteFooter } from './SiteFooter'
import { useTheme } from './useTheme'

export function AppShell() {
  const { theme, toggle } = useTheme()
  const [open, setOpen] = useState(false)

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/75 px-4 backdrop-blur-md">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label={open ? 'Tutup menu' : 'Buka menu'}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X /> : <Menu />}
        </Button>
        <Link to="/" className="flex items-center gap-2.5">
          <img src="/brand/mark-p.jpg" alt="" className="size-8 rounded-xs mix-blend-multiply dark:bg-[var(--paper-100)] dark:mix-blend-normal" />
          <span className="font-display text-lg font-light tracking-[0.22em] text-strong">IDSTATS</span>
        </Link>
        <span className="eyebrow hidden sm:inline">Modelling &amp; Optimization</span>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto"
          onClick={toggle}
          aria-label={theme === 'dark' ? 'Ganti ke mode terang' : 'Ganti ke mode gelap'}
        >
          {theme === 'dark' ? <Sun /> : <Moon />}
        </Button>
      </header>

      <div className="flex">
        <aside className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-72 shrink-0 overflow-y-auto border-r lg:block">
          <Sidebar />
        </aside>
        {open && (
          <div className="fixed inset-0 top-14 z-20 overflow-y-auto bg-background lg:hidden">
            <Sidebar onNavigate={() => setOpen(false)} />
          </div>
        )}
        <div className="flex min-h-[calc(100dvh-3.5rem)] min-w-0 flex-1 flex-col">
          <main className="flex-1 px-4 py-6 sm:px-8">
            <Outlet />
          </main>
          <SiteFooter />
        </div>
      </div>
    </div>
  )
}
