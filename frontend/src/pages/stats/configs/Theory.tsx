import type { ReactNode } from 'react'
import { Latex } from '@/components/solver/Latex'

/** Blok teori: paragraf + rumus. */
export function Theory({ children, formulas = [] }: { children: ReactNode; formulas?: string[] }) {
  return (
    <>
      {children}
      {formulas.map((f) => (
        <Latex key={f} block>
          {f}
        </Latex>
      ))}
    </>
  )
}
