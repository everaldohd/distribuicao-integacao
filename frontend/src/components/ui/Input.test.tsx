import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Input } from './Input'

describe('Input', () => {
  it('associa o label ao input via htmlFor/id', () => {
    render(<Input id="email" label="E-mail" />)
    expect(screen.getByLabelText('E-mail')).toBeInTheDocument()
  })

  it('exibe a mensagem de erro quando fornecida', () => {
    render(<Input id="pwd" label="Senha" error="Campo obrigatório" />)
    expect(screen.getByText('Campo obrigatório')).toBeInTheDocument()
  })

  it('aplica borda de erro quando há erro', () => {
    render(<Input id="pwd" label="Senha" error="inválido" />)
    expect(screen.getByLabelText('Senha').className).toContain('border-red-400')
  })

  it('repassa atributos nativos (type, placeholder)', () => {
    render(<Input id="q" label="Busca" type="search" placeholder="Buscar..." />)
    const input = screen.getByLabelText('Busca')
    expect(input).toHaveAttribute('type', 'search')
    expect(input).toHaveAttribute('placeholder', 'Buscar...')
  })
})
