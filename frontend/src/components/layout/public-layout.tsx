import { Building2, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { cn } from '@/lib/utils'

const links = [
  ['/', 'Inicio'],
  ['/agendar', 'Agendar cita'],
  ['/consultar', 'Consultar'],
  ['/tramites', 'Trámites'],
  ['/inteligencia', 'Asistente IA'],
]

export function PublicLayout() {
  const [open, setOpen] = useState(false)
  return (
    <div className="min-h-screen bg-warm-100 text-warm-900">
      <a href="#contenido" className="sr-only z-50 rounded-xl bg-white p-3 focus:not-sr-only focus:fixed focus:left-4 focus:top-4">
        Saltar al contenido
      </a>
      <div className="bg-primary px-4 py-2 text-xs text-white">
        <div className="mx-auto flex max-w-7xl justify-between">
          <span>Gobierno del Estado de México</span>
          <span>Oficialía 03 · Villa Victoria</span>
        </div>
      </div>
      <header className="border-b border-warm-200 bg-white">
        <div className="mx-auto flex min-h-20 max-w-7xl items-center justify-between gap-4 px-4">
          <Link to="/" className="flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/25">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-primary text-white"><Building2 className="h-7 w-7" /></span>
            <span><strong className="block font-heading text-base">Registro Civil</strong><span className="text-xs text-warm-500">Nueva Era Digital</span></span>
          </Link>
          <button className="rounded-xl p-2 text-primary md:hidden" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-label="Abrir menú">
            {open ? <X className="h-7 w-7" /> : <Menu className="h-7 w-7" />}
          </button>
          <nav className={cn('absolute left-0 right-0 top-[7rem] z-30 border-b bg-white p-4 shadow-soft md:static md:flex md:border-0 md:p-0 md:shadow-none', !open && 'hidden md:flex')} aria-label="Navegación principal">
            <div className="mx-auto flex max-w-7xl flex-col gap-1 md:flex-row">
              {links.map(([to, label]) => (
                <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)} className={({ isActive }) => cn('rounded-xl px-4 py-2 text-sm font-semibold text-warm-700 transition duration-200 hover:bg-accent hover:text-primary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20', isActive && 'bg-accent text-primary')}>
                  {label}
                </NavLink>
              ))}
            </div>
          </nav>
        </div>
      </header>
      <main id="contenido" className="mx-auto w-full max-w-7xl px-4 py-8 md:py-12" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="mt-12 bg-primary px-4 py-8 text-sm text-white">
        <div className="mx-auto max-w-7xl"><strong className="font-heading">Registro Civil — Oficialía 03</strong><p className="mt-1 text-white/75">Villa Victoria, Estado de México · Atención ciudadana clara y segura</p></div>
      </footer>
    </div>
  )
}
