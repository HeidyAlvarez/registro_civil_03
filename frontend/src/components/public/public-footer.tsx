import { Clock3, Mail, MapPin, Phone } from 'lucide-react'

const details = [
  { icon: MapPin, title: 'Dirección', text: 'Villa Victoria, Estado de México' },
  { icon: Clock3, title: 'Horario', text: 'Lunes a viernes · 9:00 a 16:00 h' },
  { icon: Phone, title: 'Teléfono', text: 'Atención en la Oficialía 03' },
  { icon: Mail, title: 'Contacto', text: 'Orientación para trámites y citas' },
]

export function PublicFooter() {
  return (
    <footer className="mt-8 bg-primary px-4 py-10 text-sm text-white">
      <div className="mx-auto max-w-7xl">
        <div className="grid gap-8 border-b border-white/15 pb-8 sm:grid-cols-2 lg:grid-cols-4">
          {details.map(({ icon: Icon, title, text }) => (
            <div key={title} className="flex gap-3">
              <Icon className="h-7 w-7 shrink-0 text-emerald-200" aria-hidden="true" />
              <div>
                <strong className="font-heading text-base">{title}</strong>
                <p className="mt-1 leading-6 text-white/75">{text}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="flex flex-col gap-2 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <strong className="font-heading">Registro Civil 03 · Villa Victoria</strong>
          <p className="text-white/70">Atención ciudadana clara, segura y cercana.</p>
        </div>
      </div>
    </footer>
  )
}
