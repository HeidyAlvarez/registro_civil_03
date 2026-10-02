import { Clock3, Mail, MapPin, Phone } from 'lucide-react'
import { Card, CardTitle } from '@/components/ui/card'

export function LocationPage() {
  return (
    <section>
      <p className="text-sm font-semibold text-primary">Oficialía 03</p>
      <h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Ubicación y contacto</h1>
      <p className="mt-3 max-w-2xl text-warm-500">Antes de acudir, revisa el horario y lleva los documentos de tu trámite.</p>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <Card><MapPin className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Villa Victoria, Estado de México</CardTitle><p className="mt-2 text-warm-500">Domicilio conocido, Col. Dr. Gustavo Baz Prada, C.P. 50960</p></Card>
        <Card><Clock3 className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Horario de atención</CardTitle><p className="mt-2 text-warm-500">Lunes a viernes, de 9:00 a 17:00 horas.</p></Card>
        <Card><Phone className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Atención telefónica</CardTitle><p className="mt-2 text-warm-500">Consulta el número vigente en tu comprobante o en la oficialía.</p></Card>
        <Card><Mail className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Correo electrónico</CardTitle><p className="mt-2 text-warm-500">Usa el canal institucional para dudas que requieran seguimiento.</p></Card>
      </div>
    </section>
  )
}
