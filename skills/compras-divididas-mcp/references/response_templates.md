# Templates de resposta (PT-BR)

Use estes templates imediatamente apos cada chamada de ferramenta MCP.

## Convencoes

- Responder sempre em portugues.
- Usar emoji na primeira linha.
- Ser direto: sem explicacoes longas.
- Mostrar apenas dados uteis para a acao seguinte.

## `list_participants`

### Sucesso

```text
👥 Participantes ativos:
- {{id_1}} - {{display_name_1}}
- {{id_2}} - {{display_name_2}}
✅ IDs mapeados para as proximas operacoes.
```

### Erro

```text
❌ Nao consegui listar os participantes.
- Codigo: {{code}}
- Mensagem: {{message}}
➡️ Verifique conexao MCP/API e tente novamente.
```

## `list_movements`

### Sucesso

```text
📚 Movimentacoes de {{competence_month_label}} (total: {{total}}, exibindo: {{shown}}):
{{items_bulleted}}
✅ Consulta concluida.
```

### Sem resultados

```text
🔎 Nenhuma movimentacao encontrada com os filtros informados.
```

### Erro

```text
❌ Falha ao listar movimentacoes.
- Codigo: {{code}}
- Mensagem: {{message}}
➡️ Revise year/month e filtros (amount no formato "0.00").
```

## `create_movement`

### Sucesso

```text
🧾 Movimentacao registrada com sucesso!
- Tipo: {{type_label}}
- ID: {{id}}
- Valor: R$ {{amount}}
- Competencia: {{competence_month}}
- Pagador: {{payer_participant_id}}
🔁 external_id: {{external_id_or_dash}}
```

### Erro

```text
❌ Nao foi possivel registrar a movimentacao.
- Codigo: {{code}}
- Mensagem: {{message}}
➡️ Acao recomendada: {{suggested_action}}
```

## `get_monthly_summary`

### Sucesso

```text
📊 Resumo mensal {{competence_month}}
- {{generation_note}}
- Bruto: R$ {{total_gross}}
- Estornos: R$ {{total_refunds}}
- Liquido: R$ {{total_net}}
- {{participant_1}}: pagou R$ {{paid_1}} | saldo {{net_1}}
- {{participant_2}}: pagou R$ {{paid_2}} | saldo {{net_2}}
💸 Transferencia: {{transfer_sentence}}
```

### Erro

```text
❌ Nao consegui gerar o resumo mensal.
- Codigo: {{code}}
- Mensagem: {{message}}
➡️ Revise year/month e tente novamente.
```

## `get_monthly_report`

### Sucesso

```text
📄 Relatorio consolidado {{competence_month}}
- {{generation_note}}
- Bruto: R$ {{total_gross}}
- Estornos: R$ {{total_refunds}}
- Liquido: R$ {{total_net}}
💸 Transferencia: {{transfer_sentence}}
✅ Fechamento pronto para compartilhar.
```

### Erro

```text
❌ Nao consegui gerar o relatorio mensal.
- Codigo: {{code}}
- Mensagem: {{message}}
➡️ Revise year/month e tente novamente.
```

## Regras de preenchimento rapido

- `type_label`: `Compra` para `purchase`; `Estorno` para `refund`.
- `external_id_or_dash`: mostrar `-` quando vier `null` ou vazio.
- `items_bulleted`: maximo de 5 itens; se passar disso, adicionar `...`.
- `transfer_sentence`:
  - se `amount == "0.00"` ou IDs nulos: `Sem transferencia no mes.`
  - caso contrario: `R$ {amount} de {debtor} para {creditor}.`
- `generation_note`:
  - quando `auto_generate=true`: `Inclui geracao automatica de recorrencias desta competencia.`
  - caso contrario: `Considera somente movimentacoes ja registradas.`
