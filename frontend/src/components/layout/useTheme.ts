import { useCallback, useState } from 'react'

type Theme = 'light' | 'dark'
const KEY = 'idstats-theme'

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.classList.contains('dark') ? 'dark' : 'light',
  )
  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark'
      document.documentElement.classList.toggle('dark', next === 'dark')
      try {
        localStorage.setItem(KEY, next)
      } catch {
        /* storage diblokir: tema tetap berlaku untuk sesi ini */
      }
      return next
    })
  }, [])
  return { theme, toggle }
}
