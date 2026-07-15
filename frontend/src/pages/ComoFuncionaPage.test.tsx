import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ComoFuncionaPage } from './ComoFuncionaPage'

function renderPage() {
  return render(<ComoFuncionaPage />, { wrapper: MemoryRouter })
}

describe('ComoFuncionaPage', () => {
  it('explica o sistema com título principal', () => {
    renderPage()
    expect(
      screen.getByRole('heading', { name: /como funciona a distribuição de escalas/i }),
    ).toBeInTheDocument()
  })

  it('deixa claro que o sistema está em fase de testes', () => {
    renderPage()
    expect(screen.getAllByText(/versão de teste/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/fase de testes/i).length).toBeGreaterThan(0)
  })

  it('apresenta os 4 passos da escala', () => {
    renderPage()
    expect(screen.getByText(/o gestor monta o calendário/i)).toBeInTheDocument()
    expect(screen.getByText(/marca suas preferências/i)).toBeInTheDocument()
    expect(screen.getByText(/o sistema distribui as vagas/i)).toBeInTheDocument()
    expect(screen.getByText(/a escala é publicada/i)).toBeInTheDocument()
  })

  it('explica o saldo com exemplos concretos', () => {
    renderPage()
    expect(screen.getByText('Ana')).toBeInTheDocument()
    expect(screen.getByText('Bruno')).toBeInTheDocument()
    expect(screen.getByText('+10 pontos')).toBeInTheDocument()
  })

  it('sem login, o botão principal leva para a tela de entrada', () => {
    renderPage()
    const cta = screen.getByRole('link', { name: /entrar no sistema/i })
    expect(cta).toHaveAttribute('href', '/login')
  })
})
