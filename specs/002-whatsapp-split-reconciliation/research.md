# Phase 0 Research - Reconciliacao Mensal de Compras Compartilhadas

## Escopo pesquisado

Esta fase resolve as decisoes tecnicas para entregar uma API FastAPI com
persistencia PostgreSQL no contexto do fechamento mensal de despesas do casal.

## Decisoes

### 1) Framework HTTP da API

- **Decision**: Usar FastAPI como framework principal da API v1.
- **Rationale**: Entrega validacao forte via Pydantic v2, geracao automatica de
  OpenAPI e ergonomia para testes de contrato com TestClient/httpx.
- **Alternatives considered**: Flask + marshmallow (mais manual para contratos),
  Django REST Framework (overhead maior para escopo pequeno).

### 2) Persistencia relacional

- **Decision**: Usar PostgreSQL 16 com SQLAlchemy 2.x e driver psycopg 3.
- **Rationale**: Permite constraints fortes em banco (unicidade de deduplicacao,
  FK para estorno), transacoes ACID e consultas agregadas eficientes para resumo
  e fechamento mensal.
- **Alternatives considered**: SQLite (limitacoes de concorrencia e escala),
  acesso SQL cru com psycopg (mais risco de duplicacao de regras).

### 3) Estrategia de migracoes

- **Decision**: Versionar schema com Alembic.
- **Rationale**: Garante evolucao previsivel do banco entre ambientes e
  rastreabilidade de mudancas de estrutura.
- **Alternatives considered**: SQL manual sem versao (alto risco operacional),
  reset completo de schema por ambiente (incompativel com historico de 24 meses).

### 4) Valores monetarios e arredondamento

- **Decision**: Receber valores como string decimal, converter para `Decimal`,
  aplicar `quantize(0.01, ROUND_HALF_UP)` no registro e persistir em
  `NUMERIC(12,2)`.
- **Rationale**: Atende FR-015 (arredondar cada movimentacao antes de acumular)
  e elimina problemas de ponto flutuante.
- **Alternatives considered**: `float` (imprecisao), armazenar em centavos
  inteiros (viavel, mas adiciona conversoes em todas as respostas BRL).

### 5) Competencia mensal e timezone

- **Decision**: Armazenar `occurred_at` como `timestamptz`; quando ausente no
  payload, preencher com o timestamp atual do registro em
  `America/Sao_Paulo`. Calcular `competence_month` com esse valor efetivo.
- **Rationale**: Garante determinismo de competencia mensal e consultas rapidas
  por indice em `competence_month`.
- **Alternatives considered**: Exigir data sempre no request (menos ergonomico),
  derivar mes em cada consulta (mais custo e risco de divergencia), usar timezone
  do cliente (contradiz requisito).

### 5.1) Pagador opcional no input

- **Decision**: Tornar `payer_participant_id` opcional na API e usar
  `requested_by_participant_id` como valor padrao quando nao informado.
- **Rationale**: Simplifica registro no fluxo diario sem perder consistencia,
  mantendo semantica explicita de pagador quando necessaria.
- **Alternatives considered**: Exigir pagador sempre (mais friccao), assumir
  participante fixo por configuracao global (menos flexivel).

### 6) Deduplicacao por identificador externo

- **Decision**: Criar indice unico parcial
  `(competence_month, payer_participant_id, external_id)` quando
  `external_id IS NOT NULL`.
- **Rationale**: Implementa FR-016 com garantia em nivel de banco, protegendo
  tambem contra condicoes de corrida.
- **Alternatives considered**: Checagem apenas na aplicacao (sujeita a race),
  unicidade global de external_id (restritiva demais para meses diferentes).

### 7) Controle de limite de estorno

- **Decision**: Validar estorno em transacao com bloqueio da compra original
  (`SELECT ... FOR UPDATE`) e soma acumulada dos estornos vinculados.
- **Rationale**: Impede que estornos concorrentes ultrapassem valor original da
  compra, atendendo FR-004 com consistencia forte.
- **Alternatives considered**: Trigger complexo em banco (mais dificil de manter),
  compensacao eventual apos escrita (quebra regra de negocio).

### 7.1) Vinculo de estorno por external_id

- **Decision**: Permitir estorno por `original_purchase_external_id` como
  alternativa a `original_purchase_id`.
- **Rationale**: Reduz friccao quando o cliente nao guardou o UUID da compra e
  aproveita a unicidade ja definida de `external_id` por mes e participante.
- **Alternatives considered**: Exigir sempre `original_purchase_id` (mais seguro,
  mas pior UX), busca fuzzy por descricao/valor (ambigua e sujeita a erro).

### 8) Fechamento idempotente e imutabilidade

- **Decision**: Persistir fechamento em `monthly_closures` com unicidade por
  `competence_month`; segunda chamada retorna o mesmo snapshot salvo.
- **Rationale**: Atende FR-008 e FR-009 sem recalculo divergente e facilita
  historico consultavel por 24+ meses.
- **Alternatives considered**: Recalcular sempre em tempo real (menos previsivel
  para auditoria), permitir multiplas versoes por mes (complexidade sem ganho).

### 9) Estrategia de testes e validacao de performance

- **Decision**: Cobertura minima em tres niveis: unit (calculo/rounding),
  integration (repositorio + constraints PostgreSQL), contract (OpenAPI e
  codigos de resposta), com cenario de carga para budgets PR-001..PR-003.
- **Rationale**: Alinha com a constituicao (Tests Define Done + Performance
  Budgets) e reduz regressao em regras financeiras.
- **Alternatives considered**: Apenas testes de integracao (feedback lento),
  apenas testes manuais de carga (sem repetibilidade).

### 9.1) Busca de movimentacoes por filtros

- **Decision**: Expor endpoint de listagem `GET /v1/movements` com competencia
  mensal obrigatoria e filtros opcionais (`type`, `description`, `amount`,
  `participant_id`, `external_id`), incluindo paginacao.
- **Rationale**: Permite localizar compras antigas para registrar estorno e
  reduz dependencia de armazenamento externo do `purchase_id`.
- **Alternatives considered**: Endpoint dedicado somente para compras (menos
  flexivel), sem busca (forca cliente a armazenar todos os IDs).

### 10) Observabilidade minima

- **Decision**: Registrar logs estruturados para operacoes criticas
  (`movement_created`, `refund_rejected`, `month_closed`) com
  `participant_id`, `competence_month` e `request_id`.
- **Rationale**: Melhora depuracao e auditoria operacional sem aumentar muito a
  complexidade do dominio.
- **Alternatives considered**: Logs de texto livres (dificil correlacao),
  sem telemetria adicional (baixa rastreabilidade).
