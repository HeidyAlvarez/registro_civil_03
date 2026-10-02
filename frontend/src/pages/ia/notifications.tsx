import { useState, type FormEvent } from 'react'
import { Bell, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Alert, EmptyState } from '@/components/ui/feedback'
import { Field, Input } from '@/components/ui/field'
import { api } from '@/lib/api'

type Notification = { id: number; category: string; title: string; message: string; read: boolean; created_at: string }

export function NotificationsPage() {
  const [curp, setCurp] = useState('')
  const [notifications, setNotifications] = useState<Notification[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError('')
    try { setNotifications((await api<{ notifications: Notification[] }>(`/citas/ia/api/notificaciones/?curp=${encodeURIComponent(curp)}`)).notifications) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'No fue posible consultar los avisos.') }
    finally { setLoading(false) }
  }
  return <section className="mx-auto max-w-3xl"><p className="text-sm font-semibold text-primary">Seguimiento ciudadano</p><h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Notificaciones inteligentes</h1><p className="mt-3 text-warm-500">Consulta recordatorios y cambios relacionados con tu cita.</p><Card className="mt-8"><form className="flex flex-col gap-4 sm:flex-row sm:items-end" onSubmit={submit}><div className="flex-1"><Field label="CURP" htmlFor="notification-curp"><Input id="notification-curp" required maxLength={18} value={curp} onChange={(event) => setCurp(event.target.value.toUpperCase())} /></Field></div><Button loading={loading}><Search className="h-6 w-6" />Consultar</Button></form></Card>{error ? <Alert variant="error" className="mt-5">{error}</Alert> : null}{notifications && !notifications.length ? <div className="mt-6"><EmptyState title="No tienes avisos" description="No encontramos notificaciones asociadas con esta CURP." /></div> : <div className="mt-6 space-y-4">{notifications?.map((item) => <Card key={item.id}><div className="flex gap-4"><Bell className="h-7 w-7 shrink-0 text-primary" /><div><CardTitle>{item.title}</CardTitle><CardDescription>{item.message}</CardDescription><p className="mt-3 text-xs text-warm-500">{new Date(item.created_at).toLocaleString('es-MX')} · {item.category}</p></div></div></Card>)}</div>}</section>
}
