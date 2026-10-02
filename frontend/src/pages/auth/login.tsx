import { useState, type FormEvent } from 'react'
import { KeyRound, LogIn, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Alert } from '@/components/ui/feedback'
import { Field, Input } from '@/components/ui/field'
import { postJson } from '@/lib/api'

export function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError('')
    try {
      await postJson('/citas/api/v1/auth/login/', { username, password })
      navigate('/panel', { replace: true })
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No fue posible iniciar sesión.') } finally { setLoading(false) }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-warm-100 p-4">
      <Card className="w-full max-w-md p-7">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-primary text-white"><ShieldCheck className="h-8 w-8" /></span>
        <h1 className="mt-5 font-heading text-2xl font-semibold">Acceso del personal</h1>
        <p className="mt-2 text-sm text-warm-500">Esta sección es únicamente para personal autorizado de la Oficialía 03.</p>
        {error ? <Alert variant="error" className="mt-5">{error}</Alert> : null}
        <form className="mt-6 space-y-5" onSubmit={submit}>
          <Field label="Usuario" htmlFor="username"><Input id="username" autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} /></Field>
          <Field label="Contraseña" htmlFor="password"><Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></Field>
          <Button className="w-full" size="large" loading={loading}><LogIn className="h-6 w-6" />Iniciar sesión</Button>
        </form>
        <p className="mt-6 flex items-start gap-2 text-xs text-warm-500"><KeyRound className="h-5 w-5 shrink-0" />La sesión se cierra después de 30 minutos de inactividad.</p>
      </Card>
    </main>
  )
}
