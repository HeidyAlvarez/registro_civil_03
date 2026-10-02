import { AlertCircle, CheckCircle2, Inbox, LoaderCircle, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type AlertProps = {
  children: ReactNode
  variant?: 'success' | 'warning' | 'error' | 'info'
  className?: string
}

export function Alert({ children, variant = 'info', className }: AlertProps) {
  const styles = {
    success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    warning: 'border-amber-200 bg-amber-50 text-amber-950',
    error: 'border-red-200 bg-red-50 text-red-900',
    info: 'border-primary/20 bg-accent/60 text-primary',
  }
  const Icon = variant === 'success' ? CheckCircle2 : variant === 'warning' ? TriangleAlert : AlertCircle
  return (
    <div className={cn('flex gap-3 rounded-xl border p-4 text-sm', styles[variant], className)} role={variant === 'error' ? 'alert' : 'status'}>
      <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
      <div>{children}</div>
    </div>
  )
}

export function LoadingState({ label = 'Cargando información…' }: { label?: string }) {
  return (
    <div className="flex min-h-48 items-center justify-center gap-3 text-warm-500" role="status">
      <LoaderCircle className="h-7 w-7 animate-spin text-primary" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-warm-200 bg-white p-8 text-center">
      <Inbox className="mb-3 h-10 w-10 text-primary" aria-hidden="true" />
      <h2 className="font-heading text-lg font-semibold">{title}</h2>
      <p className="mt-2 max-w-md text-sm text-warm-500">{description}</p>
    </div>
  )
}
