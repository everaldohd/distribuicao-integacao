# Segurança — postura e manutenção

> Resumo das medidas de segurança implementadas e do que ainda falta para produção.
> Mantenha este documento atualizado a cada mudança que afete segurança.
> Status do projeto: **protótipo** (não está em produção).

## Medidas implementadas

| Área | Medida | Onde |
|---|---|---|
| Senhas | Hash **bcrypt** (nunca em texto puro) | `core/security.py` |
| Senhas | Mínimo de **8 caracteres** (criação e troca) | `schemas/user.py` (`MIN_PASSWORD_LENGTH`) |
| Login | **Rate limit** 10/min por IP (anti força-bruta) | `core/ratelimit.py`, `routers/auth.py`, `main.py` |
| Login | Mensagem genérica (não revela se o usuário existe) + log de falha | `routers/auth.py` |
| Autenticação | **JWT** (HS256), expira em 8h | `core/security.py`, `routers/deps.py` |
| Autorização | `get_current_user` (autenticado) e `get_current_manager` (gestor) por dependency | `routers/deps.py` |
| Autorização | Escala **não publicada** só é visível ao gestor | `routers/schedules.py` (`get_schedule`) |
| Autorização | Preferências/saldo/trocas checam **dono/destinatário** (sem IDOR) | `routers/preferences.py`, `exchanges.py` |
| SQL Injection | Tudo via SQLAlchemy parametrizado (sem SQL cru com input) | — |
| Concorrência | **Lock** das vagas na aprovação de troca (evita corrida) | `routers/exchanges.py` (`with_for_update`) |
| Robustez | E-mail/matrícula duplicados → **400** (não 500) | `routers/users.py` |
| HTTP | Cabeçalhos de segurança (nosniff, X-Frame-Options DENY, Referrer-Policy) | `main.py` (`security_headers`) |
| CORS | Lista de origens **específica** (não `*`) | `main.py` / `config.py` |
| Auditoria | Toda ação registrada (quem, o quê, antes/depois) | `services/audit.py` + tela Auditoria |
| Segredos | `.env` **fora do Git** (`.gitignore`) | `.gitignore` |
| Dependências | Scan no CI (`pip-audit` / `npm audit`, informativo) | `.github/workflows/ci.yml` |

## Pendências para PRODUÇÃO (antes de expor publicamente)

1. **SECRET_KEY forte e fixa** — hoje o `.env` usa um placeholder. Gerar com
   `python -c "import secrets; print(secrets.token_hex(32))"` e injetar por variável de ambiente/secret
   manager. Sem isso, é possível **forjar tokens JWT**. *(adiado a pedido — fazer antes de produção)*
2. **Trocar credenciais padrão** — banco `escalas/escalas` (docker-compose) e o gestor seed `admin/admin`.
3. **HTTPS obrigatório** — terminar TLS no proxy/ingress; não trafegar JWT em HTTP.
4. **Token no front** — hoje em `localStorage` (exposto a XSS) e sem revogação. Avaliar cookie `HttpOnly`
   + CSRF, e/ou refresh tokens com expiração curta.
5. **Rate limit distribuído** — o limiter atual é em memória (ok p/ 1 instância). Com várias réplicas,
   configurar backend Redis no slowapi.
6. **SSO NEO** — ao habilitar, usar segredo forte; o token já exige `exp`. Auto-provisionamento liga-se
   por `NEO_SSO_AUTO_PROVISION`.
7. **Política de senha** — considerar exigir complexidade (maiúsc./número/símbolo) além do tamanho.
8. **bcrypt** trunca senha > 72 bytes silenciosamente (limite da lib) — comunicar/limitar no formulário.

## Notas

- A edição de escala **publicada** exige justificativa e é auditada, mas **não recalcula o saldo**
  (o histórico é congelado na publicação — comportamento intencional).
- O endpoint `/diagnostics` e os erros de validação podem expor detalhes internos; ambos são restritos
  ao gestor. Em produção, evite vazar mensagens de exceção a usuários finais.
