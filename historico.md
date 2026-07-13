# Histórico do Projeto (resumo de decisões)

> Resumo enxuto da evolução e das decisões finais. Detalhes vivos em SPEC.md, README.md,
> CONTEXT.md, SECURITY.md e MIGRACAO.md. Itens já substituídos foram omitidos.

## O que é
Sistema web de gestão e distribuição de escalas de peritos. Distribuição por **otimização**
(OR-Tools CP-SAT, seed fixo), não sorteio. Stack: FastAPI/SQLAlchemy/PostgreSQL/Celery/Redis +
React/TS. Docker Compose. **Protótipo** (não-produção; dados de teste).
Credenciais dev: `admin/admin` (gestor), `usuario/usuario` (perito). Repo: github.com/everaldohd/distribuicao-integacao.

## Decisões finais de domínio
- **Perfis = cota por GRUPO** (Plantão/Reserva/Pátio), ponderada (Reserva 12h conta 2).
  Perfis: Lotado na Interna (1/2/0), Interna c/ Restrição (0/0/1), Externa (0/0/0), Chefe (1/2/0),
  Direção (0/0/0), **Fora do Integração** (padrão, 0/0/0), **Personalizado** (por perito).
  Editar cota de um perito → vira Personalizado. (Substituiu o modelo antigo de cota por tipo.)
- **Elegibilidade** por tipo; ao trocar perfil, sincroniza com os grupos do novo perfil.
- **Preferências por modalidade** (tipo): limite = cota do grupo × fator global; desejo/evitar
  separados; só em dias que o calendário oferece o tipo.
- **Saldo**: +10 data evitada, −10 mês sem escala, −5 desejada, 0 comum (configuráveis).
  Positivo = prejudicado → escalado menos. Negativo = poupado → escalado mais. Normalizado pela média.
  **Imutável p/ quem não tem elegibilidade**. Congelado na versão publicada.
- **Solver — prioridade (pesos configuráveis pelo gestor)**: evitar buracos (100k) ≫ saldo (~1k) >
  desejo (300) > evitar (200) > equilíbrio de carga (50). Restrições rígidas: indisponibilidade,
  elegibilidade, 1 turno/dia, cota por grupo, interstício pós-Plantão (com borda do mês).
- **Papel é só permissão**: gestor também pode ser escalado (perfil+elegibilidade); vê "Minha área" + "Gestão".
- **Trocas**: 1:1 **mesmo grupo** (sem "venda"/cobertura), **aprovação do gestor obrigatória**,
  **antecedência mínima** configurável. Mural (oferta aberta) + direta. Execução atômica na aprovação.
  Escala publicada é **pública** (calendário geral).
- **Calendário**: Rascunho → Aberto → Finalizado (ao publicar). Escala publicada editável só com justificativa.

## Infra/qualidade implementadas
- **Alembic** (migrations versionadas; `create_all` aposentado). **CI** GitHub Actions (lint+test+build+scan deps).
- **Testes**: pytest (42, inclui solver/saldo/trocas + import de planilha) + vitest. **Lint**: ruff + eslint.
- **Importar cobertura por planilha (.xlsx)**: gestor importa a escala macro do instituto e o sistema
  deriva as vagas do calendário pelas **seções de interesse** que ele marca (A–F→Plantão 12h somando;
  RM/RT→Reserva Manhã/Tarde; fim de semana c/ RM=RT→Reserva 12h; PIM/PIT→Pátio). Parser puro e testável
  (`services/xlsx_import.py`); gabarito conferido à mão em `tests/test_xlsx_import.py`. Frontend com
  drag-and-drop + `ErrorBoundary`.
- **Auditoria** completa (toda ação, com antes/depois) + tela. **Diagnóstico** (/diagnostics).
- **Tooltips (ⓘ)** nas configs. **Meu Saldo** explicado (arredondado, histórico por eventos).
- **SSO NEO**: preparado e **desabilitado** por padrão.

## Segurança (ver SECURITY.md)
Feito: hash bcrypt, **rate limit no login** (10/min), **política de senha** (mín. 8 + complexidade +
máx. 72 bytes real do bcrypt), duplicados → 400, escala não publicada só p/ gestor, **lock** na
aprovação de troca, cabeçalhos HTTP, `.env` fora do git, scan de deps no CI.
**JWT em cookie HttpOnly + CSRF (double-submit) + logout** (saiu do localStorage; Bearer ainda aceito p/ API).
Credenciais de banco parametrizadas por ambiente no docker-compose.
Pendente p/ produção: **SECRET_KEY forte** (adiado), credenciais de banco fortes no deploy, **HTTPS**
+ `COOKIE_SECURE=true`, rate limit distribuído (Redis).

## Robustez / falhas ao longo do tempo (corrigidas)
- **SECRET_KEY**: chave forte no `.env`; sem chave configurada o app avisa (não gera efêmera silenciosa).
- **Troca desatualizada**: `approve` agora confere se as vagas ainda pertencem às partes (409 se mudou)
  e invalida outras trocas pendentes sobre as mesmas vagas após o swap.
- **Expiração de ofertas**: tarefa Celery beat diária (`expire_stale_exchanges`, 03:00 SP) marca EXPIRED
  trocas pendentes cujo turno entrou no prazo de antecedência.
- **Interstício na virada de mês**: validação de troca não filtra mais por `schedule_id` (cobre o dia
  seguinte/anterior em outra escala).
- **`post_publish_tasks` idempotente**: não recalcula saldo já existente e ainda notifica (Celery é at-least-once).
- **Fuso horário**: regras de data usam `America/Sao_Paulo` (`core/timeutil.py`, fallback UTC−3; `tzdata` no requirements).

> **Não é problema nesta escala:** com 100 pessoas e 1 publicação/mês (~120 rodadas em 10 anos), `historical_balances`
> fica em ~12k linhas e `audit_logs` em dezenas de milhares — volume trivial p/ Postgres. A tela de auditoria já é
> paginada e sem N+1. Retenção/arquivamento **não é necessário**. Único item de UX em aberto: refresh token (sessão de 8h).

## Migração futura (possível) — ver MIGRACAO.md
Alvo: **Java 25 + Spring Boot + Gradle + Angular 21**. Estratégia: reescrita limpa usando este repo +
SPEC.md + OpenAPI como especificação; reaproveitar Postgres; **OR-Tools tem API Java** (solver porta-se).
Não é decisão fechada — pode permanecer em Python.

## Próximos passos
- Finalizar pendências de segurança de produção quando for o deploy.
- (Opcional) Expiração automática de ofertas de troca; datas especiais (Natal/Carnaval).
