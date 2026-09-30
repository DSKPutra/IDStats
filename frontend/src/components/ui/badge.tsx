import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

export function Badge({ className, tone = 'muted', ...props }: ComponentProps<'span'> & { tone?: 'muted' | 'success' }) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
        tone === 'success' ? 'bg-success/15 text-success' : 'bg-muted text-muted-foreground',
        className,
      )}
      {...props}
    />
  )
}
