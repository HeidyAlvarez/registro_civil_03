import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatMoney(value: number | string) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
  }).format(Number(value || 0))
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'long',
  }).format(new Date(`${value}T12:00:00`))
}
