import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

type FieldProps = {
  label: string
  htmlFor: string
  hint?: string
  error?: string
  children: ReactNode
}

export function Field({ label, htmlFor, hint, error, children }: FieldProps) {
  return (
    <div className="space-y-2">
      <label htmlFor={htmlFor} className="block text-sm font-semibold text-warm-900">
        {label}
      </label>
      {children}
      {hint && !error ? <p className="text-xs text-warm-500">{hint}</p> : null}
      {error ? <p className="text-xs font-medium text-danger" role="alert">{error}</p> : null}
    </div>
  )
}

const control =
  'min-h-11 w-full rounded-xl border border-warm-200 bg-white px-3 py-2.5 text-base text-warm-900 outline-none transition duration-200 placeholder:text-warm-500 focus:border-primary focus:ring-4 focus:ring-primary/15 disabled:bg-warm-100 disabled:text-warm-500'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(control, className)} {...props} />
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(control, className)} {...props} />
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(control, 'min-h-28 resize-y', className)} {...props} />
}
