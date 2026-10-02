import { Clock3, FileText } from 'lucide-react'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Alert, EmptyState, LoadingState } from '@/components/ui/feedback'
import { useCatalog } from '@/hooks/use-catalog'
import { formatMoney } from '@/lib/utils'

export function CatalogPage() {
  const catalog = useCatalog()
  return (
    <section>
      <p className="text-sm font-semibold text-primary">Información oficial</p>
      <h1 className="mt-1 font-heading text-2xl font-semibold md:text-4xl">Trámites, requisitos y costos</h1>
      <p className="mt-3 max-w-2xl text-warm-500">Consulta qué documentos debes llevar antes de acudir a la oficialía.</p>
      {catalog.isLoading ? <LoadingState /> : null}
      {catalog.isError ? <Alert variant="error" className="mt-6">{catalog.error.message}</Alert> : null}
      {catalog.data?.secciones.length === 0 ? <EmptyState title="No hay trámites publicados" description="Vuelve a consultar más tarde." /> : null}
      <div className="mt-8 space-y-8">
        {catalog.data?.secciones.map((section) => (
          <section key={section.nombre} aria-labelledby={`section-${section.nombre}`}>
            <h2 id={`section-${section.nombre}`} className="mb-4 font-heading text-lg font-semibold">{section.nombre}</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {section.tramites.map((procedure) => (
                <Card key={procedure.id}>
                  <CardTitle>{procedure.nombre}</CardTitle>
                  <CardDescription className="flex flex-wrap gap-4"><span className="font-semibold text-primary">{formatMoney(procedure.costo)}</span><span className="flex items-center gap-1"><Clock3 className="h-5 w-5" />{procedure.duracion_minutos} minutos</span></CardDescription>
                  <div className="mt-4 flex gap-3 rounded-xl bg-warm-100 p-4 text-sm text-warm-700"><FileText className="h-6 w-6 shrink-0 text-primary" /><span className="whitespace-pre-line">{procedure.documentos || 'Sin documentos adicionales registrados.'}</span></div>
                </Card>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  )
}
