import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Camera, CameraOff, QrCode, ScanLine } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Alert } from '@/components/ui/feedback'
import { Field, Input } from '@/components/ui/field'
import { api } from '@/lib/api'

type BarcodeDetectorConstructor = new (options: { formats: string[] }) => {
  detect(source: HTMLVideoElement): Promise<{ rawValue: string }[]>
}

export function ScannerPage() {
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const [appointmentId, setAppointmentId] = useState('')
  const [token, setToken] = useState('')
  const [camera, setCamera] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null)

  function parse(value: string) {
    const match = value.match(/validar\/(\d+)\/([^/?#]+)/)
    if (match) { setAppointmentId(match[1]); setToken(match[2]); stopCamera() }
  }

  async function startCamera() {
    setMessage(null)
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      if (video.current) { video.current.srcObject = stream.current; await video.current.play() }
      setCamera(true)
      const Detector = (window as unknown as { BarcodeDetector?: BarcodeDetectorConstructor }).BarcodeDetector
      if (Detector) {
        const detector = new Detector({ formats: ['qr_code'] })
        timer.current = window.setInterval(async () => {
          if (!video.current) return
          const results = await detector.detect(video.current)
          if (results[0]) parse(results[0].rawValue)
        }, 500)
      }
    } catch { setMessage({ text: 'No fue posible abrir la cámara. Puedes capturar los datos manualmente.', error: true }) }
  }

  function stopCamera() {
    if (timer.current) window.clearInterval(timer.current)
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null; setCamera(false)
  }
  useEffect(() => stopCamera, [])

  async function validate(event: FormEvent) {
    event.preventDefault(); setLoading(true); setMessage(null)
    const body = new FormData(); body.set('token', token)
    try {
      const result = await api<{ status: string; message?: string; ciudadano?: string; tramite?: string }>(`/citas/validar-qr/${appointmentId}/`, { method: 'POST', body })
      if (result.status !== 'success') throw new Error(result.message || 'El código no es válido.')
      setMessage({ text: `Asistencia confirmada para ${result.ciudadano}. Trámite: ${result.tramite}.`, error: false })
    } catch (reason) { setMessage({ text: reason instanceof Error ? reason.message : 'No fue posible validar.', error: true }) } finally { setLoading(false) }
  }

  return (
    <section>
      <p className="text-sm font-semibold text-primary">Recepción</p><h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Escanear comprobante QR</h1>
      <p className="mt-3 text-warm-500">Apunta la cámara al código del comprobante o captura los datos manualmente.</p>
      {message ? <Alert variant={message.error ? 'error' : 'success'} className="mt-6">{message.text}</Alert> : null}
      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <Card><Camera className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Usar cámara</CardTitle><CardDescription>El navegador solicitará permiso únicamente mientras esta pantalla esté abierta.</CardDescription><div className="mt-5 overflow-hidden rounded-2xl bg-warm-900"><video ref={video} className="aspect-video w-full object-cover" muted playsInline /></div><Button className="mt-4 w-full" variant={camera ? 'danger' : 'secondary'} onClick={camera ? stopCamera : startCamera}>{camera ? <><CameraOff className="h-6 w-6" />Cerrar cámara</> : <><ScanLine className="h-6 w-6" />Abrir cámara</>}</Button></Card>
        <Card><QrCode className="h-9 w-9 text-primary" /><CardTitle className="mt-4">Validación manual</CardTitle><form className="mt-5 space-y-5" onSubmit={validate}><Field label="Folio de cita" htmlFor="scan-id"><Input id="scan-id" required inputMode="numeric" value={appointmentId} onChange={(event) => setAppointmentId(event.target.value)} /></Field><Field label="Código de seguridad" htmlFor="scan-token"><Input id="scan-token" required value={token} onChange={(event) => setToken(event.target.value)} /></Field><Button className="w-full" loading={loading}><QrCode className="h-6 w-6" />Validar asistencia</Button></form></Card>
      </div>
    </section>
  )
}
