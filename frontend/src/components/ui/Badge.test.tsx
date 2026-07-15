import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from './Badge'

describe('Badge', () => {
  it('renderiza o label', () => {
    render(<Badge label="Publicada" />)
    expect(screen.getByText('Publicada')).toBeInTheDocument()
  })

  it('aplica a cor solicitada', () => {
    render(<Badge label="Erro" color="red" />)
    expect(screen.getByText('Erro').className).toContain('bg-red-100')
  })

  it('usa cinza como cor padrão', () => {
    render(<Badge label="Rascunho" />)
    expect(screen.getByText('Rascunho').className).toContain('bg-gray-100')
  })
})
