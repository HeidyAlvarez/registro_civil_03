import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { InternalAiGate } from '@/components/layout/internal-ai-gate'

const session = vi.hoisted(() => ({
  current: {
    isLoading: false,
    data: {
      authenticated: true,
      permissions: { staff: true, official: false, administrator: false, internal_ai: false },
    },
  },
}))

vi.mock('@/hooks/use-session', () => ({
  useSession: () => session.current,
}))

function renderGate() {
  return render(
    <MemoryRouter initialEntries={['/panel/ia/asistente']}>
      <Routes>
        <Route path="/panel" element={<h1>Panel general</h1>} />
        <Route path="/panel/ia" element={<InternalAiGate />}>
          <Route path="asistente" element={<h1>Asistente de control</h1>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('acceso al asistente interno', () => {
  it('deja fuera a quien no tiene el permiso de inteligencia interna', () => {
    session.current = {
      isLoading: false,
      data: {
        authenticated: true,
        permissions: { staff: true, official: false, administrator: false, internal_ai: false },
      },
    }
    renderGate()
    expect(screen.getByRole('heading', { name: /panel general/i })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /asistente de control/i })).not.toBeInTheDocument()
  })

  it('muestra el asistente al personal con acceso interno', () => {
    session.current = {
      isLoading: false,
      data: {
        authenticated: true,
        permissions: { staff: true, official: true, administrator: false, internal_ai: true },
      },
    }
    renderGate()
    expect(screen.getByRole('heading', { name: /asistente de control/i })).toBeInTheDocument()
  })
})
