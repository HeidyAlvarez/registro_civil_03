import { Bot, CalendarCheck2, CircleX, ClipboardList, FileSearch, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

const services = [
  { to: '/agendar-cita', title: 'Agendar cita', description: 'Elige tu trámite, fecha y hora disponibles.', icon: CalendarCheck2 },
  { to: '/consultar', title: 'Consultar cita', description: 'Revisa tu cita usando el folio y la CURP.', icon: FileSearch },
  { to: '/cancelar', title: 'Cancelar cita', description: 'Cancela una cita que ya no podrás atender.', icon: CircleX },
  { to: '/tramites', title: 'Requisitos', description: 'Consulta documentos, requisitos y costos.', icon: ClipboardList },
  { to: '/ubicacion', title: 'Ubicación', description: 'Encuentra la Oficialía 03 y cómo llegar.', icon: MapPin },
  { to: '/inteligencia', title: 'Módulo de IA', description: 'Recibe orientación inmediata para tu trámite.', icon: Bot, featured: true },
]

export function HomeServicesGrid() {
  return (
    <section className="py-12 md:py-16" aria-labelledby="servicios-titulo">
      <div className="mb-7 max-w-2xl">
        <p className="text-sm font-bold uppercase tracking-wider text-primary">Servicios en línea</p>
        <h2 id="servicios-titulo" className="mt-2 font-heading text-2xl font-semibold text-warm-900 md:text-4xl">
          ¿Qué necesitas hacer?
        </h2>
        <p className="mt-3 text-warm-700">Selecciona una opción para comenzar. El proceso te guiará paso a paso.</p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {services.map(({ to, title, description, icon: Icon, featured }) => (
          <article key={to}>
            <Card
              className={cn(
                'group relative flex h-full flex-col transition duration-200 hover:-translate-y-1 hover:scale-[1.015] hover:shadow-soft',
                featured && 'border-primary bg-primary text-white',
              )}
            >
              {featured && (
                <span className="absolute right-5 top-5 rounded-full bg-warning px-3 py-1 text-xs font-bold uppercase tracking-wide text-warm-900">
                  Nuevo
                </span>
              )}
              <span className={cn('mb-5 grid h-16 w-16 place-items-center rounded-full bg-accent text-primary', featured && 'bg-white/15 text-white')}>
                <Icon className="h-12 w-12" strokeWidth={1.75} aria-hidden="true" />
              </span>
              <CardTitle className={cn(featured && 'text-white')}>{title}</CardTitle>
              <CardDescription className={cn('flex-1', featured && 'text-white/80')}>{description}</CardDescription>
              <Link
                to={to}
                className={cn(
                  'mt-6 inline-flex min-h-11 items-center justify-center rounded-xl border border-primary px-5 py-2 text-sm font-bold text-primary transition duration-200 hover:bg-accent focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/25',
                  featured && 'border-white bg-white text-primary hover:bg-emerald-50 focus-visible:ring-white/50',
                )}
                aria-label={`Ingresar a ${title}`}
              >
                Ingresar
              </Link>
            </Card>
          </article>
        ))}
      </div>
    </section>
  )
}
