import { useState, type FormEvent } from 'react'
import { FileDown, Search, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Alert } from '@/components/ui/feedback'
import { Field, Input } from '@/components/ui/field'
import { postJson } from '@/lib/api'
import { formatDate, formatMoney } from '@/lib/utils'

type Appointment = {
  folio: number
  nombre: string
  tramite: string
  fecha: string
  hora: string
  estado: string
  estado_etiqueta: string
  costo: number
  puede_cancelar: boolean
  motivo_no_cancelar?: string
  pdf_url: string
}

export function AppointmentLookupPage({ cancel = false }: { cancel?: boolean }) {
  const [folio, setFolio] = useState('')
  const [curp, setCurp] = useState('')
  const [appointment, setAppointment] = useState<Appointment | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  async function lookup(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError(''); setSuccess('')
    try {
      const response = await postJson<{ ok: boolean; cita?: Appointment; error?: string }>('/citas/api/consultar-cita/', { folio, curp })
      if (!response.ok || !response.cita) throw new Error(response.error || 'No encontramos la cita.')
      setAppointment(response.cita)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No fue posible consultar la cita.') } finally { setLoading(false) }
  }

  async function cancelAppointment() {
    if (!window.confirm('¿Confirmas que deseas cancelar esta cita? Esta acción no se puede deshacer.')) return
    setLoading(true); setError('')
    try {
      const response = await postJson<{ ok: boolean; message?: string; cita?: Appointment; error?: string }>('/citas/api/cancelar-cita/', { folio, curp })
      if (!response.ok) throw new Error(response.error || response.message || 'No fue posible cancelar.')
      setAppointment(response.cita || null); setSuccess(response.message || 'La cita se canceló correctamente.')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No fue posible cancelar.') } finally { setLoading(false) }
  }

  return (
    <section className="mx-auto max-w-3xl">
      <p className="text-sm font-semibold text-primary">Servicio ciudadano</p>
      <h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">{cancel ? 'Cancelar una cita' : 'Consultar una cita'}</h1>
      <p className="mt-3 text-warm-500">{cancel ? 'Primero consulta tu cita. Si cumple las condiciones, podrás cancelarla.' : 'Ten a la mano el folio de tu comprobante y tu CURP.'}</p>
      <Card className="mt-8">
        <form className="grid gap-5 md:grid-cols-2" onSubmit={lookup}>
          <Field label="Folio de la cita" htmlFor="folio" hint="Aparece en la parte superior de tu comprobante."><Input id="folio" inputMode="numeric" value={folio} onChange={(event) => setFolio(event.target.value)} required /></Field>
          <Field label="CURP" htmlFor="curp"><Input id="curp" value={curp} onChange={(event) => setCurp(event.target.value.toUpperCase())} maxLength={18} required /></Field>
          <Button loading={loading} className="md:col-span-2" type="submit"><Search className="h-6 w-6" />Buscar cita</Button>
        </form>
      </Card>
      {error ? <Alert variant="error" className="mt-5">{error}</Alert> : null}
      {success ? <Alert variant="success" className="mt-5">{success}</Alert> : null}
      {appointment ? (
        <Card className="mt-6 border-primary/25">
          <div className="flex flex-col justify-between gap-4 sm:flex-row"><div><CardTitle>Cita #{appointment.folio}</CardTitle><CardDescription>{appointment.nombre}</CardDescription></div><span className="h-fit rounded-full bg-accent px-3 py-1 text-sm font-semibold text-primary">{appointment.estado_etiqueta}</span></div>
          <dl className="mt-6 grid gap-4 rounded-xl bg-warm-100 p-4 sm:grid-cols-2"><div><dt className="text-xs font-semibold uppercase text-warm-500">Trámite</dt><dd className="mt-1 font-medium">{appointment.tramite}</dd></div><div><dt className="text-xs font-semibold uppercase text-warm-500">Fecha y hora</dt><dd className="mt-1 font-medium">{formatDate(appointment.fecha)} · {appointment.hora}</dd></div><div><dt className="text-xs font-semibold uppercase text-warm-500">Costo</dt><dd className="mt-1 font-medium">{formatMoney(appointment.costo)}</dd></div></dl>
          <div className="mt-5 flex flex-wrap gap-3">
            {!cancel ? <Button asChild variant="secondary"><a href={appointment.pdf_url}><FileDown className="h-6 w-6" />Descargar comprobante</a></Button> : null}
            {cancel && appointment.puede_cancelar ? <Button variant="danger" onClick={cancelAppointment} loading={loading}><XCircle className="h-6 w-6" />Cancelar cita</Button> : null}
          </div>
          {cancel && !appointment.puede_cancelar && appointment.motivo_no_cancelar ? <Alert variant="warning" className="mt-4">{appointment.motivo_no_cancelar}</Alert> : null}
        </Card>
      ) : null}
    </section>
  )
}
