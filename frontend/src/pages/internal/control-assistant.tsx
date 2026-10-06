import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Bot, Send, Sparkles, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Alert } from '@/components/ui/feedback'
import { Textarea } from '@/components/ui/field'
import { AssistantMascot } from '@/components/ia/assistant-mascot'
import { postJson } from '@/lib/api'
import { cn } from '@/lib/utils'

type Message = { id: number; role: 'personal' | 'asistente'; text: string }

const examples = [
  '¿Cuántas citas hay pendientes hoy?',
  '¿Qué movimientos de la operación conviene revisar?',
  '¿Qué decisión sugieres con los datos de hoy?',
]

export function InternalAssistantPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const log = useRef<HTMLDivElement>(null)

  useEffect(() => {
    return () => {
      setMessages([])
    }
  }, [])
  useEffect(() => {
    log.current?.scrollTo?.({ top: log.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function send(event: FormEvent, shortcut?: string) {
    event.preventDefault()
    const text = (shortcut || question).trim()
    if (!text || sending) return
    const history = messages.map((message) => ({ role: message.role, text: message.text }))
    setMessages((current) => [...current, { id: Date.now(), role: 'personal', text }])
    setQuestion('')
    setSending(true)
    setError('')
    try {
      const response = await postJson<{ message: { role: 'asistente'; text: string } }>(
        '/citas/ia/api/interno/asistente/mensaje/',
        { question: text, history },
      )
      setMessages((current) => [...current, { id: Date.now() + 1, role: 'asistente', text: response.message.text }])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'El asistente no pudo responder.')
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="mx-auto max-w-6xl">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold text-primary">Control interno</p>
          <h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Asistente de control</h1>
          <p className="mt-3 text-warm-500">
            Pregunta sobre las citas, los movimientos de la operación y las decisiones que conviene tomar.
            Esta conversación se borra al salir de la pantalla y no se guarda en el sistema.
          </p>
        </div>
        {messages.length ? (
          <Button variant="ghost" onClick={() => setMessages([])}>
            <Trash2 className="h-6 w-6" />Limpiar chat
          </Button>
        ) : null}
      </div>
      {error ? <Alert variant="error" className="mt-5">{error}</Alert> : null}
      <div className="mt-7 grid items-start gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
      <AssistantMascot modo="interno" estado={sending ? 'pensando' : messages.length ? 'hablando' : 'idle'} />
      <Card className="p-3 sm:p-5">
        <div ref={log} className="max-h-[52vh] min-h-80 space-y-4 overflow-y-auto rounded-xl bg-warm-100 p-4" role="log" aria-live="polite">
          {!messages.length ? (
            <div className="max-w-xl rounded-2xl bg-white p-4 shadow-sm">
              <strong className="flex items-center gap-2 text-primary"><Sparkles className="h-6 w-6" />Asistente</strong>
              <p className="mt-2 text-sm text-warm-700">
                Hola. Puedo ayudarte a revisar la agenda de hoy, los movimientos recientes y las opciones que muestran los datos.
                La decisión final sigue siendo del personal.
              </p>
            </div>
          ) : null}
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'max-w-[88%] whitespace-pre-wrap rounded-2xl p-4 text-sm leading-6 shadow-sm',
                message.role === 'personal' ? 'ml-auto bg-primary text-white' : 'bg-white text-warm-900',
              )}
            >
              <strong className="mb-1 block text-xs uppercase tracking-wide opacity-75">
                {message.role === 'personal' ? 'Tú' : 'Asistente'}
              </strong>
              {message.text}
            </div>
          ))}
          {sending ? <div className="max-w-sm rounded-2xl bg-white p-4 text-sm text-warm-500">Revisando los datos del sistema…</div> : null}
        </div>
        {!messages.length ? (
          <div className="my-4 flex flex-wrap gap-2">
            {examples.map((text) => (
              <button type="button" key={text} className="rounded-xl border border-warm-200 bg-white px-3 py-2 text-left text-sm hover:border-primary" onClick={(event) => send(event, text)}>
                {text}
              </button>
            ))}
          </div>
        ) : null}
        <form onSubmit={send} className="mt-4 space-y-3">
          <label className="block text-sm font-semibold" htmlFor="control-question">Tu pregunta</label>
          <Textarea id="control-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ejemplo: ¿Cuántas citas pendientes hay hoy?" required />
          <Button className="w-full" loading={sending}><Send className="h-6 w-6" />Enviar pregunta</Button>
        </form>
      </Card>
      </div>
      <p className="mt-4 flex items-center gap-2 text-sm text-warm-500"><Bot className="h-5 w-5 text-primary" />Las cifras salen de la agenda y del seguimiento del día. Si un dato no está en el sistema, el asistente lo dice.</p>
    </section>
  )
}
