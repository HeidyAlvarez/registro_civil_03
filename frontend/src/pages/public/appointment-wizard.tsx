import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { CalendarCheck2, Check, ChevronLeft, ChevronRight, Clock3, Download, UserRound } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Alert, LoadingState } from '@/components/ui/feedback'
import { Field, Input, Select } from '@/components/ui/field'
import { useCatalog } from '@/hooks/use-catalog'
import { api, postJson } from '@/lib/api'
import { formatMoney } from '@/lib/utils'

type Slot = { hora: string; ocupado: boolean }
type FormData = { tramite_id: string; nombre: string; curp: string; cp: string; direccion: string; fecha: string; hora: string }
const initialForm: FormData = { tramite_id: '', nombre: '', curp: '', cp: '', direccion: '', fecha: '', hora: '' }

export function AppointmentWizardPage() {
  const catalog = useCatalog()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState(initialForm)
  const [slots, setSlots] = useState<Slot[]>([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState<{ folio: number; qr_url: string; pdf_url: string } | null>(null)
  const procedures = useMemo(() => catalog.data?.secciones.flatMap((section) => section.tramites) || [], [catalog.data])
  const procedure = procedures.find((item) => String(item.id) === form.tramite_id)

  function update(field: keyof FormData, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  useEffect(() => {
    if (!form.fecha || !form.tramite_id) return
    setLoadingSlots(true); setError(''); setSlots([]); update('hora', '')
    api<{ horarios: Slot[] }>(`/citas/api/horarios/?fecha=${form.fecha}&tramite_id=${form.tramite_id}`)
      .then((data) => setSlots(data.horarios))
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoadingSlots(false))
  }, [form.fecha, form.tramite_id])

  async function validateCitizen() {
    setError('')
    try {
      await postJson('/citas/api/validar-curp/', { curp: form.curp })
      setStep(3)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Revisa tu CURP.') }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setSubmitting(true); setError('')
    try {
      const response = await postJson<{ ok: boolean; error?: string; folio: number; qr_url: string; pdf_url: string }>('/citas/agendar/', form)
      if (!response.ok) throw new Error(response.error || 'No fue posible agendar.')
      setReceipt(response)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No fue posible agendar.') } finally { setSubmitting(false) }
  }

  if (receipt) return (
    <section className="mx-auto max-w-2xl text-center">
      <span className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-accent text-primary"><Check className="h-9 w-9" /></span>
      <h1 className="mt-5 font-heading text-2xl font-semibold md:text-4xl">Tu cita quedó agendada</h1>
      <p className="mt-3 text-warm-500">Folio <strong className="text-warm-900">#{receipt.folio}</strong>. Guarda tu comprobante y preséntalo el día de tu cita.</p>
      <Card className="mx-auto mt-7 max-w-sm"><img className="mx-auto h-52 w-52" src={receipt.qr_url} alt={`Código QR de la cita ${receipt.folio}`} /></Card>
      <Button asChild className="mt-6"><a href={receipt.pdf_url}><Download className="h-6 w-6" />Descargar comprobante</a></Button>
    </section>
  )

  return (
    <section className="mx-auto max-w-4xl">
      <p className="text-sm font-semibold text-primary">Servicio ciudadano</p>
      <h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Agenda tu cita</h1>
      <p className="mt-3 text-warm-500">Completa los datos paso a paso. Los campos marcados son obligatorios.</p>
      <ol className="my-8 grid grid-cols-3 gap-2" aria-label="Progreso">
        {['Trámite', 'Tus datos', 'Fecha y hora'].map((label, index) => <li key={label} className={`rounded-xl px-3 py-3 text-center text-xs font-semibold ${step >= index + 1 ? 'bg-primary text-white' : 'bg-white text-warm-500'}`}>{index + 1}. {label}</li>)}
      </ol>
      {error ? <Alert variant="error" className="mb-5">{error}</Alert> : null}
      <form onSubmit={submit}>
        <Card>
          {step === 1 ? <div><CardTitle>Selecciona el trámite</CardTitle>{catalog.isLoading ? <LoadingState /> : <div className="mt-5"><Field label="Trámite" htmlFor="tramite"><Select id="tramite" required value={form.tramite_id} onChange={(event) => update('tramite_id', event.target.value)}><option value="">Selecciona una opción</option>{catalog.data?.secciones.map((section) => <optgroup key={section.nombre} label={section.nombre}>{section.tramites.map((item) => <option key={item.id} value={item.id}>{item.nombre} — {formatMoney(item.costo)}</option>)}</optgroup>)}</Select></Field>{procedure ? <Alert className="mt-4"><strong>{procedure.duracion_minutos} minutos.</strong> {procedure.documentos || 'Consulta los documentos en el catálogo.'}</Alert> : null}</div>}</div> : null}
          {step === 2 ? <div className="grid gap-5 md:grid-cols-2"><CardTitle className="md:col-span-2">Datos de la persona solicitante</CardTitle><Field label="Nombre completo" htmlFor="nombre"><Input id="nombre" required value={form.nombre} onChange={(event) => update('nombre', event.target.value)} /></Field><Field label="CURP" htmlFor="curp" hint="Debe tener 18 caracteres."><Input id="curp" required maxLength={18} value={form.curp} onChange={(event) => update('curp', event.target.value.toUpperCase())} /></Field><Field label="Código postal" htmlFor="cp"><Input id="cp" required inputMode="numeric" maxLength={5} value={form.cp} onChange={(event) => update('cp', event.target.value)} /></Field><Field label="Domicilio" htmlFor="direccion"><Input id="direccion" required value={form.direccion} onChange={(event) => update('direccion', event.target.value)} /></Field></div> : null}
          {step === 3 ? <div><CardTitle>Elige fecha y hora</CardTitle><div className="mt-5 grid gap-5 md:grid-cols-2"><Field label="Fecha de la cita" htmlFor="fecha"><Input id="fecha" type="date" required value={form.fecha} onChange={(event) => update('fecha', event.target.value)} /></Field><div><span className="block text-sm font-semibold">Horario disponible</span>{loadingSlots ? <p className="mt-3 text-sm text-warm-500">Consultando horarios…</p> : <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">{slots.map((slot) => <button key={slot.hora} type="button" disabled={slot.ocupado} onClick={() => update('hora', slot.hora)} className={`rounded-xl border px-3 py-2 text-sm font-semibold transition duration-200 disabled:bg-warm-100 disabled:text-warm-500 ${form.hora === slot.hora ? 'border-primary bg-primary text-white' : 'border-warm-200 bg-white hover:border-primary'}`}><Clock3 className="mr-1 inline h-5 w-5" />{slot.hora}</button>)}</div>}</div></div></div> : null}
          <div className="mt-8 flex flex-wrap justify-between gap-3 border-t border-warm-200 pt-5">
            {step > 1 ? <Button type="button" variant="secondary" onClick={() => setStep((current) => current - 1)}><ChevronLeft className="h-6 w-6" />Anterior</Button> : <span />}
            {step === 1 ? <Button type="button" disabled={!form.tramite_id} onClick={() => setStep(2)}>Continuar<ChevronRight className="h-6 w-6" /></Button> : null}
            {step === 2 ? <Button type="button" disabled={!form.nombre || !form.curp || !form.cp || !form.direccion} onClick={validateCitizen}><UserRound className="h-6 w-6" />Validar y continuar</Button> : null}
            {step === 3 ? <Button type="submit" disabled={!form.fecha || !form.hora} loading={submitting}><CalendarCheck2 className="h-6 w-6" />Confirmar cita</Button> : null}
          </div>
        </Card>
      </form>
    </section>
  )
}
