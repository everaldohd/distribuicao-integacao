import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { TestBanner } from './TestBanner'

describe('TestBanner', () => {
  it('avisa que o sistema está em fase de testes', () => {
    render(<TestBanner />, { wrapper: MemoryRouter })
    expect(screen.getByText(/Versão de teste/i)).toBeInTheDocument()
    expect(screen.getByText(/fase de avaliação/i)).toBeInTheDocument()
  })

  it('tem link para a página "Como funciona"', () => {
    render(<TestBanner />, { wrapper: MemoryRouter })
    const link = screen.getByRole('link', { name: /como funciona/i })
    expect(link).toHaveAttribute('href', '/como-funciona')
  })
})
