# Templates de resposta (PT-BR)

Use estes templates imediatamente apos cada chamada de ferramenta MCP.

## Convencoes

- Responder sempre em portugues.
- Usar emoji na primeira linha.
- Ser direto: sem explicacoes longas.
- Mostrar apenas dados uteis para a acao seguinte.

## Politica obrigatoria da skill

- Apos cada chamada MCP, usar exatamente 1 template desta pagina (`sucesso`, `erro` ou `sem resultados`).
- Preencher somente os placeholders; nao alterar a ordem das linhas do template escolhido.
- Nao usar scripts externos para renderizacao; a resposta deve vir diretamente deste guia.
- Nao incluir JSON bruto, cercas de codigo, cabecalhos extras, nem texto antes/depois do template.

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

## `create_recurrence`

### Sucesso

```text
🔁 Recorrencia criada com sucesso!
- ID: {{id}}
- Descricao: {{description}}
- Valor: R$ {{amount}}
- Tipo: {{recurrence_kind}}
- Parcelas: {{installments}}
- Inicio: {{start_competence_month}}
- Fim: {{end_competence_month_or_dash}}
```

### Erro

```text
❌ Nao foi possivel criar a recorrencia.
- Codigo: {{code}}
- Mensagem: {{message}}
➡️ Acao recomendada: {{suggested_action}}
```

## `list_recurrences`

### Sucesso

```text
🗂️ Recorrencias encontradas (total: {{total}}, exibindo: {{shown}}):
{{items_bulleted}}
✅ Consulta concluida.
```

### Sem resultados

```text
🔎 Nenhuma recorrencia encontrada com os filtros informados.
```

### Erro

```text
❌ Falha ao listar recorrencias.
- Codigo: {{code}}
- Mensagem: {{message}}
➡️ Revise filtros de status/year/month e tente novamente.
```

## `edit_recurrence`

### Sucesso

```text
✏️ Recorrencia atualizada com sucesso!
- ID: {{id}}
- Descricao: {{description}}
- Valor: R$ {{amount}}
- Dia de referencia: {{reference_day}}
- Status: {{status}}
📆 Vigencia: {{start_competence_month}} ate {{end_competence_month_or_dash}}
```

### Erro

```text
❌ Nao foi possivel atualizar a recorrencia.
- Codigo: {{code}}
- Mensagem: {{message}}
➡️ Acao recomendada: {{suggested_action}}
```

## `end_recurrence`

### Sucesso

```text
🛑 Recorrencia encerrada com sucesso.
- ID: {{id}}
- Status: {{status}}
- Fim efetivo: {{end_competence_month_or_dash}}
✅ Nenhum novo lancamento sera gerado para esta regra apos o encerramento.
```

### Erro

```text
❌ Nao foi possivel encerrar a recorrencia.
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
- `recurrence_kind` e `installments`:
  - quando `end_competence_month` estiver preenchido: `Parcelada` e numero de meses entre inicio/fim (inclusivo)
  - quando `end_competence_month` vier `null`: `Fixa` e `Ilimitada`
- `items_bulleted` para `list_recurrences`: maximo de 5 itens no formato `- {id} | {status} | R$ {amount} | dia {reference_day} | {description}`
- `status` para recorrencias:
  - `active` -> `Ativa`
  - `paused` -> `Pausada`
  - `ended` -> `Encerrada`
