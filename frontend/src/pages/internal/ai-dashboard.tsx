import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Bot, FileWarning, Lightbulb, UsersRound } from 'lucide-react'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Alert, LoadingState } from '@/components/ui/feedback'
import { api } from '@/lib/api'

type Summary = { alerts: number; anomalies: number; proposals: number; requests: number; demand: { hallazgos: string[] }; seasons: { frases: string[] } }

export function AiDashboardPage() {
  const summary = useQuery({ queryKey: ['internal-ai'], queryFn: () => api<Summary>('/citas/ia/api/interno/resumen/') })
  if (summary.isLoading) return <LoadingState label="Actualizando el análisis institucional…" />
  if (summary.isError) return <Alert variant="error">{summary.error.message}</Alert>
  const cards = [
    ['Casos urgentes', summary.data?.alerts || 0, AlertTriangle],
    ['Anomalías nuevas', summary.data?.anomalies || 0, FileWarning],
    ['Propuestas', summary.data?.proposals || 0, Lightbulb],
    ['Atención ciudadana', summary.data?.requests || 0, UsersRound],
  ] as const
  return (
    <section>
      <p className="text-sm font-semibold text-primary">Control interno</p><h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Módulo de inteligencia artificial</h1>
      <p className="mt-3 max-w-3xl text-warm-500">La IA detecta patrones y genera propuestas. El personal autorizado conserva la decisión final.</p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value, Icon]) => <Card key={label}><Icon className="h-8 w-8 text-primary" /><p className="mt-4 text-sm font-semibold text-warm-500">{label}</p><p className="mt-1 font-heading text-4xl font-semibold">{value}</p></Card>)}</div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2"><Card><Bot className="h-8 w-8 text-primary" /><CardTitle className="mt-4">Hallazgos de demanda</CardTitle><CardDescription>Resumen generado con datos del sistema.</CardDescription><div className="mt-4 space-y-3">{summary.data?.demand.hallazgos.map((item) => <Alert key={item}>{item}</Alert>)}</div></Card><Card><Lightbulb className="h-8 w-8 text-primary" /><CardTitle className="mt-4">Cambios de temporada</CardTitle><CardDescription>Comparación con el historial disponible.</CardDescription><div className="mt-4 space-y-3">{summary.data?.seasons.frases.map((item) => <Alert key={item} variant="warning">{item}</Alert>)}</div></Card></div>
    </section>
  )
}
