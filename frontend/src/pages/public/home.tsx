import { Bell, Bot, CalendarCheck2, FileSearch, Landmark, MapPin, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'

const services = [
  { to: '/agendar', title: 'Agendar cita', description: 'Elige tu trámite, fecha y hora. Recibe un comprobante con código QR.', icon: CalendarCheck2 },
  { to: '/consultar', title: 'Consultar cita', description: 'Revisa el estado de tu cita con tu folio y CURP.', icon: FileSearch },
  { to: '/cancelar', title: 'Cancelar cita', description: 'Cancela una cita pendiente con la anticipación requerida.', icon: XCircle },
  { to: '/tramites', title: 'Trámites y costos', description: 'Consulta requisitos, documentos y costos oficiales.', icon: Landmark },
  { to: '/ubicacion', title: 'Ubicación y contacto', description: 'Encuentra la Oficialía 03 y sus horarios de atención.', icon: MapPin },
  { to: '/inteligencia', title: 'Asistente inteligente', description: 'Obtén orientación clara sobre trámites y horarios.', icon: Bot },
]

export function HomePage() {
  return (
    <>
      <section className="rounded-2xl bg-primary px-6 py-10 text-white shadow-soft md:px-10 md:py-14">
        <p className="mb-3 text-sm font-semibold uppercase tracking-wider text-emerald-200">Registro Civil · Nueva Era Digital</p>
        <h1 className="max-w-3xl font-heading text-2xl font-semibold leading-tight md:text-4xl">Servicios claros, seguros y cerca de ti</h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-white/80">Agenda y consulta tu cita sin filas. Si necesitas ayuda, el asistente puede orientarte con información oficial.</p>
      </section>
      <section className="py-10" aria-labelledby="servicios-titulo">
        <div className="mb-6 flex items-end justify-between gap-4"><div><p className="text-sm font-semibold text-primary">Servicios disponibles</p><h2 id="servicios-titulo" className="mt-1 font-heading text-2xl font-semibold">¿Qué necesitas hacer?</h2></div><Bell className="hidden h-8 w-8 text-primary md:block" aria-hidden="true" /></div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {services.map(({ to, title, description, icon: Icon }) => (
            <Link key={to} to={to} className="group rounded-2xl focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/25">
              <Card className="h-full transition duration-200 group-hover:-translate-y-1 group-hover:border-primary/40">
                <span className="mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-accent text-primary"><Icon className="h-8 w-8" aria-hidden="true" /></span>
                <CardTitle>{title}</CardTitle><CardDescription>{description}</CardDescription>
                <span className="mt-5 inline-block text-sm font-semibold text-primary">Ingresar →</span>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </>
  )
}
