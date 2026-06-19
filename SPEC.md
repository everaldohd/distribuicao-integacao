# Especificação Funcional – Sistema de Gestão e Distribuição de Escalas

> **Status:** protótipo funcional (não está em produção; dados do banco são de teste e podem ser descartados).
> Este documento descreve o **comportamento atual** do sistema e serve de especificação para manutenção
> ou reimplementação em outro stack (ex.: Java/Spring Boot + Angular). A lógica de negócio descrita aqui
> independe da linguagem.

## Objetivo

Sistema web para gerenciar, distribuir, publicar, auditar e trocar escalas de serviço de peritos,
usando **otimização matemática** (não sorteio) para uma distribuição **justa, transparente e auditável**.
Gestores configuram a necessidade operacional e as regras; peritos informam preferências; um motor de
otimização distribui as escalas respeitando restrições rígidas e compensando historicamente quem foi
mais prejudicado.

---

# Arquitetura (implementação atual)

- **Backend:** Python · FastAPI · SQLAlchemy 2.0 · PostgreSQL · Pydantic v2 · JWT (python-jose/bcrypt)
- **Otimização:** Google OR-Tools, solver **CP-SAT** com `random_seed` fixo (reprodutível)
- **Assíncrono:** Celery + Redis (geração da escala roda em background)
- **Migrations:** Alembic · **Frontend:** React + TypeScript + Vite + TanStack Query + Tailwind
- **Qualidade:** testes (pytest + vitest), lint (ruff + eslint), CI (GitHub Actions)
- **Orquestração:** Docker Compose (serviços: db, redis, backend, worker, frontend) · Monorepo `backend/` + `frontend/`

Os quatro motores conceituais: **Cobertura** (quantas vagas por dia/tipo), **Distribuição** (otimização),
**Compensação** (saldo histórico de justiça) e **Trocas** (alterações pós-publicação sem mexer no histórico).

---

# Papéis

- **Gestor** é apenas o papel **administrativo** (acesso às telas de configuração, geração, publicação, auditoria).
  **O papel NÃO define se a pessoa pode ser escalada.** Um gestor também pode ser perito e ser escalado
  normalmente — basta ter perfil + elegibilidade. Gestores enxergam tanto a "Gestão" quanto a "Minha área".
- **Quem pode ser escalado** é definido por **perfil (cota) + elegibilidade**, para qualquer usuário.
- Múltiplos gestores são permitidos. O primeiro é criado por seed/variável de ambiente. Não há auto-cadastro.

---

# Tipos de Escala e Grupos

Tipos configuráveis (turnos diurnos). Cada tipo pertence a um **grupo** e tem um **peso** dentro do grupo:

| Tipo | Grupo | Peso |
|---|---|---|
| Plantão 12h | Plantão | 1 |
| Reserva Manhã | Reserva | 1 |
| Reserva Tarde | Reserva | 1 |
| Reserva 12h | Reserva | **2** |
| Pátio Manhã | Pátio | 1 |
| Pátio Tarde | Pátio | 1 |

O **peso** existe porque a cota e a troca são por grupo: uma Reserva 12h "consome" 2 reservas.

---

# Elegibilidade

Cada perito é elegível ou não para cada tipo de escala. O algoritmo só considera candidatos elegíveis.

**Sincronização automática:** ao trocar o perfil de um perito, suas elegibilidades são realinhadas aos
grupos liberados pelo novo perfil (habilita os tipos dos grupos com cota > 0, desabilita os demais),
evitando inconsistência. O gestor pode ajustar manualmente depois.

---

# Perfis de Distribuição (cota por GRUPO)

Cada perfil define a **cota MÁXIMA por grupo** (Plantão / Reserva / Pátio) que o perito recebe no mês —
ponderada (Reserva 12h conta 2). Perfis do sistema:

| Perfil | Plantão | Reserva | Pátio |
|---|---|---|---|
| Lotado na Interna | 1 | 2 | 0 |
| Lotado na Interna com Restrição | 0 | 0 | 1 |
| Lotado na Externa | 0 | 0 | 0 |
| Chefe | 1 | 2 | 0 |
| Direção | 0 | 0 | 0 |
| **Fora do Integração** (padrão de quem não tem perfil) | 0 | 0 | 0 |
| **Personalizado** | cota individual por perito |

- O gestor pode **criar novos perfis** e editar as cotas de cada um.
- Ao editar a cota de **um perito específico**, ele migra automaticamente para **Personalizado** (cota individual).
- Quem não tem perfil cai no padrão **Fora do Integração** (cotas zeradas → não é escalado).

> A cota é por grupo (não por tipo). O modelo antigo de "cota por tipo + exceções individuais" foi substituído.

---

# Calendário Operacional

Ao criar um mês, os dias são classificados automaticamente: seg–sex = Dia útil; sáb/dom = Final de semana.
O gestor pode reclassificar qualquer dia (Dia útil / Final de semana / Feriado). Não há feriados automáticos.

## Modelo de Cobertura (vagas por dia/tipo)

O gestor aplica um modelo padrão por categoria de dia (e pode editar dia a dia, com motivo auditado):

- **Dia útil:** 1 Plantão 12h, 1 Reserva Manhã, 1 Reserva Tarde, 1 Pátio Manhã, 1 Pátio Tarde
- **Fim de semana:** 1 Plantão 12h, 1 Reserva 12h

O calendário começa em **Rascunho**, passa a **Aberto** (recebe preferências e gera escala) e vira
**Finalizado** quando a escala daquele mês é publicada.

---

# Preferências dos Usuários (por MODALIDADE)

Antes da publicação, o perito registra preferências **por modalidade** (tipo de escala), não só por dia:

- Modos separados: **Desejo trabalhar** e **Prefiro não**.
- Botões por modalidade liberada pelo perfil (grupos com cota > 0), cada um com cor.
- Só é possível marcar dias em que o **calendário oferece aquela modalidade**.
- **Limite de dias** = cota do grupo × **fator global** (configurável pelo gestor), contado
  **separadamente** para desejo e evitar.
- São preferências, não obrigações.
- Após a publicação do mês, a agenda fica **somente leitura**: os dias escalados aparecem em dourado e as
  preferências continuam visíveis apenas como registro.

---

# Indisponibilidades

Cadastradas pelo gestor: **Férias, Abono, Licença** (período). O algoritmo nunca escala em período indisponível.

---

# Regras Operacionais

## Restrições Rígidas (nunca violadas)

- Não escalar em férias/abono/licença.
- No máximo 1 escala por perito por dia.
- Não atribuir Plantão 12h em dias seguidos ao mesmo perito.
- **Interstício:** nenhuma escala no dia seguinte a um Plantão 12h. Vale também na **borda do mês**
  (consulta a versão publicada do mês anterior para bloquear o dia 1 se necessário).
- Respeitar elegibilidade.
- Respeitar a **cota por grupo** (ponderada).

## Restrições Suaves (otimizadas) — pesos configuráveis pelo gestor

Prioridade efetiva (do mais forte ao mais fraco), com pesos padrão:

1. **Evitar buracos** (vaga vazia) — peso 100.000 (dominante)
2. **Justiça (saldo)** — quem tem saldo alto é escalado **menos** (até ~1.000 por turno)
3. **Atender datas desejadas** — +300
4. **Evitar datas indesejadas** — −200
5. **Equilíbrio de carga** — −50 por desvio

Todos esses pesos são editáveis pelo gestor.

## Buracos na Escala

Se faltam peritos elegíveis/disponíveis, o solver **não falha**: usa variável de folga e deixa a vaga
vazia ("buraco"), sinalizada na interface, para o gestor preencher manualmente.

---

# Saldo Histórico de Compensação

Cada perito tem um saldo acumulado, que o acompanha mesmo mudando de função/elegibilidade.

| Evento | Valor padrão (configurável) |
|---|---|
| Mês sem escala | −10 |
| Data desejada atendida | −5 |
| Escala comum | 0 |
| Data evitada atribuída | +10 |

- **Saldo positivo = prejudicado** → será **poupado** (escalado menos). **Negativo = poupado** → escalado mais.
- **Novo usuário** entra com a **média** dos saldos ativos (nivelado com a equipe).
- **Normalização mensal:** subtrai a média geral de todos, preservando diferenças relativas e evitando
  inflação/deflação infinita.
- **Imutável para quem não pode ser escalado:** perito sem nenhuma elegibilidade não recebe penalidade
  nem entra na normalização (saldo congelado).
- O **ranking** inclui todos que estão na rotação (têm perfil), independentemente de serem gestores.

## Congelamento do Histórico

O saldo é calculado **apenas sobre a versão publicada**. Trocas posteriores não alteram o saldo.

---

# Versionamento de Escalas

Estados: **Rascunho · Simulada · Gerada · Publicada · Arquivada**. Escala publicada não é sobrescrita;
alterações geram nova versão. Todas as versões são preservadas.

## Fluxo de Geração

1. Gestor configura o mês e a cobertura. 2. Gestor cadastra indisponibilidades. 3. Peritos informam
preferências. 4. (Opcional) Simulação. 5. Geração (assíncrona, via solver). 6. Ajustes manuais /
preenchimento de buracos. 7. Publicação (finaliza o calendário, calcula saldo e dispara e-mails).

## Edição pós-publicação

A escala publicada pode ser alterada pelo gestor (reatribuir/esvaziar vaga), porém **com justificativa
obrigatória**, registrada na auditoria.

## Simulação

Estimativa rápida (sem solver): total de vagas, peritos elegíveis, % estimado de preferências atendidas,
datas evitadas estimadas e buracos previstos.

---

# Sistema de Trocas

Após a publicação. **Regra central: troca 1:1, sempre do MESMO grupo** (Plantão↔Plantão, Reserva↔Reserva,
Pátio↔Pátio) — para evitar "venda" e manter carga/cota neutras. **Toda troca exige aprovação do gestor.**

- **Antecedência mínima** (em dias) configurável pelo gestor: os turnos envolvidos devem estar a pelo
  menos N dias no futuro. Verificada ao solicitar, ao aceitar e ao aprovar.
- **Mural (troca aberta):** o perito coloca um turno à disposição; colegas veem e **propõem** um turno do
  mesmo grupo em troca.
- **Troca direta:** o perito escolhe um colega e um turno dele para propor a troca 1:1.
- **Validação rígida** em cada etapa (elegibilidade, indisponibilidade, interstício, sem duplo turno no dia,
  mesmo grupo, antecedência).
- **Aprovação do gestor** executa a troca (swap das atribuições) em transação atômica.
- **Estados:** no mural → aguardando colega → aguardando gestor → aprovada / recusada / cancelada / expirada.
- **Escala geral pública:** qualquer perito vê o calendário do mês publicado com todos os colegas — base
  para identificar turnos e iniciar trocas.
- **Auditoria:** cada transição registra autor, valores antes/depois e descrição.

---

# Notificações por E-mail

Eventos: publicação de escala (escalados do mês), troca solicitada (destinatário), troca aceita/recusada/
aprovada (envolvidos), buraco preenchido manualmente (afetado). E-mail cadastrado pelo gestor.

---

# Auditoria

## Operacional
Registra **todas as ações** de gestor e perito, com data/hora, responsável e valores anterior/novo:
usuários, perfis, elegibilidades, cotas individuais, indisponibilidades, calendário, geração, publicação,
edição manual, configuração de saldo/pesos e todas as transições de troca. Consultável em tela própria.

## Matemática (por geração do solver)
Nº de elegíveis, vagas, preferências cadastradas/atendidas, datas evitadas atribuídas, buracos, tempo de
processamento, função objetivo, seed e parâmetros.

## Diagnóstico
Endpoint que verifica saúde do sistema (banco, Redis, worker Celery, dados base/seed), retornando o que
está OK e o que falhou.

---

# Explicabilidade

Cada atribuição guarda flags simples ("elegível", "descansado", "data desejada", "saldo positivo", etc.)
para justificar a escolha sem expor fórmulas/pesos na interface.

---

# Área do Usuário (perito)

- **Minha Agenda:** calendário do mês; registra preferências por modalidade; após publicado vira leitura
  (dias escalados em dourado).
- **Escala Geral:** calendário público do mês publicado com todos os peritos.
- **Trocas:** colocar à disposição / troca direta / propor / aceitar / recusar / cancelar; acompanhar status.
- **Meu Saldo:** saldo atual (arredondado) com explicação clara do significado e histórico **por eventos**
  (o que aconteceu no mês), sem expor a matemática de normalização.

# Área do Gestor

- **Usuários:** cadastro; por usuário: perfil, elegibilidades, cota individual e indisponibilidades.
- **Perfis & Regras:** cotas por grupo de cada perfil; criar perfis; fator de preferências; antecedência de troca.
- **Tipos de Escala**, **Calendários** (cobertura por dia), **Escalas** (gerar/editar/publicar/apagar não publicadas),
  **Aprovar Trocas**, **Escala Geral**.
- **Saldo / Ranking:** ranking + edição dos **pontos de saldo** e dos **pesos da distribuição** (com dicas).
- **Auditoria** e **Diagnóstico**.
- Configurações têm **dicas (ⓘ)** explicativas ao passar o mouse.

---

# Algoritmo de Distribuição

Google OR-Tools **CP-SAT**, `random_seed` fixo (reprodutível). Variáveis: `x[perito, dia, tipo]` (1 = escalado)
e `gap[dia, tipo]` (vaga vazia). Restrições rígidas e função objetivo conforme as seções acima (pesos
configuráveis). Não usa sorteio.

---

# Evolução Futura Planejada

- Módulo de **datas especiais** (Natal, Ano Novo, Carnaval) com rodízio próprio.
- **Integração NEO (SSO)** — ponto de entrada já preparado e desativado por padrão.
- **Expiração automática** de ofertas de troca ao entrar na janela de antecedência.
