import { Building2, Menu, TextCursorInput, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

const links = [
  ['/', 'Inicio'],
  ['/agendar-cita', 'Agendar cita'],
  ['/consultar', 'Consultar'],
  ['/tramites', 'Requisitos'],
  ['/inteligencia', 'Módulo de IA'],
]

const textSizes = [100, 112.5, 125]

export function PublicHeader() {
  const [open, setOpen] = useState(false)
  const [textSizeIndex, setTextSizeIndex] = useState(0)

  useEffect(() => {
    document.documentElement.style.fontSize = `${textSizes[textSizeIndex]}%`
    return () => {
      document.documentElement.style.fontSize = ''
    }
  }, [textSizeIndex])

  const increaseText = () => setTextSizeIndex((current) => (current + 1) % textSizes.length)

  return (
    <>
      <div className="bg-primary px-4 py-2 text-xs text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-2">
          <span>Gobierno del Estado de México</span>
          <span>Oficialía 03 · Villa Victoria</span>
        </div>
      </div>
      <header className="relative z-30 border-b border-warm-200 bg-white">
        <div className="mx-auto flex min-h-20 max-w-7xl items-center gap-3 px-4">
          <Link to="/" className="mr-auto flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/25">
            <span className="grid h-12 w-12 place-items-center rounded-full bg-primary text-white" aria-hidden="true">
              <Building2 className="h-8 w-8" />
            </span>
            <span>
              <strong className="block font-heading text-base text-warm-900 md:text-lg">Registro Civil 03</strong>
              <span className="hidden text-xs text-warm-500 sm:block">Villa Victoria · Nueva Era Digital</span>
            </span>
          </Link>

          <nav
            className={cn(
              'absolute left-0 right-0 top-full border-b bg-white p-4 shadow-soft lg:static lg:flex lg:border-0 lg:p-0 lg:shadow-none',
              !open && 'hidden lg:flex',
            )}
            aria-label="Navegación principal"
          >
            <div className="mx-auto flex max-w-7xl flex-col gap-1 lg:flex-row">
              {links.map(([to, label]) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'rounded-xl px-3 py-2 text-sm font-semibold text-warm-700 transition duration-200 hover:bg-accent hover:text-primary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20',
                      isActive && 'bg-accent text-primary',
                    )
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>
          </nav>

          <button
            type="button"
            onClick={increaseText}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-warm-200 px-3 py-2 text-sm font-bold text-primary transition duration-200 hover:border-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20"
            aria-label={`Aumentar tamaño del texto. Tamaño actual: ${textSizes[textSizeIndex]} por ciento`}
            title="Aumentar tamaño del texto"
          >
            <TextCursorInput className="h-6 w-6" aria-hidden="true" />
            <span className="hidden xl:inline">Aumentar texto</span>
            <span aria-hidden="true">A+</span>
          </button>

          <button
            type="button"
            className="grid h-11 w-11 place-items-center rounded-xl text-primary transition hover:bg-accent focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20 lg:hidden"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-label={open ? 'Cerrar menú' : 'Abrir menú'}
          >
            {open ? <X className="h-7 w-7" aria-hidden="true" /> : <Menu className="h-7 w-7" aria-hidden="true" />}
          </button>
        </div>
      </header>
    </>
  )
}
