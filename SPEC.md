# Especificação Funcional – Sistema Inteligente de Gestão e Distribuição de Escalas

## Objetivo

Desenvolver um sistema web para gerenciamento, distribuição, publicação, auditoria e troca de escalas de serviço, utilizando otimização matemática para garantir distribuição justa, transparente e auditável.

O sistema deverá permitir que gestores configurem a necessidade operacional de cada período e que os usuários informem preferências, enquanto um motor de otimização distribui as escalas respeitando restrições e compensando historicamente os usuários mais prejudicados.

O sistema não deve ser baseado em sorteio aleatório.

Toda distribuição deverá ser produzida por otimização matemática reproduzível e auditável.

---

# Arquitetura

## Backend

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Celery e Redis para execução assíncrona do motor de otimização em background, evitando bloqueio de thread no endpoint da API.

## Motor de Otimização

* Google OR-Tools
* Solver CP-SAT com `random_seed` fixo para garantir reprodutibilidade total.

## Frontend

* React + TypeScript
* Interface web responsiva.
* Separação entre Área do Gestor e Área do Usuário.
* Frontend desacoplado via API REST.

## Organização

Monorepo com pastas `backend/` e `frontend/`.

---

# Conceitos Gerais

O sistema é dividido em quatro motores principais:

## Motor de Cobertura

Define quantas vagas existem em cada dia e em cada tipo de escala.

## Motor de Distribuição

Executa a otimização matemática para atribuição das escalas.

## Motor de Compensação

Mantém histórico de justiça e equilíbrio ao longo do tempo.

## Motor de Trocas

Permite alterações posteriores sem impactar o histórico oficial utilizado pelo algoritmo.

---

# Tipos de Escala

O sistema deve permitir cadastro de tipos de escala configuráveis (apenas turnos diurnos).

Tipos iniciais:

* Plantão 12h
* Reserva Manhã
* Reserva Tarde
* Reserva 12h
* Pátio Manhã
* Pátio Tarde

Novos tipos poderão ser adicionados futuramente sem alteração estrutural.

---

# Elegibilidade

Cada usuário poderá ser elegível ou inelegível para cada tipo de escala.

Exemplo:

| Tipo    | Elegível |
| ------- | -------- |
| Plantão | Sim      |
| Reserva | Sim      |
| Pátio   | Não      |

O algoritmo somente poderá considerar candidatos elegíveis.

---

# Perfis de Distribuição

O sistema deverá permitir que o gestor crie perfis personalizados.

Cada perfil define quantas atribuições de cada tipo deverão ser distribuídas ao usuário durante o mês.

Exemplo:

Perfil 1:

* Plantão 12h: 1
* Reserva 12h: 0
* Reserva Manhã: 1
* Reserva Tarde: 1
* Pátio Manhã: 0
* Pátio Tarde: 0

Perfil 2:

* Plantão 12h: 4
* Reserva 12h: 4

Perfil 3:

* Pátio Manhã: 4
* Pátio Tarde: 4

Os nomes dos perfis serão definidos livremente pelo gestor.

Exceções individuais poderão sobrescrever os valores do perfil para um usuário específico.

Quando uma exceção individual torna a cobertura de um dia inviável (ex.: reduz demais o pool disponível), o sistema trata o turno como buraco na escala — não como erro de configuração.

---

# Calendário Operacional

Ao criar um mês, o sistema deverá classificar automaticamente:

* Segunda a sexta: Dia útil
* Sábado: Final de semana
* Domingo: Final de semana

O gestor poderá alterar manualmente qualquer data para:

* Dia útil
* Final de semana
* Feriado

O sistema não deverá depender de feriados automáticos.

A classificação final sempre será definida pelo gestor.

---

# Modelo de Cobertura

O gestor configura um modelo padrão para cada categoria de dia.

## Exemplo – Dias Úteis

| Tipo          | Quantidade |
| ------------- | ---------: |
| Plantão 12h   |          2 |
| Reserva Manhã |          1 |
| Reserva Tarde |          1 |
| Reserva 12h   |          0 |
| Pátio Manhã   |          1 |
| Pátio Tarde   |          1 |

## Exemplo – Finais de Semana

| Tipo          | Quantidade |
| ------------- | ---------: |
| Plantão 12h   |          1 |
| Reserva Manhã |          0 |
| Reserva Tarde |          0 |
| Reserva 12h   |          1 |
| Pátio Manhã   |          0 |
| Pátio Tarde   |          0 |

## Exemplo – Feriados

| Tipo        | Quantidade |
| ----------- | ---------: |
| Plantão 12h |          1 |
| Reserva 12h |          1 |

Após gerar o calendário do mês, o gestor poderá alterar individualmente qualquer dia.

Todas as alterações devem ficar registradas na auditoria com motivo.

---

# Preferências dos Usuários

Antes da geração da escala, o usuário poderá informar:

## Datas Desejadas

Datas que prefere trabalhar.

## Datas a Evitar

Datas que prefere evitar.

Essas informações são preferências — não restrições obrigatórias.

---

# Indisponibilidades

Serão cadastradas pelo gestor.

Tipos iniciais:

* Férias
* Abonos
* Licenças

O algoritmo nunca poderá escalar usuários em períodos indisponíveis.

---

# Regras Operacionais

## Restrições Rígidas

Jamais podem ser violadas.

* Não escalar durante férias, abonos ou licenças.
* Não atribuir mais de uma escala ao mesmo usuário no mesmo dia.
* Não atribuir Plantão de 12h em dias seguidos para o mesmo usuário.
* Não atribuir nenhuma escala (qualquer tipo) no dia imediatamente seguinte a um Plantão de 12h (interstício obrigatório). **Essa restrição aplica-se também na borda do mês**: se um usuário fez Plantão 12h no último dia do mês anterior (versão publicada), ele não poderá receber nenhuma escala no dia 1 do mês sendo gerado. O algoritmo deverá consultar o mês anterior para verificar essa condição.
* Respeitar elegibilidade.
* Respeitar cotas do perfil.
* Respeitar exceções individuais.

## Restrições Suaves

Devem ser maximizadas ou minimizadas.

* Atender datas desejadas.
* Evitar datas indesejadas.
* Equilibrar distribuição histórica.
* Reduzir concentração de datas desfavoráveis.
* Favorecer usuários historicamente mais prejudicados.

## Tratamento de Inviabilidade (Buracos na Escala)

Caso não haja quantidade suficiente de usuários elegíveis e disponíveis para cobrir as vagas de um determinado dia, o motor de otimização não deve travar ou falhar.

O algoritmo deverá utilizar variáveis de folga para deixar o turno em branco. A interface exibirá esse espaço como um "buraco na escala" com alerta visual, indicando que o gestor deve solucionar a falta de efetivo manualmente (preenchimento manual disponível na Área do Gestor).

---

# Saldo Histórico de Compensação

Cada usuário possui um saldo acumulado.

O saldo acompanha o usuário independentemente de mudanças de função ou elegibilidade.

Valores padrão:

| Evento                 | Valor |
| ---------------------- | ----: |
| Mês sem escala         |   -10 |
| Data desejada atendida |    -5 |
| Escala comum           |     0 |
| Data evitada atribuída |   +10 |

Os valores deverão ser configuráveis por gestores.

O algoritmo deverá priorizar usuários com maior saldo acumulado.

## Entrada de Novos Usuários

Ao cadastrar um novo usuário, seu saldo histórico inicial será a média matemática dos saldos atuais de todos os usuários ativos, garantindo que ele entre nivelado com a equipe.

## Normalização (Deflação)

Após o fechamento de cada ciclo mensal, caso a média geral dos saldos sofra inflação ou deflação sistêmica, o sistema deverá aplicar um fator de normalização, subtraindo a média geral do saldo de cada usuário. Isso preserva as diferenças relativas e evita crescimento infinito dos números.

---

# Congelamento do Histórico

O saldo histórico será calculado exclusivamente com base na versão publicada da escala.

Trocas posteriores não alteram o saldo.

Exemplo: Agosto publicado → saldo calculado. Trocas realizadas posteriormente não afetam o saldo utilizado na geração de setembro.

---

# Fluxo de Geração

1. Gestor configura o mês.
2. Gestor cadastra férias e abonos.
3. Usuários informam preferências.
4. Gestor executa simulação.
5. Gestor gera a escala.
6. Gestor realiza ajustes manuais.
7. Gestor publica a escala.

---

# Simulação

Antes da geração definitiva, o sistema deverá apresentar:

* Quantidade total de vagas.
* Quantidade de usuários elegíveis.
* Percentual estimado de preferências atendidas.
* Quantidade estimada de datas evitadas atribuídas.
* Quantidade exata de possíveis buracos na escala (vagas sem preenchimento).
* Estatísticas gerais da distribuição.

---

# Explicabilidade

Cada atribuição gerada deverá possuir justificativas baseadas em metadados simples de validação (flags indicativas), sem necessidade de expor pesos complexos ou fórmulas matemáticas na interface final.

Exemplo:

"Usuário selecionado porque:
* Era elegível.
* Não possuía indisponibilidade.
* Cumpriu o interstício de descanso.
* Possuía saldo histórico positivo (+15).
* Atendia a uma preferência cadastrada."

---

# Versionamento de Escalas

Nenhuma escala publicada poderá ser sobrescrita.

Estados possíveis:

* Rascunho
* Simulada
* Gerada
* Publicada
* Arquivada

Toda alteração após publicação deverá gerar uma nova versão.

Todas as versões são preservadas para consulta.

---

# Sistema de Trocas

Após a publicação da escala.

## Troca Aberta

O usuário disponibiliza uma escala para troca. Fica visível para todos os usuários elegíveis para aquele tipo de escala.

## Troca Direta

Um usuário pode solicitar troca diretamente para outro usuário.

## Validação

Toda troca deve passar por validação automática. O sistema deve impedir trocas que violem regras operacionais rígidas (incluindo o interstício pós-plantão 12h).

## Auditoria de Trocas

Toda troca deverá registrar: solicitante, destinatário, datas envolvidas, data e hora, resultado.

---

# Notificações por E-mail

O sistema enviará e-mails automáticos nos seguintes eventos:

* Publicação de nova escala (para todos os usuários escalados no mês).
* Solicitação de troca recebida (para o destinatário).
* Troca aceita ou recusada (para o solicitante).
* Escala com buraco preenchida manualmente pelo gestor (para o usuário afetado).

O e-mail de cada usuário é cadastrado pelo gestor no momento da criação do perfil do usuário. Não há auto-cadastro de usuários.

---

# Gestores (Administradores)

O gestor é o papel administrativo do sistema. Podem existir múltiplos gestores.

Gestores têm acesso total a todas as funcionalidades de configuração, geração, publicação e auditoria.

O primeiro gestor é criado via script de seed ou variável de ambiente na inicialização do sistema.

Gestores adicionais são criados por gestores existentes.

---

# Auditoria Operacional

Registrar:

* Criação e alteração de perfis
* Cadastro de férias e abonos
* Geração de escala
* Publicação
* Alterações manuais (com motivo)
* Trocas

Cada registro deve conter: data e hora, usuário responsável, valor anterior, valor novo.

---

# Auditoria Matemática

Registrar informações da execução do solver:

* Número de usuários elegíveis
* Número de vagas
* Preferências cadastradas e atendidas
* Datas evitadas atribuídas
* Quantidade de turnos descobertos (buracos)
* Tempo de processamento
* Função objetivo final
* Seed utilizado

---

# Área do Usuário

Visualização em calendário semelhante ao Google Agenda.

Funcionalidades:

* Consultar escalas futuras.
* Consultar histórico.
* Informar preferências.
* Disponibilizar escalas para troca.
* Solicitar trocas.
* Consultar histórico de trocas.
* Consultar saldo histórico.

## Indicador de Equilíbrio

Exibir:

* Saldo atual.
* Posição relativa na equipe (ex.: "72º de 103").
* Evolução histórica com representação gráfica.

---

# Área do Gestor

Funcionalidades:

* Cadastro de usuários (incluindo e-mail para notificações).
* Cadastro de perfis e elegibilidades.
* Configuração mensal e modelo de cobertura.
* Alteração individual de datas com motivo registrado.
* Simulação antes da geração.
* Geração de escala.
* Preenchimento manual de turnos descobertos.
* Ajustes manuais gerais.
* Publicação.
* Relatórios.
* Auditoria completa.
* Cadastro de outros gestores.
* Configuração dos valores do saldo de compensação.

---

# Algoritmo de Distribuição

Utilizar Google OR-Tools CP-SAT com `random_seed` fixo.

Objetivo principal: maximizar justiça histórica.

Objetivos secundários:

1. Respeitar todas as restrições rígidas.
2. Atender o maior número possível de preferências.
3. Minimizar atribuições em datas evitadas.
4. Equilibrar cargas de trabalho.
5. Priorizar usuários historicamente prejudicados.
6. Gerar buracos na escala de forma controlada em caso de inviabilidade.
7. Produzir solução reproduzível e auditável.

Não utilizar sorteio aleatório como mecanismo principal.

---

# Evolução Futura Planejada

Implementar módulo específico para datas especiais (Natal, Ano Novo, Carnaval) com regras próprias de rodízio e distribuição independentes do mecanismo padrão de compensação.
