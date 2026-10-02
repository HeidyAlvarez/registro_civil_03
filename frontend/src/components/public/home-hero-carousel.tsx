import { ChevronLeft, ChevronRight, Clock3, Pause, Play, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

const notices = [
  {
    eyebrow: 'Trámites en línea',
    title: 'Agenda tu cita sin filas',
    description: 'Elige el trámite, día y horario que mejor te convenga desde cualquier dispositivo.',
    action: 'Agendar mi cita',
    to: '/agendar-cita',
    icon: Clock3,
    imageLabel: 'Espacio para fotografía de atención en la Oficialía 03',
  },
  {
    eyebrow: 'Información importante',
    title: 'Horario de atención',
    description: 'Te atendemos de lunes a viernes de 9:00 a 16:00 horas en Villa Victoria.',
    action: 'Ver ubicación',
    to: '/ubicacion',
    icon: Clock3,
    imageLabel: 'Espacio para fotografía del edificio de la Oficialía 03',
  },
  {
    eyebrow: 'Nuevo servicio',
    title: 'Conoce el asistente virtual',
    description: 'Resuelve dudas sobre requisitos, costos y horarios con información clara y oficial.',
    action: 'Preguntar al asistente',
    to: '/inteligencia',
    icon: Sparkles,
    imageLabel: 'Espacio para imagen del nuevo asistente virtual',
  },
]

export function HomeHeroCarousel() {
  const [active, setActive] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    if (paused || prefersReducedMotion) return
    const timer = window.setInterval(() => setActive((current) => (current + 1) % notices.length), 7000)
    return () => window.clearInterval(timer)
  }, [paused])

  const show = (index: number) => setActive((index + notices.length) % notices.length)
  const notice = notices[active]
  const Icon = notice.icon

  return (
    <section
      className="relative overflow-hidden rounded-2xl bg-primary text-white shadow-soft"
      aria-roledescription="carrusel"
      aria-label="Avisos importantes"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false)
      }}
    >
      <div className="grid min-h-[420px] md:grid-cols-[1.15fr_.85fr]">
        <div className="flex flex-col justify-center px-6 py-10 md:px-10 lg:px-14">
          <p className="mb-3 text-sm font-bold uppercase tracking-[0.16em] text-emerald-200">{notice.eyebrow}</p>
          <h1 className="max-w-2xl font-heading text-2xl font-semibold leading-tight md:text-4xl">{notice.title}</h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-white/85">{notice.description}</p>
          <Link
            to={notice.to}
            className="mt-7 inline-flex min-h-12 w-fit items-center justify-center rounded-xl bg-white px-6 py-3 text-base font-bold text-primary transition duration-200 hover:bg-emerald-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/50"
          >
            {notice.action}
          </Link>
        </div>
        <div className="relative m-4 min-h-56 overflow-hidden rounded-2xl border border-white/20 bg-emerald-950/40 md:m-6 md:ml-0">
          <div className="absolute inset-0 grid place-items-center px-8 text-center">
            <div>
              <span className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-white/10">
                <Icon className="h-10 w-10 text-emerald-200" aria-hidden="true" />
              </span>
              <p className="mt-4 text-sm font-medium text-white/70">{notice.imageLabel}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="absolute bottom-4 left-6 right-6 flex items-center justify-between gap-4 md:left-10 md:right-auto">
        <div className="flex gap-2" aria-label="Seleccionar aviso">
          {notices.map((item, index) => (
            <button
              key={item.title}
              type="button"
              onClick={() => show(index)}
              className={cn(
                'h-3 rounded-full border border-white/60 transition-all duration-200 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/50',
                active === index ? 'w-8 bg-white' : 'w-3 bg-white/30 hover:bg-white/70',
              )}
              aria-label={`Mostrar aviso ${index + 1}: ${item.title}`}
              aria-current={active === index ? 'true' : undefined}
            />
          ))}
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => show(active - 1)} className="grid h-10 w-10 place-items-center rounded-xl bg-white/10 transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/50" aria-label="Aviso anterior">
            <ChevronLeft className="h-6 w-6" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => setPaused((value) => !value)} className="grid h-10 w-10 place-items-center rounded-xl bg-white/10 transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/50" aria-label={paused ? 'Reanudar carrusel' : 'Pausar carrusel'}>
            {paused ? <Play className="h-5 w-5" aria-hidden="true" /> : <Pause className="h-5 w-5" aria-hidden="true" />}
          </button>
          <button type="button" onClick={() => show(active + 1)} className="grid h-10 w-10 place-items-center rounded-xl bg-white/10 transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/50" aria-label="Aviso siguiente">
            <ChevronRight className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>
      </div>
    </section>
  )
}
