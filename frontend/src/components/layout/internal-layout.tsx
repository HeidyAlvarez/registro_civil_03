import { Ban, Bot, CalendarDays, ChartNoAxesCombined, ClipboardList, FileClock, Landmark, LogOut, Menu, QrCode, ShieldCheck, WalletCards, X } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LoadingState } from '@/components/ui/feedback'
import { useSession } from '@/hooks/use-session'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

const nav: { to: string; label: string; icon: LucideIcon; permission?: 'official' | 'administrator' | 'internal_ai' }[] = [
  { to: '/panel', label: 'Resumen', icon: ChartNoAxesCombined },
  { to: '/panel/agenda', label: 'Agenda', icon: CalendarDays },
  { to: '/panel/escaner', label: 'Escáner QR', icon: QrCode },
  { to: '/panel/caja', label: 'Caja', icon: WalletCards },
  { to: '/panel/historial', label: 'Historial', icon: ClipboardList },
  { to: '/panel/bitacora', label: 'Bitácora', icon: FileClock },
  { to: '/panel/reporte', label: 'Reporte financiero', icon: ChartNoAxesCombined, permission: 'official' },
  { to: '/panel/horarios', label: 'Bloquear horarios', icon: Ban, permission: 'official' },
  { to: '/panel/catalogo', label: 'Catálogo', icon: Landmark, permission: 'administrator' },
  { to: '/panel/ia', label: 'Módulo IA', icon: Bot, permission: 'internal_ai' },
]

export function InternalLayout() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const session = useSession()
  if (session.isLoading) return <LoadingState label="Validando tu acceso…" />
  if (!session.data?.authenticated) return <Navigate to="/acceso" replace />

  return (
    <div className="min-h-screen bg-warm-100 text-warm-900">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-primary text-white shadow-soft">
        <div className="mx-auto flex min-h-20 max-w-[1440px] items-center justify-between gap-4 px-4">
          <div className="flex items-center gap-3"><ShieldCheck className="h-9 w-9" /><div><strong className="font-heading">Registro Civil</strong><span className="block text-xs text-white/70">Panel operativo · {session.data.full_name || session.data.username}</span></div></div>
          <button className="rounded-xl p-2 lg:hidden" onClick={() => setOpen((value) => !value)} aria-label="Mostrar navegación">{open ? <X className="h-7 w-7" /> : <Menu className="h-7 w-7" />}</button>
        </div>
      </header>
      <div className="mx-auto grid max-w-[1440px] lg:grid-cols-[260px_1fr]">
        <aside className={cn('border-r border-warm-200 bg-white p-4 lg:block lg:min-h-[calc(100vh-5rem)]', !open && 'hidden')}>
          <nav className="space-y-1" aria-label="Panel operativo">
            {nav.filter((item) => !item.permission || session.data.permissions[item.permission]).map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/panel'} onClick={() => setOpen(false)} className={({ isActive }) => cn('flex min-h-12 items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold transition duration-200 hover:bg-accent hover:text-primary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20', isActive && 'bg-accent text-primary')}>
                <Icon className="h-6 w-6" aria-hidden="true" />{label}
              </NavLink>
            ))}
          </nav>
          <Button variant="ghost" className="mt-8 w-full justify-start" type="button" onClick={async () => { await api('/citas/api/v1/auth/logout/', { method: 'POST' }); navigate('/acceso', { replace: true }) }}><LogOut className="h-6 w-6" />Cerrar sesión</Button>
        </aside>
        <main className="min-w-0 p-4 md:p-8" id="contenido"><Outlet /></main>
      </div>
    </div>
  )
}
