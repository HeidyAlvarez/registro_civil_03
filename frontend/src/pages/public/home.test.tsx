import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { HomePage } from './home'

describe('HomePage', () => {
  it('presenta los servicios ciudadanos con texto claro', () => {
    render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: /servicios claros/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /agendar cita/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /asistente inteligente/i })).toBeInTheDocument()
  })
})
