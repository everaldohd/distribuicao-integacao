# Guia de Migração → Java 25 · Spring Boot · Gradle · Angular 21

> Plano para reimplementar o sistema (hoje Python/FastAPI + React) no stack do trabalho,
> **usando este repositório como especificação**. Regras de negócio: ver **[SPEC.md](SPEC.md)**.
> Contrato exato da API: o **OpenAPI** do protótipo (`http://localhost:8000/openapi.json` ou `/docs`).

## Estratégia

- **Reescrita limpa** (não conversão em paralelo): este app é a referência viva (funciona, tem testes e docs).
- **Reaproveitar o PostgreSQL**: o schema do banco é independente da linguagem. JPA/Hibernate fala com o
  mesmo banco. O schema atual pode ser recriado por migrations Flyway/Liquibase (gerar a partir das tabelas existentes).
- **Backend primeiro** (paridade de contrato), **depois o Angular**.
- **Validar com os 23 testes atuais** como checklist de paridade (portar para JUnit).

---

## Stack alvo e equivalências

| Hoje (Python) | Alvo (Java/Angular) |
|---|---|
| FastAPI | **Spring Boot 3.5+/4.x** (Web/REST), compatível com **Java 25** |
| Pydantic (schemas) | DTOs + **Bean Validation** (`jakarta.validation`) |
| SQLAlchemy (models) | **JPA/Hibernate** (entidades) + Spring Data repositories |
| Alembic (migrations) | **Flyway** (recomendado) ou Liquibase |
| python-jose + passlib/bcrypt (JWT) | **Spring Security** + `jjwt` (ou Nimbus) + BCryptPasswordEncoder |
| Celery + Redis (async) | **Spring `@Async`** + Quartz/Spring Batch; fila opcional (Redis/RabbitMQ) |
| OR-Tools (Python) | **OR-Tools (Java)** — `com.google.ortools:ortools-java` (Maven Central) |
| Uvicorn | Tomcat embutido (Spring Boot) |
| pip/requirements | **Gradle** (Kotlin DSL) |
| React + Vite + TanStack Query + Tailwind | **Angular 21** (standalone + signals) + HttpClient + Tailwind |
| pytest / vitest | **JUnit 5** / **Jasmine+Karma** ou Vitest |
| ruff / eslint | **Spotless/Checkstyle** / ESLint (Angular já traz) |

Notas de versão:
- **Java 25** (LTS). No Gradle, `toolchain { languageVersion = JavaLanguageVersion.of(25) }`.
- **OR-Tools Java**: carregar nativos com `Loader.loadNativeLibraries()` antes de usar o `CpModel`.
- **Angular 21**: componentes **standalone** por padrão, **signals**, novo control-flow `@if/@for`, `inject()`.

---

## Backend — estrutura de pacotes sugerida (Spring Boot)

```
com.instituto.escalas
├── config/        # Security (JWT), CORS, OpenAPI, Async
├── domain/        # entidades JPA
├── repository/    # interfaces Spring Data JPA
├── dto/           # requests/responses (equivalente aos schemas Pydantic)
├── web/           # @RestController (equivalente aos routers)
├── service/       # regras de negócio (balance, exchange, etc.)
├── solver/        # ScheduleSolver com OR-Tools Java
└── audit/         # AuditService (log_action) + entidades de auditoria
```

### Modelos → Entidades JPA (mapa)

| SQLAlchemy (app/models) | Entidade JPA | Observações |
|---|---|---|
| `User` | `User` | + `matricula`, `profileId`, `isManager`, `isActive` |
| `ScheduleType` | `ScheduleType` | + `groupName`, `groupWeight` |
| `Profile` / `ProfileGroupLimit` / `UserGroupLimit` | idem | cota por grupo (não por tipo) |
| `Eligibility` | `Eligibility` | `@UniqueConstraint(user, type)` |
| `OperationalCalendar` / `CalendarDay` / `DayCoverage` | idem | enums `CalendarStatus`, `DayCategory` |
| `UserPreference` | `UserPreference` | tem `scheduleTypeId` (modalidade) + `type` (desired/avoid) |
| `Schedule` / `Assignment` | idem | `explanation_flags` → `jsonb` (Hibernate `@JdbcTypeCode(SqlTypes.JSON)`) |
| `HistoricalBalance` / `BalanceConfig` | idem | BalanceConfig tem pontos + `preferenceFactor` + `exchangeMinLeadDays` + 5 pesos |
| `Exchange` | `Exchange` | `status`/`type` como `String`/enum; `approvedById` |
| `AuditLog` / `SolverAudit` | idem | `previous/new_value` → `jsonb` |

> Dica: campos `jsonb` (explanation_flags, audit values, simulation_data) → usar tipo JSON do Hibernate 6.

### Endpoints → Controllers (visão geral; contrato completo no OpenAPI)

| Router atual | Controller | Principais rotas |
|---|---|---|
| `auth` | `AuthController` | `POST /auth/login`, `POST /auth/sso` |
| `users` | `UserController` | CRUD, `/me`, `/me/password`, `/{id}/eligibilities`, `/{id}/limits`, `/{id}/unavailabilities` |
| `profiles` | `ProfileController` | CRUD, `GET /profiles/groups` |
| `schedule_types` | `ScheduleTypeController` | CRUD |
| `calendars` | `CalendarController` | CRUD, `apply-default-template`, `PATCH /{id}/days/{dayId}` |
| `schedules` | `ScheduleController` | list/get, `published`, `simulate`, `generate`, `publish`, `DELETE`, `PATCH assignments/{id}`, `manual-fill` |
| `preferences` | `PreferenceController` | `/options`, CRUD, `/config` |
| `exchanges` | `ExchangeController` | `board`, `mine`, `pending-approval`, `offer`, `direct`, `propose`, `accept`, `reject`, `cancel`, `approve`, `manager-reject`, `config` |
| `balance` | `BalanceController` | `/me`, `/leaderboard`, `/config` |
| `audit` | `AuditController` | `GET /audit` |
| `diagnostics` | `DiagnosticsController` | `GET /diagnostics` |

Prefixo `/api/v1`. Autorização: `@PreAuthorize("hasRole('MANAGER')")` no equivalente a `get_current_manager`;
`get_current_user` = qualquer autenticado.

### Solver em OR-Tools Java (o item mais técnico)

Portar `app/services/optimizer/solver.py` quase 1:1:
- Variáveis: `BoolVar x[perito][dia][tipo]`, `IntVar gap[dia][tipo]`.
- **Restrições rígidas**: indisponibilidade, elegibilidade, 1 turno/dia, cobertura = atrib.+gap,
  **cota por grupo ponderada** (`Σ peso·x ≤ cota`), interstício pós-Plantão (com borda do mês).
- **Objetivo** (pesos lidos do `BalanceConfig`): `−wGap·gap +wDesired·desejo −wAvoid·evitar`
  + saldo (positivo → escalar menos) + `−wEquity·desvio`.
- `solver.getParameters().setRandomSeed(42)` para reprodutibilidade; `setMaxTimeInSeconds(...)`.
- Persistir `Assignment`s + `SolverAudit`; status → `GENERATED`.
- Rodar em `@Async` (equivalente ao Celery): endpoint cria `Schedule(DRAFT)` e dispara a tarefa; front faz polling.

### Saldo / regras (serviços)

- `BalanceService.computeAndPersistMonthly(scheduleId)` — pontos por evento, normalização pela média,
  **imutável para quem não tem elegibilidade**, congelado na versão publicada.
- `ExchangeValidator.validate(reqAssignment, tgtAssignment)` — mesmo grupo, antecedência, elegibilidade,
  indisponibilidade, interstício, sem duplo turno no dia.
- `AuditService.log(...)` chamado em toda mutação (espelhar o `log_action`).

---

## Frontend — Angular 21

Estrutura por feature (standalone components + signals + um `ApiService` central):

```
src/app
├── core/          # ApiService (HttpClient), AuthService, interceptors (JWT, 401), guards
├── shared/        # UI base (Button, Card, Badge, InfoTip), pipes
├── features/
│   ├── gestor/    # usuarios, perfis, tipos, calendarios, escalas, aprovar-trocas, saldo, auditoria
│   └── perito/    # agenda, escala-geral, trocas, saldo
└── app.routes.ts  # rotas + canActivate (auth/role)
```

| React (hoje) | Angular 21 |
|---|---|
| TanStack Query | `HttpClient` + signals (ou `@tanstack/angular-query`) |
| `lib/api.ts` (axios + interceptors) | `ApiService` + `HttpInterceptor` (Bearer token, 401→login) |
| React Router + `RequireAuth` | `Routes` + `CanActivateFn` (auth e papel) |
| páginas `pages/*` | componentes standalone em `features/*` |
| Tailwind | Tailwind (mesmas classes) |

Mapa de telas (1:1 com as atuais): Login, SSO; **Perito**: Minha Agenda, Escala Geral, Trocas, Meu Saldo;
**Gestor**: Usuários (+modal), Perfis & Regras, Tipos de Escala, Calendários (+detalhe), Escalas (+detalhe),
Aprovar Trocas, Saldo/Ranking, Auditoria, Diagnóstico. Menu mostra "Minha área" + "Gestão" para gestor.

---

## Ordem de execução (milestones)

1. **Esqueleto** Spring Boot (Gradle, Java 25) + Postgres + Flyway (schema inicial) + Security/JWT + OpenAPI.
2. **Entidades + repositories + auth** (login/sso) — paridade com `/auth` e `/users/me`.
3. **CRUDs de configuração**: usuários, perfis/cotas, tipos, elegibilidades, indisponibilidades.
4. **Calendário + cobertura**.
5. **Solver (OR-Tools Java)** + geração assíncrona + auditoria matemática. ← maior risco, validar cedo.
6. **Publicação + saldo** (cálculo, normalização, ranking) + config de pesos.
7. **Preferências por modalidade** + limites.
8. **Trocas** (mural/direta, aprovação do gestor, antecedência) + escala pública.
9. **Auditoria + diagnóstico**.
10. **Angular**: core/auth → telas do perito → telas do gestor.
11. **Testes** (JUnit dos casos críticos do solver/saldo/trocas) + CI (GitHub Actions com Gradle + Angular build).

---

## Riscos e dicas

- **OR-Tools Java** é o ponto crítico: confirme que a equipe topa mantê-lo e valide o porte do solver logo no início (milestone 5) com um cenário pequeno (igual aos testes `test_solver.py`).
- **jsonb**: vários campos usam JSON — configure o tipo no Hibernate desde o começo.
- **Geração assíncrona**: replicar o padrão "cria DRAFT → processa em background → polling" para não travar a request.
- **Reprodutibilidade**: manter `random_seed = 42` para o solver Java dar resultados estáveis.
- **Não migrar dados**: o banco é de teste; comece limpo e rode o seed equivalente.
