const YEAR = new Date().getFullYear()

/** Footer brand Dea Saka Kurnia Putra: garis streak, hak cipta, dan tagline. */
export function SiteFooter() {
  return (
    <footer className="no-print mt-12 text-[var(--text-on-inverse-muted)]" style={{ background: 'var(--ink-gradient)' }}>
      <span className="streak" aria-hidden="true" />
      <div className="flex flex-col gap-3 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div className="flex items-center gap-3">
          <img src="/brand/mark-p.jpg" alt="" className="size-8 rounded-xs" />
          <div>
            <p className="font-display text-sm font-light tracking-[0.34em] text-[var(--paper-050)]">DEA SAKA KURNIA PUTRA</p>
            <p className="text-[10px] uppercase tracking-[0.22em]">A brighter tomorrow through meaningful work</p>
          </div>
        </div>
        <p className="text-xs">
          © {YEAR} Dea Saka Kurnia Putra. Hak cipta dilindungi undang-undang.
        </p>
      </div>
    </footer>
  )
}
