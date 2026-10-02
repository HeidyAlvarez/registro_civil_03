import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { HomePage } from './home'

describe('HomePage', () => {
  it('presenta los servicios ciudadanos con texto claro', () => {
    render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: /agenda tu cita sin filas/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /qué necesitas hacer/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /ingresar a agendar cita/i })).toHaveAttribute('href', '/agendar-cita')
    expect(screen.getByRole('link', { name: /ingresar a módulo de ia/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pausar carrusel/i })).toBeInTheDocument()
  })
})
