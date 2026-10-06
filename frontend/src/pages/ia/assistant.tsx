import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Bell, Bot, Clock3, Send, Sparkles, Trash2, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Alert, LoadingState } from '@/components/ui/feedback'
import { Textarea } from '@/components/ui/field'
import { AssistantMascot } from '@/components/ia/assistant-mascot'
import { api, postJson } from '@/lib/api'
import { cn } from '@/lib/utils'

type Message = { id: number; role: 'ciudadano' | 'asistente'; text: string; options: { etiqueta: string; valor: string }[]; refer: boolean }

export function AiHubPage() {
  return (
    <section>
      <p className="text-sm font-semibold text-primary">Inteligencia artificial responsable</p>
      <h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Orientación inteligente para tu trámite</h1>
      <p className="mt-3 max-w-3xl text-warm-500">La IA explica información oficial y analiza la demanda. No toma decisiones legales ni cambia citas sin autorización.</p>
      <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Link to="/inteligencia/asistente"><Card className="h-full transition hover:border-primary"><Bot className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Asistente</CardTitle><CardDescription>Pregunta con tus propias palabras.</CardDescription></Card></Link>
        <Link to="/inteligencia/afluencia"><Card className="h-full transition hover:border-primary"><TrendingUp className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Días concurridos</CardTitle><CardDescription>Consulta cuándo hay mayor demanda.</CardDescription></Card></Link>
        <Link to="/inteligencia/horario"><Card className="h-full transition hover:border-primary"><Clock3 className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Mejor horario</CardTitle><CardDescription>Compara horarios disponibles.</CardDescription></Card></Link>
        <Link to="/inteligencia/notificaciones"><Card className="h-full transition hover:border-primary"><Bell className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Notificaciones</CardTitle><CardDescription>Consulta avisos vinculados con tu CURP.</CardDescription></Card></Link>
      </div>
    </section>
  )
}

export function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const log = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api<{ messages: Message[] }>('/citas/ia/api/asistente/').then((data) => setMessages(data.messages)).catch((reason: Error) => setError(reason.message)).finally(() => setLoading(false))
    return () => { api('/citas/ia/api/asistente/', { method: 'DELETE', keepalive: true }).catch(() => undefined) }
  }, [])
  useEffect(() => { log.current?.scrollTo({ top: log.current.scrollHeight, behavior: 'smooth' }) }, [messages])

  async function send(event: FormEvent, shortcut?: string) {
    event.preventDefault(); const text = (shortcut || question).trim(); if (!text) return
    const optimistic: Message = { id: Date.now(), role: 'ciudadano', text, options: [], refer: false }
    setMessages((current) => [...current, optimistic]); setQuestion(''); setSending(true); setError('')
    try {
      const response = await postJson<{ message: Message }>('/citas/ia/api/asistente/mensaje/', { question: text })
      setMessages((current) => [...current, response.message])
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'El asistente no pudo responder.') } finally { setSending(false) }
  }

  async function clear() {
    await api('/citas/ia/api/asistente/', { method: 'DELETE' }); setMessages([])
  }

  if (loading) return <LoadingState label="Iniciando una conversación temporal…" />
  return (
    <section className="mx-auto max-w-6xl">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-semibold text-primary">Conversación temporal</p><h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Asistente inteligente</h1><p className="mt-3 text-warm-500">El chat se elimina cuando sales de esta pantalla.</p></div>{messages.length ? <Button variant="ghost" onClick={clear}><Trash2 className="h-6 w-6" />Limpiar chat</Button> : null}</div>
      {error ? <Alert variant="error" className="mt-5">{error}</Alert> : null}
      <div className="mt-7 grid items-start gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
      <AssistantMascot modo="ciudadano" estado={sending ? 'pensando' : messages.length ? 'hablando' : 'idle'} />
      <Card className="p-3 sm:p-5">
        <div ref={log} className="max-h-[52vh] min-h-80 space-y-4 overflow-y-auto rounded-xl bg-warm-100 p-4" role="log" aria-live="polite">
          {!messages.length ? <div className="max-w-xl rounded-2xl bg-white p-4 shadow-sm"><strong className="flex items-center gap-2 text-primary"><Sparkles className="h-6 w-6" />Asistente</strong><p className="mt-2 text-sm text-warm-700">Hola. Puedo orientarte sobre trámites, documentos, costos, horarios y citas. Escribe tu pregunta con tus propias palabras.</p></div> : null}
          {messages.map((message) => <div key={message.id} className={cn('max-w-[88%] rounded-2xl p-4 text-sm leading-6 shadow-sm', message.role === 'ciudadano' ? 'ml-auto bg-primary text-white' : 'bg-white text-warm-900')}><strong className="mb-1 block text-xs uppercase tracking-wide opacity-75">{message.role === 'ciudadano' ? 'Tú' : 'Asistente'}</strong>{message.text}{message.options?.length ? <div className="mt-3 flex flex-wrap gap-2">{message.options.map((option) => <button key={option.valor} onClick={(event) => send(event, option.valor)} className="rounded-xl border border-primary px-3 py-2 text-left text-xs font-semibold text-primary hover:bg-accent">{option.etiqueta}</button>)}</div> : null}</div>)}
          {sending ? <div className="max-w-sm rounded-2xl bg-white p-4 text-sm text-warm-500">Analizando tu pregunta…</div> : null}
        </div>
        {!messages.length ? <div className="my-4 flex flex-wrap gap-2">{['¿Qué necesito para registrar un matrimonio?', '¿Cuál es el horario de atención?', '¿Cuánto cuesta una copia certificada?'].map((text) => <button key={text} className="rounded-xl border border-warm-200 bg-white px-3 py-2 text-sm hover:border-primary" onClick={(event) => send(event, text)}>{text}</button>)}</div> : null}
        <form onSubmit={send} className="mt-4 space-y-3"><label className="block text-sm font-semibold" htmlFor="question">Tu pregunta</label><Textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ejemplo: ¿Qué documentos necesito llevar?" required /><Button className="w-full" loading={sending}><Send className="h-6 w-6" />Enviar pregunta</Button></form>
      </Card>
      </div>
    </section>
  )
}
