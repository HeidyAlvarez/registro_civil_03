import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, CheckCircle2, CircleDollarSign, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Alert, EmptyState, LoadingState } from '@/components/ui/feedback'
import { api } from '@/lib/api'
import { formatDate, formatMoney } from '@/lib/utils'

type Appointment = { id: number; fecha: string; hora: string; nombre: string; curp: string; tramite: string; estado: string; costo: number }

export function AppointmentsPage({ mode = 'agenda' }: { mode?: 'agenda' | 'cash' | 'history' }) {
  const queryClient = useQueryClient()
  const query = mode === 'agenda' ? 'incluir_futuras=1' : mode === 'cash' ? 'estado=ASISTIDA' : 'estado=FINALIZADA,CANCELADA'
  const appointments = useQuery({ queryKey: ['appointments', mode], queryFn: () => api<{ citas: Appointment[] }>(`/citas/api/citas/?${query}`), refetchInterval: 30_000 })
  const action = useMutation({
    mutationFn: ({ url }: { url: string }) => api(url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' }, body: new FormData() }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['appointments'] }),
  })
  const title = mode === 'agenda' ? 'Agenda de atención' : mode === 'cash' ? 'Fila de caja' : 'Historial de citas'
  if (appointments.isLoading) return <LoadingState />
  return (
    <section>
      <p className="text-sm font-semibold text-primary">Control operativo</p>
      <h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">{title}</h1>
      <p className="mt-3 text-warm-500">{mode === 'agenda' ? 'Citas pendientes de hoy y próximas fechas.' : mode === 'cash' ? 'Personas cuya asistencia ya fue validada.' : 'Consulta los movimientos finalizados y cancelados.'}</p>
      {appointments.isError ? <Alert variant="error" className="mt-6">{appointments.error.message}</Alert> : null}
      {action.isError ? <Alert variant="error" className="mt-6">{action.error.message}</Alert> : null}
      {!appointments.data?.citas.length ? <div className="mt-8"><EmptyState title="No hay citas en esta sección" description="La lista se actualizará cuando existan registros." /></div> : (
        <div className="mt-8 grid gap-4">
          {appointments.data.citas.map((appointment) => (
            <Card key={appointment.id} className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
              <div className="flex gap-4"><span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-accent text-primary">{mode === 'cash' ? <CircleDollarSign className="h-7 w-7" /> : <CalendarDays className="h-7 w-7" />}</span><div><h2 className="font-heading font-semibold">{appointment.nombre}</h2><p className="text-sm text-warm-500">{appointment.tramite} · {formatDate(appointment.fecha)} a las {appointment.hora}</p><span className="mt-2 inline-block rounded-full bg-warm-100 px-3 py-1 text-xs font-semibold">{appointment.estado}</span></div></div>
              <div className="flex items-center gap-3 lg:text-right"><strong className="mr-auto text-primary lg:mr-2">{formatMoney(appointment.costo)}</strong>{mode === 'cash' ? <Button loading={action.isPending} onClick={() => action.mutate({ url: `/citas/caja/cobrar/${appointment.id}/` })}><CircleDollarSign className="h-6 w-6" />Registrar pago</Button> : null}{mode === 'agenda' && appointment.estado === 'ASISTIDA' ? <Button variant="secondary" loading={action.isPending} onClick={() => action.mutate({ url: `/citas/citas/revertir-asistencia/${appointment.id}/` })}><RefreshCw className="h-6 w-6" />Revertir</Button> : null}{mode === 'history' ? <CheckCircle2 className="h-7 w-7 text-primary" /> : null}</div>
            </Card>
          ))}
        </div>
      )}
    </section>
  )
}
