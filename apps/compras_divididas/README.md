# compras-divididas

Aplicacao para fechamento mensal de compras compartilhadas entre duas pessoas,
com o mesmo nucleo de dominio exposto por CLI e Skill.

## Visao geral

- Entrada: lote de mensagens (autor, texto, data opcional) para um periodo mes/ano.
- Pipeline: classificacao hibrida (regras + fallback LLM), validacao de estorno e dedupe
  em janela de 5 minutos.
- Saida: resumo executivo (pagador, recebedor, valor) e detalhamento auditavel.

## Arquitetura

- `src/compras_divididas/domain/`: regras de negocio puras (dinheiro BRL, dedupe, estorno).
- `src/compras_divididas/application/`: casos de uso e schemas de classificacao.
- `src/compras_divididas/infrastructure/`: settings, adaptadores LLM e persistencia.
- `src/compras_divididas/api/`: handlers tipo endpoint para criar e consultar fechamento.
- `src/compras_divididas/cli.py`: comando `close-month` para processar JSON local.
- `src/compras_divididas/skill.py`: comando `fechar <json_payload>` para OpenClaw Skill.

## Fluxo operacional

1. Carregar payload de fechamento (`period`, `participants`, `messages`).
2. Classificar cada mensagem em `valid`, `invalid`, `ignored` ou `deduplicated`.
3. Somar apenas lancamentos validos incluidos no calculo.
4. Calcular repasse bilateral e montar relatorio com contagens e detalhes.
5. Persistir fechamento e disponibilizar consultas por id e ultimo por periodo.

## Comandos principais

```bash
uv run python -m compras_divididas.cli close-month --input examples/feb-2026.json
```

Skill (texto de comando):

```text
fechar {"period":{"year":2026,"month":2},"participants":[...],"messages":[...]}
```

## Validacao

```bash
uv run ruff check apps/compras_divididas tests/test_compras_divididas_integration.py
uv run mypy apps/compras_divididas/src apps/compras_divididas/tests tests/test_compras_divididas_integration.py
uv run pytest apps/compras_divididas/tests tests/test_compras_divididas_integration.py
```

Benchmarks (D100/D500/D2000/reprocess_50):

```bash
uv run pytest apps/compras_divididas/tests/performance/test_reconciliation_benchmarks.py
```
