import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export type SessionUser = {
  authenticated: boolean
  username?: string
  full_name?: string
  role?: 'ADMIN' | 'OFICIAL' | 'CAPTURISTA'
  permissions: {
    staff: boolean
    official: boolean
    administrator: boolean
    internal_ai: boolean
  }
}

export function useSession() {
  return useQuery({
    queryKey: ['session'],
    queryFn: () => api<SessionUser>('/citas/api/v1/auth/me/'),
    retry: false,
    staleTime: 60_000,
  })
}
