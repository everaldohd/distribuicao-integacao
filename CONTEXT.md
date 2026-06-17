# CONTEXT – Sistema de Gestão e Distribuição de Escalas

> Documento de referência rápida para retomada de sessões.
> Leia este arquivo antes de qualquer pergunta sobre o projeto.

---

## Visão Geral

Sistema web para gerenciamento, distribuição e auditoria de escalas de serviço.
A distribuição é feita por **otimização matemática** (OR-Tools CP-SAT), não por sorteio.
O histórico de justiça é mantido via **saldo de compensação** acumulado por usuário.

**Stack:** Python · FastAPI · SQLAlchemy · PostgreSQL · Celery · Redis · OR-Tools CP-SAT  
**Frontend planejado:** React + TypeScript (ainda não iniciado)  
**Organização:** Monorepo — `backend/` e `frontend/` na mesma pasta

---

## Regras de Negócio Críticas

| Regra | Detalhe |
|---|---|
| Interstício pós-Plantão 12h | Nenhuma escala no dia seguinte. Aplica-se **inclusive na borda do mês**: consulta a publicação do mês anterior. |
| Buraco na escala | Se não há usuários disponíveis suficientes, a vaga fica **em branco** (variável de folga). Nunca falha. |
| Saldo de compensação | Acumulado por usuário. Normalizado mensalmente (subtrai média geral). Novo usuário entra com a média da equipe. |
| Histórico congelado | Saldo calculado só sobre a versão **publicada**. Trocas posteriores não alteram o saldo. |
| Reprodutibilidade | CP-SAT com `random_seed = 42` fixo. Mesmos inputs → mesma escala. |
| Gestores | Papel administrador. Múltiplos gestores permitidos. Criados por outros gestores. Sem auto-cadastro de usuários. |
| Notificações | E-mail (SMTP). Disparadas em: publicação, solicitação/aceite/recusa de troca, preenchimento manual. |
| Versionamento | Escala publicada é imutável. Qualquer alteração pós-publicação gera nova versão. |

---

## Mapa de Arquivos

```
DistribuicaoIntegracao/
├── SPEC.md                        # Especificação funcional completa
├── CONTEXT.md                     # Este arquivo
├── docker-compose.yml             # PostgreSQL + Redis + API + Worker
│
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── alembic.ini
    ├── .env.example               # Variáveis de ambiente (copiar para .env)
    │
    ├── alembic/
    │   └── env.py                 # Configuração do Alembic (migrations)
    │
    └── app/
        ├── main.py                # FastAPI app: registra todos os routers
        ├── seed.py                # Cria primeiro gestor, tipos de escala e config de saldo
        │
        ├── core/
        │   ├── config.py          # Pydantic Settings (lê .env)
        │   ├── database.py        # Engine SQLAlchemy, SessionLocal, Base, get_db()
        │   └── security.py        # Hash de senha (bcrypt), criação/decodificação JWT
        │
        ├── models/
        │   ├── __init__.py        # Importa todos os modelos (necessário para Alembic)
        │   ├── user.py            # User: id, name, email, hashed_password, is_manager, profile_id
        │   ├── schedule_type.py   # ScheduleType: nome, requires_rest_day_after (Plantão 12h = True)
        │   ├── profile.py         # Profile + ProfileRule (cotas) + UserProfileException (exceções individuais)
        │   ├── eligibility.py     # Eligibility: user_id × schedule_type_id × is_eligible
        │   ├── operational_calendar.py  # OperationalCalendar (mês) + CalendarDay + DayCoverage
        │   ├── unavailability.py  # Unavailability: férias/abono/licença por período
        │   ├── preference.py      # UserPreference: datas desejadas ou a evitar
        │   ├── schedule.py        # Schedule (versão) + Assignment (atribuição ou buraco)
        │   ├── historical_balance.py  # HistoricalBalance (saldo mensal) + BalanceConfig (valores)
        │   ├── exchange.py        # Exchange: trocas abertas ou diretas entre usuários
        │   └── audit.py           # AuditLog (operacional) + SolverAudit (matemático)
        │
        ├── schemas/
        │   ├── user.py            # UserCreate, UserUpdate, UserOut, Token, LoginRequest
        │   ├── schedule_type.py   # ScheduleTypeCreate/Update/Out
        │   ├── calendar.py        # CalendarCreate/Out, DayOverrideRequest, CoverageTemplateSet
        │   ├── schedule.py        # ScheduleOut, AssignmentOut, ManualFillRequest, SimulationResult
        │   └── exchange.py        # ExchangeCreate/Out, ExchangeAccept
        │
        ├── routers/
        │   ├── deps.py            # get_current_user(), get_current_manager() (dependências de auth)
        │   ├── auth.py            # POST /auth/login → JWT
        │   ├── users.py           # CRUD usuários + /me + troca de senha
        │   ├── schedule_types.py  # CRUD tipos de escala
        │   ├── calendars.py       # Criar mês, aplicar template de cobertura, override de dia
        │   ├── schedules.py       # Simular, gerar (async), publicar, preenchimento manual
        │   ├── preferences.py     # CRUD preferências do usuário logado
        │   ├── exchanges.py       # Criar troca aberta/direta, aceitar, recusar
        │   └── balance.py         # Saldo pessoal, leaderboard, config dos valores
        │
        ├── services/
        │   ├── audit.py           # log_action(): persiste AuditLog
        │   ├── balance.py         # compute_and_persist_monthly_balances() + saldo inicial novo usuário
        │   ├── notification.py    # _send_email() + funções por evento (SMTP)
        │   ├── exchange_validator.py  # validate_exchange(): checa regras rígidas antes de executar troca
        │   └── optimizer/
        │       └── solver.py      # ScheduleSolver: CP-SAT completo (ver abaixo)
        │
        └── workers/
            ├── celery_app.py      # Instância Celery + configuração
            └── tasks.py           # run_solver_task, post_publish_tasks, notify_exchange
```

---

## Solver CP-SAT (`services/optimizer/solver.py`)

Classe `ScheduleSolver`. Dois modos: `simulate_only=True` (estimativa rápida) ou `solve()` (geração completa).

**Variáveis de decisão**
- `x[user, date, type]` — BoolVar: 1 se usuário é escalado
- `gap[date, type]` — IntVar: vagas não preenchidas (buracos)

**Restrições rígidas implementadas**
1. Indisponibilidade (férias/abono/licença)
2. Elegibilidade por tipo
3. Máximo 1 turno por usuário por dia
4. Cobertura = atribuições + gap (garante que vagas sejam contabilizadas)
5. Cotas do perfil por tipo (com exceções individuais)
6. Interstício pós-Plantão 12h (dia seguinte bloqueado)
7. **Borda do mês**: consulta `Schedule` publicado do mês anterior para bloquear dia 1 se necessário

**Função objetivo (soft constraints)**
- `WEIGHT_GAP = 100_000` — minimiza buracos (prioridade máxima)
- `WEIGHT_DESIRED = 300` — atende preferências desejadas
- `WEIGHT_AVOID = 200` — penaliza atribuição em datas a evitar
- `WEIGHT_BALANCE = 10` — prioriza usuários com maior saldo histórico
- `WEIGHT_LOAD_EQUITY = 50` — equilibra carga entre usuários

**Parâmetros**
- `random_seed = 42` (fixo, via `settings.SOLVER_RANDOM_SEED`)
- `max_time_in_seconds = 60` (configurável)
- `num_workers = 4`

**Saída**
- Persiste `Assignment` para cada atribuição e cada buraco
- Persiste `SolverAudit` com todas as métricas da execução
- Atualiza `Schedule.status` para `GENERATED`

---

## Endpoints da API

Prefixo: `/api/v1`

| Método | Caminho | Acesso | Descrição |
|---|---|---|---|
| POST | `/auth/login` | Público | Retorna JWT |
| GET | `/users/me` | Usuário | Perfil do usuário logado |
| POST | `/users/` | Gestor | Criar usuário |
| GET/PUT | `/users/{id}` | Gestor | Ler/atualizar usuário |
| GET/POST/PUT | `/schedule-types/` | Misto | CRUD tipos de escala |
| POST | `/calendars/` | Gestor | Criar calendário do mês |
| POST | `/calendars/{id}/coverage-template` | Gestor | Aplicar modelo de cobertura |
| PATCH | `/calendars/{id}/days/{day_id}` | Gestor | Override de categoria/cobertura de um dia |
| POST | `/schedules/simulate/{calendar_id}` | Gestor | Simulação síncrona |
| POST | `/schedules/generate/{calendar_id}` | Gestor | Gera escala (async, via Celery) → 202 |
| POST | `/schedules/{id}/publish` | Gestor | Publica + dispara saldo + e-mails |
| POST | `/schedules/{id}/manual-fill` | Gestor | Preenche buraco manualmente |
| GET/POST/DELETE | `/preferences/` | Usuário | CRUD preferências do mês |
| GET | `/exchanges/open` | Usuário | Lista trocas abertas disponíveis |
| POST | `/exchanges/` | Usuário | Cria troca aberta ou direta |
| POST | `/exchanges/{id}/accept` | Usuário | Aceita troca (valida regras antes) |
| POST | `/exchanges/{id}/reject` | Usuário | Recusa troca |
| GET | `/balance/me` | Usuário | Histórico de saldo pessoal |
| GET | `/balance/leaderboard` | Usuário | Ranking de todos os usuários |
| GET/PUT | `/balance/config` | Misto | Lê/atualiza valores do saldo |

---

## Fluxo de Geração (resumo técnico)

```
Gestor → POST /calendars/           → cria OperationalCalendar + CalendarDays (classificação automática)
Gestor → POST /coverage-template    → preenche DayCoverage padrão por categoria
Gestor → PATCH /days/{id}           → overrides manuais com auditoria
Gestor → cadastra Unavailabilities
Usuário → POST /preferences/        → datas desejadas/a evitar
Gestor → POST /simulate/{cal_id}    → estimativa rápida (sem solver)
Gestor → POST /generate/{cal_id}    → cria Schedule(DRAFT) + enfileira run_solver_task no Celery
Worker → ScheduleSolver.solve()     → CP-SAT → persiste Assignments + SolverAudit → Schedule(GENERATED)
Gestor → POST /manual-fill          → preenche buracos restantes
Gestor → POST /publish              → Schedule(PUBLISHED) + enfileira post_publish_tasks
Worker → compute_and_persist_monthly_balances() + notify_schedule_published() por e-mail
```

---

## Como Subir o Projeto

```bash
# 1. Configurar variáveis
cp backend/.env.example backend/.env
# editar backend/.env com SMTP e credenciais

# 2. Subir tudo
docker compose up --build

# Serviços:
# API:      http://localhost:8000
# Docs:     http://localhost:8000/docs
# Postgres: localhost:5432
# Redis:    localhost:6379
```

O `seed.py` roda automaticamente na inicialização e cria:
- Primeiro gestor (`FIRST_MANAGER_EMAIL` / `FIRST_MANAGER_PASSWORD`)
- 6 tipos de escala padrão (Plantão 12h com `requires_rest_day_after=True`)
- Configuração de saldo padrão

---

## Próximos Passos

- [ ] Frontend React + TypeScript (área do gestor + área do usuário)
- [ ] Migrations Alembic (`alembic revision --autogenerate`)
- [ ] Testes automatizados (pytest)
- [ ] Relatórios da área do gestor
- [ ] Módulo de datas especiais (Natal, Ano Novo, Carnaval) — previsto na spec
