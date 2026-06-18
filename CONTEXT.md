# CONTEXT – Sistema de Gestão e Distribuição de Escalas

> Referência rápida para retomar sessões. Leia antes de mexer no projeto.
> Documentação completa: **[README.md](README.md)**. Especificação original: **SPEC.md**.

---

## Visão Geral

Sistema web para gerenciar, distribuir e auditar escalas de serviço de peritos.
Distribuição por **otimização matemática** (OR-Tools CP-SAT), não por sorteio.
Justiça mantida por **saldo de compensação** acumulado por perito.

**Stack:** Python · FastAPI · SQLAlchemy 2.0 · PostgreSQL · Celery · Redis · OR-Tools CP-SAT
· React + TypeScript + Vite + TanStack Query + Tailwind. Tudo via **Docker Compose**
(`db`, `redis`, `backend`, `worker`, `frontend`). Monorepo: `backend/` + `frontend/`.

**Credenciais dev (seed):** `admin`/`admin` (gestor) · `usuario`/`usuario` (perito).

---

## Estado Atual (o que está pronto)

- ✅ Backend completo (auth, usuários, perfis, calendários, escalas, preferências, saldo, trocas-base, auditoria).
- ✅ Frontend completo do gestor e do perito.
- ✅ **Perfis por GRUPO** (Plantão/Reserva/Pátio) com cota ponderada (Reserva 12h = 2).
- ✅ **Preferências por MODALIDADE** com limite = cota_grupo × fator (separado p/ desejo/evitar).
- ✅ Editor visual de calendário (cobertura por dia) e de escala (reatribuir vagas).
- ✅ Calendário vira **Finalizado** ao publicar; escala publicada editável só **com justificativa**.
- ✅ Ranking inclui todos os peritos ativos; saldo imutável p/ quem não tem elegibilidade.
- ✅ **SSO NEO** preparado (endpoint + rota), **desativado por padrão** (`NEO_SSO_SECRET` vazio).

---

## Regras de Negócio Críticas

| Regra | Detalhe |
|---|---|
| Cota por grupo | `Σ (peso × turnos) ≤ cota` por perito/grupo. Reserva 12h pesa 2. Editar cota de um perito → vira **Personalizado**. |
| Perfil padrão | Quem não tem perfil cai em **Fora do Integração** (cotas zeradas). |
| Interstício pós-Plantão 12h | Sem escala no dia seguinte. Vale inclusive na borda do mês (consulta publicação anterior). |
| Buraco na escala | Faltando perito, a vaga fica vazia (variável de folga). Nunca falha. |
| Saldo | Positivo = prejudicado → escalado menos. Normalizado mensalmente. Só sobre a versão publicada. Imutável p/ inelegíveis. |
| Preferências | Por modalidade; só em dias com cobertura; limite cota×fator (desejo/evitar separados). |
| Versão publicada | Calendário trava (Finalizado). Alteração exige justificativa (auditada). |
| Reprodutibilidade | CP-SAT `random_seed = 42`. |

---

## Modelos (backend/app/models)

- **user.py** — `User`: + `matricula` (p/ NEO), `profile_id` (string, sem FK rígida).
- **profile.py** — `Profile` (flags `is_default`/`is_custom`/`is_system`) · `ProfileGroupLimit`
  (cota por grupo) · `UserGroupLimit` (cota individual do Personalizado) · `ProfileRule` (legado, não usado).
- **schedule_type.py** — `ScheduleType`: + `group_name`, `group_weight`.
- **eligibility.py** — `Eligibility`: user × tipo × is_eligible.
- **operational_calendar.py** — `OperationalCalendar` (status draft/open/locked) · `CalendarDay` · `DayCoverage`.
- **preference.py** — `UserPreference`: + `schedule_type_id` (modalidade) + `type` (desired/avoid).
- **schedule.py** — `Schedule` (draft/generated/published/...) · `Assignment` (props `user_name`/`schedule_type_name`).
- **historical_balance.py** — `HistoricalBalance` · `BalanceConfig` (+ `preference_factor`).
- **unavailability.py**, **exchange.py**, **audit.py** (`AuditLog` + `SolverAudit`).

> Schema gerenciado por **Alembic** (migration inicial em `alembic/versions/`). `alembic upgrade head`
> roda no startup do backend; em instalação nova cria tudo. O `create_all` foi aposentado.

---

## Solver (`services/optimizer/solver.py`)

`ScheduleSolver`. Var.: `x[perito,dia,tipo]`, `gap[dia,tipo]`.
Restrições: indisponibilidade · elegibilidade · 1 turno/dia · cobertura=atrib.+gap ·
**cota por grupo ponderada** · interstício (com borda do mês).
Objetivo: `−100k·gap +300·desejo −200·evitar` · saldo (**positivo → escalar menos**) · `±50` equidade.
Saída: `Assignment`s + `SolverAudit`; `Schedule.status = generated`. Roda async no Celery.

---

## Telas (frontend/src/pages)

**Gestor:** Usuários (+ modal: perfil, elegibilidades, cota por grupo, férias) · **Perfis & Regras**
(cotas por grupo + fator de preferências) · Tipos de Escala · Calendários (+ detalhe por dia) ·
Escalas (Em preparação / Publicadas; ver-editar; apagar não publicada) · detalhe da escala (reatribuir) ·
Saldo/Ranking.
**Perito:** **Minha Agenda** (preferências por modalidade com cores; pós-publicação vira dourado read-only) ·
Trocas · Meu Saldo.

---

## Como Subir

```bash
cp backend/.env.example backend/.env   # ajustar
docker compose up --build
# Frontend 5173 · API 8000 · Docs /docs
docker compose exec backend python -m app.seed_test   # 100 peritos de teste
```

---

## Trocas de escala

Troca **1:1, mesmo grupo** (Plantão/Reserva/Pátio), com **aprovação do gestor** e auditoria.
Fluxos: mural (oferta aberta → colega propõe) e direta (solicita a um colega). Antecedência
mínima configurável (`BalanceConfig.exchange_min_lead_days`). Validação rígida em cada etapa;
execução atômica (swap das atribuições) só na aprovação. `GET /schedules/published` expõe a
escala do mês a qualquer perito (calendário geral). Router: `app/routers/exchanges.py`.

## Próximos Passos

- [ ] Integração NEO (SSO) real — habilitar quando a equipe do NEO fornecer o segredo/contrato.
- [ ] Relatórios e datas especiais (Natal/Ano Novo/Carnaval), previstos na SPEC.
- [ ] Expiração automática de ofertas de troca ao entrar na janela de antecedência (hoje a
      antecedência é checada na criação/aceite/aprovação; falta um job que marque `expired`).
