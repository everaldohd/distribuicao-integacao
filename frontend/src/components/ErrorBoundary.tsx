import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { error: Error | null }

/** Evita que uma exceção de render derrube o app inteiro (tela branca). */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary capturou:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50">
          <div className="max-w-md w-full bg-white rounded-xl shadow p-6 text-center">
            <p className="text-lg font-bold text-gray-900 mb-1">Algo deu errado</p>
            <p className="text-sm text-gray-500 mb-4">
              Ocorreu um erro inesperado na tela. Você pode recarregar e tentar de novo.
            </p>
            <pre className="text-xs text-left text-red-600 bg-red-50 rounded p-2 overflow-auto max-h-32 mb-4">
              {this.state.error.message}
            </pre>
            <button
              onClick={() => { this.setState({ error: null }); window.location.reload() }}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm"
            >
              Recarregar
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
