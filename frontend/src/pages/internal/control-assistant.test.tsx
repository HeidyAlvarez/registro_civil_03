import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AiHubPage } from '@/pages/ia/assistant'
import { AiDashboardPage } from '@/pages/internal/ai-dashboard'
import { InternalAssistantPage } from '@/pages/internal/control-assistant'

afterEach(() => {
  vi.unstubAllGlobals()
})

function mockFetch() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
    const url = String(input)
    if (url.includes('/interno/resumen/') && options?.method !== 'POST') {
      return {
        ok: true,
        json: async () => ({
          alerts: 1,
          anomalies: 0,
          proposals: 0,
          requests: 0,
          demand: { hallazgos: ['La demanda está repartida.'] },
          seasons: { frases: ['Sin un cambio marcado.'] },
        }),
      }
    }
    return {
      ok: true,
      json: async () => ({ message: { role: 'asistente', text: 'Hoy hay 2 citas pendientes.' } }),
    }
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('asistente de control interno', () => {
  it('responde con el sistema y olvida la conversación al salir', async () => {
    const fetchMock = mockFetch()
    const view = render(<InternalAssistantPage />)

    expect(screen.getByRole('heading', { name: /asistente de control/i })).toBeInTheDocument()
    expect(screen.getByText(/se borra al salir de la pantalla/i)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /cuántas citas hay pendientes hoy/i }))

    expect(await screen.findByText('Hoy hay 2 citas pendientes.')).toBeInTheDocument()
    expect(String(fetchMock.mock.calls[0][0])).toContain('/citas/ia/api/interno/asistente/mensaje/')
    const options = fetchMock.mock.calls[0][1]
    expect(options?.method).toBe('POST')
    expect(JSON.parse(String(options?.body))).toMatchObject({
      question: '¿Cuántas citas hay pendientes hoy?',
      history: [],
    })

    view.unmount()
    render(<InternalAssistantPage />)

    expect(screen.queryByText('Hoy hay 2 citas pendientes.')).not.toBeInTheDocument()
    expect(screen.getByText(/no se guarda en el sistema/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('ofrece la entrada solo en el módulo interno', async () => {
    mockFetch()
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const dashboard = render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <AiDashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('link', { name: /asistente de control/i })).toHaveAttribute('href', '/panel/ia/asistente')
    dashboard.unmount()

    render(<MemoryRouter><AiHubPage /></MemoryRouter>)
    for (const link of screen.getAllByRole('link')) {
      expect(link.getAttribute('href') || '').not.toContain('/panel')
    }
    expect(screen.queryByRole('link', { name: /asistente de control/i })).not.toBeInTheDocument()
  })
})
