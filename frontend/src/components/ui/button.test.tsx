import { render, screen } from '@testing-library/react'
import { Download } from 'lucide-react'
import { describe, expect, it } from 'vitest'
import { Button } from './button'

describe('Button', () => {
  it('renderiza enlaces con icono mediante asChild', () => {
    render(
      <Button asChild>
        <a href="/comprobante.pdf"><Download aria-hidden="true" />Descargar comprobante</a>
      </Button>,
    )

    expect(screen.getByRole('link', { name: /descargar comprobante/i })).toHaveAttribute('href', '/comprobante.pdf')
  })
})
