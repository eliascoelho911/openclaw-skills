# Phase 0 Research - Transacoes Recorrentes

## Escopo pesquisado

Esta fase consolidou decisoes para implementar recorrencias mensais no
`compras_divididas` com idempotencia por recorrencia+competencia, retomada segura
apos interrupcao, ciclo de vida completo e contratos HTTP consistentes com a API
existente.

## Decisoes

### 1) Estrategia de modelagem da recorrencia

- **Decision**: Introduzir tres agregados dedicados: `recurrence_rule`
  (configuracao mutavel), `recurrence_occurrence` (ledger por competencia) e
  `recurrence_event` (auditoria append-only).
- **Rationale**: Separa claramente regra de negocio futura, execucao mensal e
  rastreabilidade historica, atendendo FR-005, FR-006, FR-007, FR-009 e FR-015.
- **Alternatives considered**: Persistir tudo em `financial_movements` com flags
  de recorrencia (mistura conceitos e dificulta ciclo de vida); usar apenas uma
  tabela de recorrencia sem ledger de ocorrencias (fraca para retentativas e
  diagnostico de bloqueios).

### 2) Idempotencia e retomada apos interrupcao

- **Decision**: Garantir idempotencia com `UNIQUE(recurrence_rule_id,
  competence_month)` em `recurrence_occurrence`, processar geracao em lotes
  curtos com `FOR UPDATE SKIP LOCKED` e usar rerun da mesma competencia para
  concluir itens faltantes sem duplicar lancamentos.
- **Rationale**: O banco se torna a fonte de verdade contra condicoes de corrida,
  e o processamento em lotes curtos permite retomar apos falha parcial sem
  rollback global do mes.
- **Alternatives considered**: Confiar apenas em pre-check no servico (suscetivel
  a race condition); transacao unica para todo o mes (um erro invalida tudo);
  sem lock por competencia (aumenta contencao e ruido operacional).

### 3) Ciclo de vida da recorrencia

- **Decision**: Adotar estados explicitos `active`, `paused` e `ended`, com
  transicoes `active->paused`, `paused->active`, `active->ended` e
  `paused->ended`; `ended` e terminal.
- **Rationale**: Diferencia pausa temporaria de encerramento definitivo, elimina
  ambiguidade operacional e cobre FR-007 e FR-015 sem deletar historico.
- **Alternatives considered**: Modelo binario ativo/inativo (nao diferencia
  encerramento definitivo); soft-delete (contraria requisito de nao excluir).

### 4) Politica de edicao e concorrencia

- **Decision**: Aplicar last-write-wins em atualizacoes da regra e bloquear
  alteracao de `start_competence_month` apos primeira geracao bem-sucedida.
  Demais campos continuam editaveis.
- **Rationale**: Atende FR-013 e FR-014 com comportamento previsivel e simples,
  preservando a capacidade de ajuste rapido para competencias futuras.
- **Alternatives considered**: Optimistic locking com conflito de versao (nao
  atende last-write-wins); congelar regra inteira apos primeira geracao (inviabiliza
  manutencao prevista em FR-007/FR-008).

### 5) Regra de calendario mensal e ajuste de dia invalido

- **Decision**: Calcular data da ocorrencia no dominio com
  `scheduled_day = min(reference_day, ultimo_dia_do_mes)` e representar
  competencia como primeiro dia do mes (`YYYY-MM-01`).
- **Rationale**: A logica fica deterministica e facilmente testavel em unit
  tests, cobrindo FR-016 e edge case de meses curtos/leap year.
- **Alternatives considered**: Calcular tudo em SQL (mais dificil de validar e
  manter); fixar erro quando o dia nao existe (contraria FR-016).

### 6) Padrao de contratos FastAPI/Pydantic

- **Decision**: Expor endpoints novos em `/v1/recurrences` para CRUD/lifecycle e
  endpoint de execucao mensal em `/v1/months/{year}/{month}/recurrences/generate`,
  mantendo envelope de erro `{code, message, details}`.
- **Rationale**: Mantem consistencia com o padrao atual de rotas `v1`, permite
  validacao forte com Pydantic e devolve contadores de geracao (`generated`,
  `ignored`, `blocked`, `failed`) exigidos por FR-011.
- **Alternatives considered**: Endpoint generico unico de status via `PATCH`
  (menos explicito para auditoria); endpoint assincorono com fila (complexidade
  desnecessaria para o volume alvo atual).

### 7) Integracao com modulos existentes

- **Decision**: Reutilizar validacoes e regras consolidadas de
  `participant_repository`, `movement_service`, `domain.competence` e
  `domain.money`; adicionar modulo de recorrencia nas mesmas camadas atuais
  (`api`, `services`, `repositories`, `db/models`, `tests`).
- **Rationale**: Reduz duplicacao e risco de inconsistencias entre lancamento
  manual e lancamento gerado por recorrencia, mantendo a arquitetura ja usada no
  projeto.
- **Alternatives considered**: Criar fluxo paralelo sem reutilizar
  `movement_service` (duplicaria regras e mensagens); gerar movimentos apenas no
  cliente (perde controle de idempotencia e auditoria no servidor).

### 8) Observabilidade e eventos de negocio

- **Decision**: Registrar eventos append-only para criacao, edicao, pausa,
  reativacao, encerramento e resultados da geracao (`generated`, `blocked`,
  `failed`, `ignored`), com ator, timestamp e payload contextual.
- **Rationale**: Garante rastreabilidade funcional pedida em FR-009 e facilita
  diagnostico sem depender apenas de logs de infraestrutura.
- **Alternatives considered**: Somente logs de aplicacao (pior consulta de
  historico funcional); sem eventos dedicados (fraco para auditoria).

### 9) Estrategia de testes e validacao de performance

- **Decision**: Cobertura obrigatoria em tres niveis: unit (regras de calendario,
  transicoes e validacoes), integration (constraints PostgreSQL,
  concorrencia/idempotencia/retomada) e contract (endpoints e codigos HTTP), com
  cenario de performance para 1.000 recorrencias elegiveis por competencia.
- **Rationale**: Alinha com a constituicao (Tests Define Done e Performance
  Budgets) e cobre os riscos principais da feature.
- **Alternatives considered**: Apenas integration tests (feedback mais lento) ou
  apenas teste manual de carga (sem repetibilidade).
