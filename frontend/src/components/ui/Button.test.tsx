import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Button } from './Button'

describe('Button', () => {
  it('renderiza o texto do botão', () => {
    render(<Button>Salvar</Button>)
    expect(screen.getByRole('button', { name: 'Salvar' })).toBeInTheDocument()
  })

  it('fica desabilitado quando loading', () => {
    render(<Button loading>Enviando</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})
