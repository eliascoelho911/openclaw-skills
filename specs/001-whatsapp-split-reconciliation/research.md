# Research - compras-divididas

## Contexto

Este documento consolida as decisoes de Fase 0 para a feature de fechamento mensal de compras compartilhadas com app binario Python, Skill OpenClaw, PostgreSQL e inferencia via OpenAIClient.

## Decisao 1 - Arquitetura do binario + Skill

- Decision: usar arquitetura hexagonal (ports and adapters) com um nucleo de dominio deterministico compartilhado por dois adaptadores de entrada: binario `compras-divididas` e Skill OpenClaw.
- Rationale:
  - Mantem regras financeiras criticas fora do LLM, melhorando determinismo (FR-012).
  - Reutiliza o mesmo fluxo para CLI e Skill, evitando divergencia de comportamento.
  - Facilita testes unitarios e integracao com infraestrutura isolada.
- Alternatives considered:
  - Monolito procedural simples: entrega rapida, mas com maior acoplamento e risco de regressao.
  - Microservicos/event-driven: mais escalavel, porem complexo demais para o escopo atual.
  - LLM-first para tudo: flexivel, mas fraco em auditabilidade e reproducibilidade.

## Decisao 2 - Modelagem e persistencia no PostgreSQL

- Decision: modelar fluxo append-only com `process_run`, `raw_message`, `extracted_entry` e `monthly_closure`; armazenar dinheiro em centavos (`BIGINT`) e usar constraints para bilateralidade, idempotencia e dedupe.
- Rationale:
  - Evita erros de ponto flutuante e garante precisao de centavos em BRL.
  - Preserva trilha de auditoria completa sem expurgo (FR-019).
  - Permite reprocessamento sem dupla contagem com chaves de unicidade e hash de entrada.
- Alternatives considered:
  - `NUMERIC(14,2)`: legivel em SQL, mas com mais custo computacional e maior risco de mistura de escala.
  - Modelo mutavel por upsert direto: simples, mas perde historico e explicabilidade.
  - Event sourcing completo com ledger: robusto, porem complexo para reconciliacao bilateral inicial.

## Decisao 3 - Inference com OpenAIClient

- Decision: usar OpenAIClient com structured output em JSON Schema estrito (`strict: true`), `temperature=0`, classificacao por mensagem, validacao deterministica pos-LLM e fallback para invalido quando houver inconsistencias.
- Rationale:
  - Reduz variacao de formato e melhora confiabilidade do parser.
  - Mantem regras de negocio (estorno, dedupe, periodo, bilateralidade) em codigo testavel.
  - Aumenta auditabilidade com versionamento de prompt/schema e armazenamento de trace.
- Alternatives considered:
  - Regex-only: altamente deterministico, mas cobertura menor para linguagem livre.
  - Resposta textual sem schema: implementacao rapida, mas fragil para parsing.
  - Fine-tuning dedicado: potencial ganho de recall, mas custo e operacao maiores.

## Decisao 4 - Estrategia de performance e confiabilidade

- Decision: validar com dois trilhos complementares: benchmark automatizado fim a fim (datasets D100/D500/D2000 + reprocessamento de 50 alteracoes) e suite de confiabilidade deterministica com golden datasets.
- Rationale:
  - Cobre diretamente PR-001..PR-004 com metricas objetivas (p95 e max).
  - Detecta regressao de classificacao, dedupe e saldo antes de release.
  - Fornece evidencia de reproducibilidade em reexecucoes identicas.
- Alternatives considered:
  - Cronometragem manual: facil, mas nao reprodutivel.
  - Apenas teste em staging/producao: realista, mas caro e tardio.
  - So microbenchmarks unitarios: insuficiente para fluxo ponta a ponta.

## Resolucao de NEEDS CLARIFICATION

- Formato da aplicacao binaria: definido para CLI Python empacotado (`compras-divididas`) com adaptador de Skill.
- Integracao Skill/OpenClaw: definida por orquestracao no mesmo nucleo de dominio, sem duplicar regra de negocio.
- Estrategia de inferencia: definida com OpenAIClient + JSON Schema estrito + validacao deterministica.
- Persistencia e historico: definido PostgreSQL append-only com retencao completa.
- Validacao de performance: definido plano de benchmark e criterios de aprovacao por dataset.

Todas as clarificacoes tecnicas da Fase 0 estao resolvidas.
