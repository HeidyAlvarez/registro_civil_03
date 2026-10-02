import { useQuery } from '@tanstack/react-query'
import { CalendarClock, CircleDollarSign, ClipboardCheck, UsersRound } from 'lucide-react'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Alert, LoadingState } from '@/components/ui/feedback'
import { api } from '@/lib/api'
import { formatMoney } from '@/lib/utils'

type Dashboard = {
  total_citas_hoy: number
  citas_pendientes: number
  citas_en_caja: number
  citas_finalizadas: number
  ingresos_hoy: number
}

export function DashboardPage() {
  const summary = useQuery({ queryKey: ['dashboard'], queryFn: () => api<Dashboard>('/citas/api/dashboard/'), refetchInterval: 60_000 })
  if (summary.isLoading) return <LoadingState label="Preparando el resumen del día…" />
  if (summary.isError) return <Alert variant="error">{summary.error.message}</Alert>
  const items = [
    ['Citas de hoy', summary.data?.total_citas_hoy || 0, UsersRound],
    ['Pendientes', summary.data?.citas_pendientes || 0, CalendarClock],
    ['En caja', summary.data?.citas_en_caja || 0, CircleDollarSign],
    ['Finalizadas', summary.data?.citas_finalizadas || 0, ClipboardCheck],
  ] as const
  return (
    <section>
      <p className="text-sm font-semibold text-primary">Operación diaria</p>
      <h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Resumen de la oficialía</h1>
      <p className="mt-3 text-warm-500">Información actualizada automáticamente para organizar la atención.</p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {items.map(([label, value, Icon]) => <Card key={label}><Icon className="h-8 w-8 text-primary" /><p className="mt-4 text-sm font-semibold text-warm-500">{label}</p><p className="mt-1 font-heading text-4xl font-semibold">{value}</p></Card>)}
      </div>
      <Card className="mt-6 bg-primary text-white"><CardTitle className="text-white">Ingresos registrados hoy</CardTitle><CardDescription className="text-white/70">Pagos vigentes, sin citas canceladas.</CardDescription><p className="mt-4 font-heading text-4xl font-semibold">{formatMoney(summary.data?.ingresos_hoy || 0)}</p></Card>
    </section>
  )
}
