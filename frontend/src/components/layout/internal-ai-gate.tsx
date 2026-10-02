import { Navigate, Outlet } from 'react-router-dom'
import { LoadingState } from '@/components/ui/feedback'
import { useSession } from '@/hooks/use-session'

export function InternalAiGate() {
  const session = useSession()
  if (session.isLoading) return <LoadingState label="Validando tu acceso…" />
  if (!session.data?.permissions.internal_ai) return <Navigate to="/panel" replace />
  return <Outlet />
}
