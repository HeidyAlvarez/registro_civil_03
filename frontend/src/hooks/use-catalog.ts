import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export type Procedure = {
  id: number
  nombre: string
  costo: number
  duracion_minutos: number
  documentos: string
}

export type ProcedureSection = {
  nombre: string
  tramites: Procedure[]
}

export function useCatalog() {
  return useQuery({
    queryKey: ['catalog'],
    queryFn: () => api<{ secciones: ProcedureSection[] }>('/citas/api/tramites/'),
    staleTime: 5 * 60_000,
  })
}
