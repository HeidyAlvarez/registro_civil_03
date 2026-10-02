import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Clock3, TrendingDown, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Alert, EmptyState, LoadingState } from '@/components/ui/feedback'
import { Field, Input, Select } from '@/components/ui/field'
import { useCatalog } from '@/hooks/use-catalog'
import { api } from '@/lib/api'

type Demand = { total_citas: number; por_dia: { nombre: string; total: number; pct: number }[]; por_hora: { hora: string; total: number; pct: number }[]; hallazgos: string[] }
type Suggestion = { error: string | null; options: { hora: string; nivel: 'baja' | 'media' | 'alta'; disponible: boolean; explicacion: string }[] }

export function DemandPage() {
  const query = useQuery({ queryKey: ['ai-demand'], queryFn: () => api<Demand>('/citas/ia/api/demanda/') })
  if (query.isLoading) return <LoadingState label="Analizando la afluencia…" />
  if (query.isError) return <Alert variant="error">{query.error.message}</Alert>
  return (
    <section>
      <p className="text-sm font-semibold text-primary">Análisis de afluencia</p><h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Días más concurridos</h1>
      <p className="mt-3 text-warm-500">Estas cifras se calculan con el historial del sistema y sirven como orientación.</p>
      {!query.data?.total_citas ? <div className="mt-8"><EmptyState title="Todavía no hay suficiente historial" description="El análisis aparecerá conforme se registren citas." /></div> : <>
        <div className="mt-8 grid gap-4 lg:grid-cols-2"><Card><CardTitle>Demanda por día</CardTitle><div className="mt-5 space-y-4">{query.data.por_dia.map((item) => <div key={item.nombre}><div className="mb-1 flex justify-between text-sm"><span>{item.nombre}</span><strong>{item.total} citas</strong></div><div className="h-3 overflow-hidden rounded-full bg-warm-100"><div className="h-full rounded-full bg-primary" style={{ width: `${item.pct}%` }} /></div></div>)}</div></Card><Card><CardTitle>Demanda por hora</CardTitle><div className="mt-5 grid grid-cols-2 gap-3">{query.data.por_hora.map((item) => <div key={item.hora} className="rounded-xl bg-warm-100 p-3"><span className="text-xs text-warm-500">{item.hora}</span><strong className="block text-lg">{item.total}</strong></div>)}</div></Card></div>
        <div className="mt-5 space-y-3">{query.data.hallazgos.map((finding) => <Alert key={finding}>{finding}</Alert>)}</div>
      </>}
    </section>
  )
}

export function ScheduleSuggestionPage() {
  const catalog = useCatalog()
  const [procedure, setProcedure] = useState('')
  const [date, setDate] = useState('')
  const [result, setResult] = useState<Suggestion | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError('')
    try { setResult(await api<Suggestion>(`/citas/ia/api/sugerencia/?tramite=${procedure}&fecha=${date}`)) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'No fue posible analizar los horarios.') }
    finally { setLoading(false) }
  }
  return (
    <section>
      <p className="text-sm font-semibold text-primary">Planea tu visita</p><h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Encuentra un horario conveniente</h1>
      <p className="mt-3 text-warm-500">Comparamos la disponibilidad real con la demanda histórica. Tú eliges la hora final.</p>
      <Card className="mt-8"><form className="grid gap-5 md:grid-cols-[1fr_220px_auto] md:items-end" onSubmit={submit}><Field label="Trámite" htmlFor="suggestion-procedure"><Select id="suggestion-procedure" required value={procedure} onChange={(event) => setProcedure(event.target.value)}><option value="">Selecciona una opción</option>{catalog.data?.secciones.flatMap((section) => section.tramites).map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select></Field><Field label="Fecha" htmlFor="suggestion-date"><Input id="suggestion-date" type="date" required value={date} onChange={(event) => setDate(event.target.value)} /></Field><Button loading={loading}><Clock3 className="h-6 w-6" />Analizar</Button></form></Card>
      {error ? <Alert variant="error" className="mt-5">{error}</Alert> : null}
      {result?.error ? <Alert variant="warning" className="mt-5">{result.error}</Alert> : null}
      {result?.options.length ? <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{result.options.map((option) => <Card key={option.hora} className={!option.disponible ? 'opacity-60' : option.nivel === 'baja' ? 'border-emerald-300' : ''}><div className="flex items-center justify-between"><CardTitle>{option.hora}</CardTitle>{option.nivel === 'baja' ? <TrendingDown className="h-7 w-7 text-emerald-600" /> : <TrendingUp className="h-7 w-7 text-amber-600" />}</div><CardDescription>{option.explicacion}</CardDescription><span className={`mt-4 inline-block rounded-full px-3 py-1 text-xs font-semibold ${option.disponible ? 'bg-accent text-primary' : 'bg-warm-200 text-warm-500'}`}>{option.disponible ? `Demanda ${option.nivel}` : 'No disponible'}</span></Card>)}</div> : null}
    </section>
  )
}
