import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Baby, CalendarCheck2, Check, ChevronLeft, ChevronRight, Clock3, Download, Mail, MapPin, Phone, UserRound } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Alert, LoadingState } from '@/components/ui/feedback'
import { Field, Input, Select } from '@/components/ui/field'
import { useCatalog } from '@/hooks/use-catalog'
import { api, postJson } from '@/lib/api'
import { formatMoney } from '@/lib/utils'

type Slot = { hora: string; ocupado: boolean }
type FormData = {
  tramite_id: string
  curp: string
  nombres: string
  apellido_paterno: string
  apellido_materno: string
  calle: string
  numero_exterior: string
  numero_interior: string
  colonia: string
  municipio: string
  estado: string
  cp: string
  fecha: string
  hora: string
  rn_nombre: string
  rn_apellido_paterno: string
  rn_apellido_materno: string
  rn_sexo: string
  rn_fecha: string
  rn_hora: string
  rn_lugar_tipo: string
  rn_lugar_nombre: string
  rn_municipio: string
}
const initialForm: FormData = {
  tramite_id: '', curp: '', nombres: '', apellido_paterno: '', apellido_materno: '',
  calle: '', numero_exterior: '', numero_interior: '', colonia: '', municipio: '',
  estado: 'Estado de México', cp: '', fecha: '', hora: '', rn_nombre: '',
  rn_apellido_paterno: '', rn_apellido_materno: '', rn_sexo: '', rn_fecha: '',
  rn_hora: '', rn_lugar_tipo: '', rn_lugar_nombre: '', rn_municipio: '',
}

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
  const isBirthRegistration = procedure?.nombre.toLocaleLowerCase('es').includes('nacimiento') ?? false
  const birthDataComplete = !isBirthRegistration || Boolean(
    form.rn_nombre && form.rn_apellido_paterno && form.rn_apellido_materno && form.rn_sexo
    && form.rn_fecha && form.rn_lugar_tipo && form.rn_lugar_nombre && form.rn_municipio,
  )
  const applicantDataComplete = Boolean(
    form.curp.length === 18 && form.nombres && form.apellido_paterno && form.apellido_materno
    && form.calle && form.numero_exterior && form.colonia && form.municipio
    && form.estado && form.cp.length === 5,
  )

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
      const nombre = [form.nombres, form.apellido_paterno, form.apellido_materno].filter(Boolean).join(' ')
      const direccion = [
        form.calle,
        `No. exterior ${form.numero_exterior}`,
        form.numero_interior ? `No. interior ${form.numero_interior}` : '',
        `Col. ${form.colonia}`,
        form.municipio,
        form.estado,
      ].filter(Boolean).join(', ')
      const datos_recien_nacido = isBirthRegistration ? {
        nombre: form.rn_nombre,
        apellido_paterno: form.rn_apellido_paterno,
        apellido_materno: form.rn_apellido_materno,
        sexo: form.rn_sexo,
        fecha_nacimiento: form.rn_fecha,
        hora_nacimiento: form.rn_hora,
        lugar_tipo: form.rn_lugar_tipo,
        lugar_nombre: form.rn_lugar_nombre,
        municipio_nacimiento: form.rn_municipio,
      } : undefined
      const response = await postJson<{ ok: boolean; error?: string; folio: number; qr_url: string; pdf_url: string }>('/citas/agendar/', {
        tramite_id: form.tramite_id, nombre, curp: form.curp, cp: form.cp, direccion,
        fecha: form.fecha, hora: form.hora, datos_recien_nacido,
      })
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
          {step === 1 ? (
            <div>
              <CardTitle>Selecciona el trámite</CardTitle>
              {catalog.isLoading ? <LoadingState /> : (
                <div className="mt-5">
                  <Field label="Trámite" htmlFor="tramite">
                    <Select id="tramite" required value={form.tramite_id} onChange={(event) => update('tramite_id', event.target.value)}>
                      <option value="">Selecciona una opción</option>
                      {catalog.data?.secciones.map((section) => (
                        <optgroup key={section.nombre} label={section.nombre}>
                          {section.tramites.map((item) => <option key={item.id} value={item.id}>{item.nombre} — {formatMoney(item.costo)}</option>)}
                        </optgroup>
                      ))}
                    </Select>
                  </Field>
                  {procedure ? <Alert className="mt-4"><strong>{procedure.duracion_minutos} minutos.</strong> {procedure.documentos || 'Consulta los documentos en el catálogo.'}</Alert> : null}
                  {isBirthRegistration ? (
                    <section className="mt-6 rounded-2xl border border-warm-200 bg-warm-100 p-5" aria-labelledby="datos-recien-nacido">
                      <div className="mb-5 flex items-center gap-3">
                        <Baby className="h-8 w-8 text-primary" aria-hidden="true" />
                        <div><h2 id="datos-recien-nacido" className="font-heading text-lg font-semibold">Datos del recién nacido</h2><p className="text-sm text-warm-500">Completa la información del registro de nacimiento.</p></div>
                      </div>
                      <div className="grid gap-5 md:grid-cols-2">
                        <Field label="Nombre(s) *" htmlFor="rn-nombre"><Input id="rn-nombre" required value={form.rn_nombre} onChange={(event) => update('rn_nombre', event.target.value)} /></Field>
                        <Field label="Sexo *" htmlFor="rn-sexo"><Select id="rn-sexo" required value={form.rn_sexo} onChange={(event) => update('rn_sexo', event.target.value)}><option value="">Selecciona</option><option value="H">Hombre</option><option value="M">Mujer</option></Select></Field>
                        <Field label="Apellido paterno *" htmlFor="rn-apellido-paterno"><Input id="rn-apellido-paterno" required value={form.rn_apellido_paterno} onChange={(event) => update('rn_apellido_paterno', event.target.value)} /></Field>
                        <Field label="Apellido materno *" htmlFor="rn-apellido-materno"><Input id="rn-apellido-materno" required value={form.rn_apellido_materno} onChange={(event) => update('rn_apellido_materno', event.target.value)} /></Field>
                        <Field label="Fecha de nacimiento *" htmlFor="rn-fecha"><Input id="rn-fecha" type="date" required value={form.rn_fecha} onChange={(event) => update('rn_fecha', event.target.value)} /></Field>
                        <Field label="Hora de nacimiento" htmlFor="rn-hora" hint="Opcional, si aparece en el certificado."><Input id="rn-hora" type="time" value={form.rn_hora} onChange={(event) => update('rn_hora', event.target.value)} /></Field>
                        <Field label="Tipo de lugar *" htmlFor="rn-lugar-tipo"><Select id="rn-lugar-tipo" required value={form.rn_lugar_tipo} onChange={(event) => update('rn_lugar_tipo', event.target.value)}><option value="">Selecciona</option><option value="hospital">Hospital</option><option value="clinica">Clínica</option><option value="domicilio">Domicilio</option><option value="otro">Otra localidad</option></Select></Field>
                        <Field label="Hospital, clínica o localidad *" htmlFor="rn-lugar-nombre"><Input id="rn-lugar-nombre" required value={form.rn_lugar_nombre} onChange={(event) => update('rn_lugar_nombre', event.target.value)} /></Field>
                        <Field label="Municipio de nacimiento *" htmlFor="rn-municipio"><Input id="rn-municipio" required value={form.rn_municipio} onChange={(event) => update('rn_municipio', event.target.value)} /></Field>
                      </div>
                    </section>
                  ) : null}
                </div>
              )}
            </div>
          ) : null}
          {step === 2 ? (
            <div>
              <CardTitle>Datos de la persona solicitante</CardTitle>
              <p className="mt-2 text-sm text-warm-500">Captura los mismos datos solicitados en el formulario original.</p>
              <div className="mt-6 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                <Field label="CURP *" htmlFor="curp" hint="Debe tener 18 caracteres."><Input id="curp" required maxLength={18} autoCapitalize="characters" value={form.curp} onChange={(event) => update('curp', event.target.value.toUpperCase())} /></Field>
                <Field label="Apellido paterno *" htmlFor="apellido-paterno"><Input id="apellido-paterno" required autoComplete="family-name" value={form.apellido_paterno} onChange={(event) => update('apellido_paterno', event.target.value)} /></Field>
                <Field label="Apellido materno *" htmlFor="apellido-materno"><Input id="apellido-materno" required autoComplete="additional-name" value={form.apellido_materno} onChange={(event) => update('apellido_materno', event.target.value)} /></Field>
                <Field label="Nombre(s) *" htmlFor="nombres"><Input id="nombres" required autoComplete="given-name" value={form.nombres} onChange={(event) => update('nombres', event.target.value)} /></Field>
                <Field label="Calle *" htmlFor="calle"><Input id="calle" required autoComplete="address-line1" value={form.calle} onChange={(event) => update('calle', event.target.value)} /></Field>
                <Field label="No. exterior *" htmlFor="numero-exterior"><Input id="numero-exterior" required value={form.numero_exterior} onChange={(event) => update('numero_exterior', event.target.value)} /></Field>
                <Field label="No. interior" htmlFor="numero-interior" hint="Opcional"><Input id="numero-interior" value={form.numero_interior} onChange={(event) => update('numero_interior', event.target.value)} /></Field>
                <Field label="Colonia *" htmlFor="colonia"><Input id="colonia" required value={form.colonia} onChange={(event) => update('colonia', event.target.value)} /></Field>
                <Field label="Municipio *" htmlFor="municipio"><Input id="municipio" required value={form.municipio} onChange={(event) => update('municipio', event.target.value)} /></Field>
                <Field label="Estado *" htmlFor="estado"><Input id="estado" required value={form.estado} onChange={(event) => update('estado', event.target.value)} /></Field>
                <Field label="Código postal *" htmlFor="cp"><Input id="cp" required inputMode="numeric" autoComplete="postal-code" maxLength={5} value={form.cp} onChange={(event) => update('cp', event.target.value.replace(/\D/g, ''))} /></Field>
              </div>
            </div>
          ) : null}
          {step === 3 ? <div><CardTitle>Elige fecha y hora</CardTitle><div className="mt-5 grid gap-5 md:grid-cols-2"><Field label="Fecha de la cita" htmlFor="fecha"><Input id="fecha" type="date" required value={form.fecha} onChange={(event) => update('fecha', event.target.value)} /></Field><div><span className="block text-sm font-semibold">Horario disponible</span>{loadingSlots ? <p className="mt-3 text-sm text-warm-500">Consultando horarios…</p> : <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">{slots.map((slot) => <button key={slot.hora} type="button" disabled={slot.ocupado} onClick={() => update('hora', slot.hora)} className={`rounded-xl border px-3 py-2 text-sm font-semibold transition duration-200 disabled:bg-warm-100 disabled:text-warm-500 ${form.hora === slot.hora ? 'border-primary bg-primary text-white' : 'border-warm-200 bg-white hover:border-primary'}`}><Clock3 className="mr-1 inline h-5 w-5" />{slot.hora}</button>)}</div>}</div></div></div> : null}
          <div className="mt-8 flex flex-wrap justify-between gap-3 border-t border-warm-200 pt-5">
            {step > 1 ? <Button type="button" variant="secondary" onClick={() => setStep((current) => current - 1)}><ChevronLeft className="h-6 w-6" />Anterior</Button> : <span />}
            {step === 1 ? <Button type="button" disabled={!form.tramite_id || !birthDataComplete} onClick={() => setStep(2)}>Continuar<ChevronRight className="h-6 w-6" /></Button> : null}
            {step === 2 ? <Button type="button" disabled={!applicantDataComplete} onClick={validateCitizen}><UserRound className="h-6 w-6" />Validar y continuar</Button> : null}
            {step === 3 ? <Button type="submit" disabled={!form.fecha || !form.hora} loading={submitting}><CalendarCheck2 className="h-6 w-6" />Confirmar cita</Button> : null}
          </div>
        </Card>
      </form>
      <aside className="mt-8 rounded-2xl border border-warm-200 bg-white p-6 shadow-soft" aria-labelledby="contacto-oficialia">
        <h2 id="contacto-oficialia" className="font-heading text-lg font-semibold">Ubicación y contacto de la Oficialía 03</h2>
        <p className="mt-2 text-sm text-warm-500">Esta información permanece visible para que puedas comunicarte o llegar al lugar de tu cita.</p>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <a className="flex items-start gap-3 rounded-xl bg-warm-100 p-4 text-warm-900 transition hover:bg-accent focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20" href="tel:+527262515238">
            <Phone className="h-7 w-7 shrink-0 text-primary" aria-hidden="true" /><span><strong className="block">Teléfono</strong><span className="text-sm">(726) 251 5238</span></span>
          </a>
          <a className="flex items-start gap-3 rounded-xl bg-warm-100 p-4 text-warm-900 transition hover:bg-accent focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20" href="mailto:rc_villavictoria03@edomex.gob.mx">
            <Mail className="h-7 w-7 shrink-0 text-primary" aria-hidden="true" /><span><strong className="block">Correo</strong><span className="break-all text-sm">rc_villavictoria03@edomex.gob.mx</span></span>
          </a>
          <a className="flex items-start gap-3 rounded-xl bg-warm-100 p-4 text-warm-900 transition hover:bg-accent focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20" href="https://maps.app.goo.gl/1fw4Pw9aHDKFBfbn6" target="_blank" rel="noreferrer">
            <MapPin className="h-7 w-7 shrink-0 text-primary" aria-hidden="true" /><span><strong className="block">Ubicación</strong><span className="text-sm">Col. Dr. Gustavo Baz Prada, Villa Victoria, C.P. 50960</span></span>
          </a>
        </div>
      </aside>
    </section>
  )
}
