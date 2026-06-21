# Segurança — postura e manutenção

> Resumo das medidas de segurança implementadas e do que ainda falta para produção.
> Mantenha este documento atualizado a cada mudança que afete segurança.
> Status do projeto: **protótipo** (não está em produção).

## Medidas implementadas

| Área | Medida | Onde |
|---|---|---|
| Senhas | Hash **bcrypt** (nunca em texto puro) | `core/security.py` |
| Senhas | Mín. **8 caracteres** + **complexidade** (minúsc./maiúsc./dígito/símbolo) e máx. **72 bytes** (limite do bcrypt, checado em bytes) | `schemas/user.py` (`validate_password_strength`) |
| Sessão | JWT em **cookie HttpOnly** (inacessível a JS → mitiga roubo por XSS); header Bearer ainda aceito p/ clientes de API | `core/security.py` (`set_auth_cookies`), `routers/deps.py`, `routers/auth.py` |
| Sessão | **CSRF double-submit**: cookie `csrf_token` legível refletido no header `X-CSRF-Token`, conferido nos métodos que alteram estado | `main.py` (`csrf_protect`), `frontend/src/lib/api.ts` |
| Sessão | `POST /auth/logout` limpa os cookies de sessão | `routers/auth.py` |
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

1. ~~**SECRET_KEY forte e fixa**~~ — **FEITO**: chave forte gerada no `.env` (dev) e o app agora avisa
   de forma barulhenta se subir sem chave configurada (em vez de gerar uma efêmera silenciosa que
   derruba sessões a cada restart / diverge entre réplicas — ver `_ensure_secret_key` em `config.py`).
   Em produção, **gere uma nova** e injete por secret manager.
2. **Trocar credenciais padrão** — o `docker-compose.yml` agora lê `POSTGRES_USER/PASSWORD/DB` do
   ambiente (default só p/ dev). Em produção, defina valores fortes e troque o gestor seed `admin/admin`
   (`FIRST_MANAGER_EMAIL/PASSWORD`).
3. **HTTPS obrigatório** — terminar TLS no proxy/ingress; não trafegar JWT em HTTP. Ao subir atrás de
   HTTPS, defina **`COOKIE_SECURE=true`** (cookies só viajam em conexão segura).
5. **Rate limit distribuído** — o limiter atual é em memória (ok p/ 1 instância). Com várias réplicas,
   configurar backend Redis no slowapi.
6. **SSO NEO** — ao habilitar, usar segredo forte; o token já exige `exp`. Auto-provisionamento liga-se
   por `NEO_SSO_AUTO_PROVISION`.

> **Resolvido nesta rodada:** política de senha (complexidade + limite real de 72 bytes), token movido
> de `localStorage` para **cookie HttpOnly** com proteção **CSRF** (double-submit) e endpoint de logout,
> e credenciais de banco parametrizadas por ambiente. Falta, para produção: `COOKIE_SECURE=true` sob
> HTTPS, SECRET_KEY forte (adiado), e rate limit distribuído.

## Notas

- A edição de escala **publicada** exige justificativa e é auditada, mas **não recalcula o saldo**
  (o histórico é congelado na publicação — comportamento intencional).
- O endpoint `/diagnostics` e os erros de validação podem expor detalhes internos; ambos são restritos
  ao gestor. Em produção, evite vazar mensagens de exceção a usuários finais.
