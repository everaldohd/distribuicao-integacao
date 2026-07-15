/** Extrai uma mensagem amigável de um erro do axios/FastAPI.
 *
 * O FastAPI devolve `detail` como string (HTTPException) ou como lista de
 * objetos (erro de validação 422, ex.: política de senha). Aqui normalizamos
 * os dois formatos para exibir ao usuário.
 */
export function getApiErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string }
    if (typeof first?.msg === 'string') {
      // Pydantic prefixa "Value error, " nas mensagens de validador — removemos
      return first.msg.replace(/^Value error,\s*/i, '')
    }
  }
  return fallback
}

/** Texto único dos requisitos de senha — exibir perto de qualquer campo de senha nova. */
export const PASSWORD_REQUIREMENTS =
  'Mínimo de 8 caracteres, incluindo ao menos 1 caractere especial (ex.: !#-.,*).'
