import katex from 'katex'
import 'katex/dist/katex.min.css'
import { useMemo } from 'react'

export function Latex({ children, block = false }: { children: string; block?: boolean }) {
  const html = useMemo(
    () => katex.renderToString(children, { throwOnError: false, displayMode: block }),
    [children, block],
  )
  return block ? (
    <div className="overflow-x-auto py-1" dangerouslySetInnerHTML={{ __html: html }} />
  ) : (
    <span dangerouslySetInnerHTML={{ __html: html }} />
  )
}
