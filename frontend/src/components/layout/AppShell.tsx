import { Menu, Moon, Sun, X } from 'lucide-react'
import { useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Sidebar } from './Sidebar'
import { useTheme } from './useTheme'

export function AppShell() {
  const { theme, toggle } = useTheme()
  const [open, setOpen] = useState(false)

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/85 px-4 backdrop-blur">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label={open ? 'Tutup menu' : 'Buka menu'}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X /> : <Menu />}
        </Button>
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <img src="/favicon.svg" alt="" className="size-6" />
          IDStats
        </Link>
        <span className="hidden text-sm text-muted-foreground sm:inline">Modelling &amp; Optimization</span>
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
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
