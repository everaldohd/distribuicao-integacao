# Sistema de Gestão e Distribuição de Escalas

> **Status:** protótipo funcional — **não está em produção**; os dados do banco são de teste e
> podem ser descartados a qualquer momento. A especificação de negócio está em **[SPEC.md](SPEC.md)**
> (serve de base para manutenção ou reimplementação em outro stack).

Aplicação web para **planejar, distribuir e auditar escalas de serviço** de peritos.
A distribuição **não é por sorteio**: um otimizador matemático (Google OR-Tools / CP-SAT)
encontra a alocação mais justa respeitando regras rígidas (elegibilidade, cotas, interstício,
férias) e maximizando preferências e equilíbrio de carga.

---

## Sumário

- [Visão geral](#visão-geral)
- [Arquitetura e stack](#arquitetura-e-stack)
- [Como rodar](#como-rodar)
- [Conceitos do domínio](#conceitos-do-domínio)
- [Perfis e cotas (limite por grupo)](#perfis-e-cotas-limite-por-grupo)
- [Preferências por modalidade](#preferências-por-modalidade)
- [Saldo de compensação (justiça)](#saldo-de-compensação-justiça)
- [O otimizador (CP-SAT)](#o-otimizador-cp-sat)
- [Ciclo de vida de uma escala](#ciclo-de-vida-de-uma-escala)
- [Integração NEO (SSO) — preparada](#integração-neo-sso--preparada)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Referência da API](#referência-da-api)
- [Scripts úteis](#scripts-úteis)

---

## Visão geral

Há dois perfis de acesso:

- **Gestor (admin)** — cadastra usuários, perfis/cotas, tipos de escala, monta o calendário
  do mês, gera/edita/publica escalas e acompanha o ranking de saldo.
- **Perito (usuário)** — registra preferências de datas por modalidade, vê sua escala
  publicada e acompanha seu saldo.

Credenciais de desenvolvimento (seed): `admin` / `admin` (gestor) e `usuario` / `usuario` (perito).

---

## Arquitetura e stack

```
┌────────────┐     HTTP/JSON      ┌──────────────┐
│  Frontend  │ ─────────────────▶ │   Backend    │
│ React+Vite │   /api/v1 (proxy)  │   FastAPI    │
└────────────┘                    └──────┬───────┘
                                         │
                        ┌────────────────┼─────────────────┐
                        ▼                ▼                  ▼
                  ┌───────────┐    ┌───────────┐     ┌────────────┐
                  │PostgreSQL │    │   Redis    │     │  Worker    │
                  │  (dados)  │    │ (fila)     │ ──▶ │  Celery    │
                  └───────────┘    └───────────┘     │ (CP-SAT)   │
                                                     └────────────┘
```

- **Backend:** Python · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · JWT (python-jose) · OR-Tools CP-SAT
- **Async:** Celery + Redis (a geração da escala roda em background)
- **Banco:** PostgreSQL
- **Frontend:** React 18 · TypeScript · Vite · TanStack Query · React Router · Tailwind CSS
- **Orquestração:** Docker Compose (serviços: `db`, `redis`, `backend`, `worker`, `frontend`)

---

## Como rodar

```bash
# 1. Variáveis de ambiente do backend
cp backend/.env.example backend/.env   # ajuste SECRET_KEY, credenciais, SMTP...

# 2. Subir tudo
docker compose up --build
```

| Serviço   | URL                              |
|-----------|----------------------------------|
| Frontend  | http://localhost:5173            |
| API       | http://localhost:8000            |
| API Docs  | http://localhost:8000/docs       |

Na primeira subida, `seed.py` cria automaticamente: gestor inicial, tipos de escala (com grupo/peso),
os perfis do sistema e a configuração de saldo. Para popular 100 peritos de teste:

```bash
docker compose exec backend python -m app.seed_test
```

> **WSL2/Docker:** o hot-reload do Vite usa polling (`vite.config.ts`). Após mudar arquivos do
> frontend que não recarregarem sozinhos, rode `docker compose restart frontend`.

---

## Conceitos do domínio

| Conceito | O que é |
|---|---|
| **Tipo de escala** | Modalidade de turno: Plantão 12h, Reserva (Manhã/Tarde/12h), Pátio (Manhã/Tarde). |
| **Grupo** | Agrupa tipos para fins de cota: **Plantão**, **Reserva**, **Pátio**. |
| **Peso do grupo** | Quanto um tipo "consome" da cota do grupo. Reserva 12h = **2**; os demais = 1. |
| **Calendário** | A *demanda* do mês: quantas vagas de cada tipo existem em cada dia. |
| **Cobertura (DayCoverage)** | Quantidade de vagas de um tipo num dia específico. |
| **Escala (Schedule)** | O *resultado*: quem cobre cada vaga. Versionada e auditada. |
| **Atribuição (Assignment)** | Um perito num tipo numa data — ou um "buraco" (vaga sem perito). |
| **Perfil** | Define a cota máxima por grupo de um perito (ver abaixo). |
| **Preferência** | Pedido do perito: "quero / não quero" uma modalidade numa data. |
| **Saldo** | Pontuação de justiça acumulada por perito (ver abaixo). |

---

## Perfis e cotas (limite por grupo)

Cada perito tem um **perfil** que define o **máximo por grupo** que ele pode receber no mês.
Os limites são **ponderados** (Reserva 12h conta 2). Perfis do sistema:

| Perfil | Plantão | Reserva | Pátio |
|---|---|---|---|
| Lotado na Interna | 1 | 2 | 0 |
| Lotado na Interna com Restrição | 0 | 0 | 1 |
| Lotado na Externa | 0 | 0 | 0 |
| Chefe | 1 | 2 | 0 |
| Direção | 0 | 0 | 0 |
| **Fora do Integração** (padrão p/ quem não tem perfil) | 0 | 0 | 0 |
| **Personalizado** | definido por perito |

- O gestor edita as cotas dos perfis em **Perfis & Regras**, e pode **criar novos perfis**.
- Ao editar a cota de um perito específico, ele migra automaticamente para **Personalizado**
  (os limites passam a ser individuais, guardados em `user_group_limits`).
- O otimizador garante: para cada perito e grupo, `Σ (peso × turnos) ≤ cota do grupo`.

---

## Preferências por modalidade

O perito registra preferências **por modalidade** (não só por dia), na tela **Minha Agenda**:

- Botões coloridos = modalidades liberadas pelo seu perfil (grupos com cota > 0).
- Modos separados: **Desejo trabalhar** e **Prefiro não**.
- Só é possível marcar dias em que o calendário oferece aquela modalidade.
- **Limite de dias** = `cota do grupo × fator global` (configurável pelo gestor em Perfis & Regras),
  contado **separadamente** para "desejo" e "evitar".

Após a publicação, a agenda do mês vira **somente leitura**: os dias escalados aparecem em dourado
e as bolinhas de preferência continuam visíveis (apenas como registro).

---

## Saldo de compensação (justiça)

O saldo mede quão "prejudicado" um perito foi, para priorizá-lo no futuro. Convenção (configurável):

| Evento no mês | Efeito no saldo |
|---|---|
| Mês sem nenhuma escala | **−10** |
| Recebeu uma data desejada | **−5** |
| Forçado numa data que pediu para evitar | **+10** |
| Turno comum | 0 |

- **Saldo alto (positivo)** = foi prejudicado → o otimizador o escala **menos**.
- **Saldo baixo (negativo)** = foi favorecido → é escalado **mais**.
- Ao fim do mês o saldo é **normalizado** (subtrai a média) para puxar todos ao equilíbrio.
- Quem **não pode ser escalado** (sem nenhuma elegibilidade) fica com saldo **imutável**.
- O saldo é calculado apenas sobre a versão **publicada**.

---

## O otimizador (CP-SAT)

`backend/app/services/optimizer/solver.py` — classe `ScheduleSolver`.

**Variáveis:** `x[perito, dia, tipo]` (1 = escalado) e `gap[dia, tipo]` (vagas vazias).

**Restrições rígidas:**
1. Indisponibilidade (férias/abono/licença)
2. Elegibilidade por tipo
3. No máximo 1 turno por perito por dia
4. Cobertura = atribuições + buracos
5. **Cota por grupo** ponderada (Reserva 12h = 2)
6. Interstício pós-Plantão 12h (bloqueia o dia seguinte, inclusive na virada do mês)

**Objetivo (pesos):** minimizar buracos (`100_000`), atender desejos (`+300`),
evitar datas indesejadas (`−200`), **respeitar saldo** (positivo → escalar menos),
equilibrar carga (`50`). `random_seed = 42` garante reprodutibilidade.

A geração roda **assíncrona** (Celery): o endpoint cria um `Schedule` em rascunho e enfileira a tarefa;
o frontend faz polling até o status virar `generated`.

---

## Ciclo de vida de uma escala

```
Calendário (Rascunho → Aberto)            Escala
        │ cria mês + cobertura              │
        │ preferências dos peritos          │
        ▼                                    ▼
   [Aberto] ── gerar ──▶ Schedule(draft) ─solver─▶ Schedule(generated)
                                                        │ editar (livre)
                                                        ▼
   [Finalizado] ◀── publicar ─────────── Schedule(published)
        (calendário trava)                    │ editar só com justificativa (auditado)
                                              ▼
                                        saldo + e-mails (async)
```

- **Em preparação** (rascunho/gerada): o gestor pode **editar livremente** ou **apagar** a escala.
- **Publicada**: o calendário do mês vira **Finalizado**; alterações exigem **justificativa**
  (registrada na auditoria). Nova geração cria uma nova versão.

---

## Integração NEO (SSO) — preparada

Há um ponto de entrada de **login delegado** pronto, porém **desativado por padrão**
(`NEO_SSO_SECRET` vazio). Quando habilitado, o NEO abre a aplicação em `/sso?token=<JWT>`
(JWT HS256 assinado com o segredo compartilhado, contendo `matricula`, `email`, `name`, `exp`);
o endpoint `POST /auth/sso` valida, identifica/cria o perito pela matrícula e emite a sessão.
Detalhes em `backend/app/routers/auth.py`.

---

## Estrutura de pastas

```
DistribuicaoIntegracao/
├── docker-compose.yml
├── README.md            ← este arquivo
├── CONTEXT.md           ← referência rápida p/ retomar sessões
├── SPEC.md              ← especificação funcional original
├── backend/
│   └── app/
│       ├── main.py            # registra os routers
│       ├── seed.py            # seed inicial (gestor, tipos, perfis, config)
│       ├── seed_test.py       # 100 peritos de teste
│       ├── alembic/           # migrations versionadas (schema do banco)
│       ├── core/              # config, database, security (JWT/bcrypt)
│       ├── models/            # tabelas SQLAlchemy
│       ├── schemas/           # contratos Pydantic
│       ├── routers/           # endpoints HTTP
│       ├── services/          # regras de negócio (balance, optimizer, notification...)
│       └── workers/           # Celery (tasks assíncronas)
└── frontend/
    └── src/
        ├── App.tsx            # rotas
        ├── lib/               # api (axios), auth, types
        ├── components/        # layout + UI base
        └── pages/
            ├── gestor/        # telas do administrador
            └── usuario/       # telas do perito
```

---

## Referência da API

Prefixo: `/api/v1`. Documentação interativa: `/docs`.

| Método | Caminho | Acesso | Descrição |
|---|---|---|---|
| POST | `/auth/login` | Público | Login local → JWT |
| POST | `/auth/sso` | Público | Login delegado NEO (se habilitado) |
| GET | `/users/me` | Logado | Dados do usuário logado |
| GET/POST | `/users/` | Gestor | Listar / criar usuários |
| PUT | `/users/{id}` | Gestor | Atualizar (perfil, matrícula, etc.) |
| GET/PUT | `/users/{id}/eligibilities` | Gestor | Tipos que o perito pode fazer |
| GET/PUT | `/users/{id}/limits` | Gestor | Cota por grupo do perito (→ Personalizado) |
| GET/POST/DELETE | `/users/{id}/unavailabilities` | Gestor | Férias/abono/licença |
| GET/POST/PUT/DELETE | `/profiles/` | Gestor | Perfis e cotas por grupo |
| GET | `/profiles/groups` | Logado | Grupos e tipos/pesos |
| GET/POST/PUT | `/schedule-types/` | Misto | Tipos de escala |
| GET/POST | `/calendars/` | Gestor | Calendário do mês |
| POST | `/calendars/{id}/apply-default-template` | Gestor | Cobertura padrão (dia útil × fim de semana) |
| PATCH | `/calendars/{id}/days/{day_id}` | Gestor | Override de um dia |
| POST | `/schedules/generate/{calendar_id}` | Gestor | Gera escala (async) |
| GET | `/schedules/` · `/schedules/{id}` | Logado | Lista / detalhe (com atribuições) |
| PATCH | `/schedules/{id}/assignments/{aid}` | Gestor | Reatribuir vaga (justificativa se publicada) |
| POST | `/schedules/{id}/publish` | Gestor | Publica (finaliza calendário, dispara saldo/e-mails) |
| DELETE | `/schedules/{id}` | Gestor | Apaga escala não publicada |
| GET | `/preferences/options` | Logado | Modalidades, limites e disponibilidade do mês |
| GET/POST/DELETE | `/preferences/` | Logado | Preferências por modalidade |
| GET/PUT | `/preferences/config` | Misto | Fator do limite de preferências |
| GET | `/balance/me` · `/balance/leaderboard` | Logado | Saldo pessoal / ranking |
| GET/PUT | `/balance/config` | Misto | Valores do saldo |
| GET | `/audit/` | Gestor | Trilha de auditoria (filtros por ação/entidade) |
| GET | `/diagnostics/` | Gestor | Saúde do sistema (banco, Redis, Celery, seed) |
| GET | `/health` | Público | Liveness simples |

### Observabilidade
- **Logs**: formato `timestamp | nível | módulo | mensagem` (stdout). Há *middleware* que loga
  toda requisição (método, rota, status, tempo) e logs nos pontos críticos (login, geração,
  publicação, exclusão de escala).
- **Auditoria**: toda ação de admin (usuários, perfis, elegibilidades, cotas, férias, escalas) e
  do perito (preferências) é gravada em `audit_logs` com autor, valores anterior/novo e descrição;
  consultável em **Auditoria** (gestor). A geração da escala também grava `SolverAudit` (métricas da otimização).
- **Testes**: `pytest` (backend) cobrindo auth, usuários, tipos, **solver (cota/interstício)**, **saldo**
  e **limite de preferências**; `vitest` (frontend). Rode: `docker compose exec backend python -m pytest -q`
  e `docker compose exec frontend npm test`.
- **Migrations**: schema gerenciado por **Alembic** (`alembic upgrade head` roda no startup do backend).
- **Lint**: `ruff` (backend) e `eslint` (frontend).
- **CI**: GitHub Actions (`.github/workflows/ci.yml`) roda lint + testes + build a cada push/PR.

---

## Scripts úteis

```bash
# Logs de um serviço
docker compose logs backend --tail 50

# Seed inicial / dados de teste
docker compose exec backend python -m app.seed
docker compose exec backend python -m app.seed_test

# Acesso ao banco
docker compose exec db psql -U escalas -d escalas
```
