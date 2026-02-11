# Feature Specification: Automacao de Fechamento de Compras Compartilhadas

**Feature Branch**: `[001-whatsapp-split-reconciliation]`  
**Created**: 2026-02-11  
**Status**: Draft  
**Input**: User description: "Eu tenho um grupo no whatsapp com a minha esposa onde enviamos ao decorrer dos dias as compras que estamos dividindo entre nos dois. Ex: Eu -> \"Mercado R$20\". R$20 e o valor ja dividido entre nos dois. Ou seja, eu pago 20 reais e ela tambem. O problema e que a contabilidade no final do mes e ainda manual e eu gostaria de automatizar isso com uma skill no Openclaw"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fechar o mes automaticamente (Priority: P1)

Como participante de um casal que divide compras, quero consolidar automaticamente os lancamentos do mes para saber rapidamente quem deve pagar quanto para quem.

**Why this priority**: Resolve diretamente a dor principal (contabilidade mensal manual) e entrega valor imediato mesmo sem recursos adicionais.

**Independent Test**: Pode ser testada isoladamente ao fornecer um conjunto de lancamentos validos de um mes e verificar se o saldo final e o pagador/recebedor estao corretos.

**Acceptance Scenarios**:

1. **Given** um conjunto de lancamentos validos de ambos os participantes no mes selecionado, **When** o fechamento mensal e solicitado, **Then** o sistema retorna total por participante, saldo liquido e instrucao de pagamento final.
2. **Given** lancamentos validos apenas de um participante no mes selecionado, **When** o fechamento mensal e solicitado, **Then** o sistema informa que o outro participante deve o valor total acumulado desse mes.
3. **Given** ausencia de lancamentos validos no periodo, **When** o fechamento mensal e solicitado, **Then** o sistema retorna saldo zero e informa que nao ha repasse pendente.

---

### User Story 2 - Interpretar mensagens do WhatsApp com seguranca (Priority: P2)

Como usuario, quero que a skill identifique automaticamente mensagens de compra em formato livre e separe mensagens validas, invalidas e irrelevantes para evitar erro no fechamento.

**Why this priority**: Evita calculos incorretos e reduz retrabalho de conferencia, mantendo confianca no resultado.

**Independent Test**: Pode ser testada isoladamente com um lote misto de mensagens (compras, conversa comum e entradas mal formatadas) e verificacao da classificacao correta de cada item.

**Acceptance Scenarios**:

1. **Given** uma mensagem no formato "Mercado R$20" com autor identificado, **When** o sistema processa o lote, **Then** o item e classificado como lancamento valido com descricao e valor monetario reconhecidos.
2. **Given** uma mensagem sem valor monetario identificavel, **When** o sistema processa o lote, **Then** o item e marcado como invalido com motivo explicito e nao entra no calculo.
3. **Given** uma mensagem de conversa sem contexto de compra, **When** o sistema processa o lote, **Then** o item e ignorado e contabilizado no resumo de mensagens nao financeiras.

---

### User Story 3 - Conferir o fechamento com transparencia (Priority: P3)

Como usuario, quero receber um extrato detalhado dos lancamentos considerados para validar rapidamente o resultado e corrigir divergencias no proximo processamento.

**Why this priority**: Garante auditabilidade e aumenta confianca, especialmente nos primeiros meses de uso.

**Independent Test**: Pode ser testada isoladamente ao gerar um fechamento e conferir se todos os itens validos aparecem com os dados necessarios para auditoria.

**Acceptance Scenarios**:

1. **Given** um fechamento mensal gerado, **When** o usuario visualiza o relatorio detalhado, **Then** cada lancamento valido aparece com data, autor, descricao e valor utilizado no calculo.
2. **Given** que existem itens invalidos no periodo, **When** o usuario consulta o fechamento, **Then** o relatorio apresenta a lista desses itens com os respectivos motivos de rejeicao.
3. **Given** um conjunto de mensagens corrigido e reenviado para processamento, **When** um novo fechamento e gerado, **Then** o saldo final reflete exclusivamente os dados do novo conjunto.

### Edge Cases

- Mensagens duplicadas no lote (ex.: exportacao reenviada parcialmente) devem ser sinalizadas para evitar dupla contagem.
- Valores com formatos diferentes (`R$20`, `R$ 20`, `20`, `20,50`, `20.50`) devem ser tratados de forma consistente.
- Lancamentos com valor zero, negativo ou nao numerico devem ser rejeitados com motivo claro.
- Mensagens sem autor identificavel nao devem entrar no calculo financeiro.
- Mensagens na virada do mes devem respeitar rigorosamente o periodo selecionado para o fechamento.
- Entradas de participantes fora do casal nao devem ser consideradas no saldo bilateral.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE aceitar um lote de mensagens contendo, no minimo, autor, conteudo textual e data da mensagem.
- **FR-002**: O sistema DEVE permitir selecionar o periodo de fechamento por mes/ano e considerar apenas mensagens dentro desse intervalo.
- **FR-003**: O sistema DEVE identificar lancamentos financeiros em texto livre quando houver valor monetario em reais.
- **FR-004**: O sistema DEVE interpretar cada valor informado como cota individual ja dividida entre duas pessoas.
- **FR-005**: Para cada lancamento valido, o sistema DEVE creditar o valor ao autor do lancamento como valor adiantado ao outro participante.
- **FR-006**: O sistema DEVE calcular o saldo liquido mensal com base na diferenca entre os creditos acumulados dos dois participantes.
- **FR-007**: O sistema DEVE informar claramente quem deve pagar, quem recebe e o valor final da transferencia do mes.
- **FR-008**: O sistema DEVE gerar um resumo mensal com total por participante, saldo final, quantidade de itens validos, invalidos e ignorados.
- **FR-009**: O sistema DEVE listar os lancamentos validos com data, autor, descricao e valor considerado.
- **FR-010**: O sistema DEVE listar entradas invalidas com motivo explicito de rejeicao e excluir essas entradas do calculo.
- **FR-011**: O sistema DEVE ignorar mensagens nao financeiras e reportar a quantidade total ignorada no fechamento.
- **FR-012**: O sistema DEVE produzir o mesmo resultado sempre que o mesmo conjunto de dados e o mesmo periodo forem processados novamente.
- **FR-013**: O sistema DEVE suportar reconciliacao apenas entre dois participantes e sinalizar erro quando houver tentativa de fechamento com mais de dois participantes.
- **FR-014**: O sistema DEVE apresentar todos os valores monetarios com precisao de centavos e formato padronizado em BRL.

### Assumptions & Dependencies

- O fluxo inicial considera que as mensagens do WhatsApp sao fornecidas pelo usuario (copiadas ou exportadas), sem dependencia de sincronizacao automatica.
- O valor registrado em cada mensagem representa a cota individual ja dividida entre os dois participantes.
- O fechamento e bilateral (somente usuario e esposa), sem rateio para terceiros.
- A moeda de referencia para todos os calculos e o real brasileiro (BRL).
- O lote fornecido contem informacoes confiaveis de autor e data para cada mensagem candidata.

### Key Entities *(include if feature involves data)*

- **Participante**: Pessoa envolvida no fechamento mensal (ex.: usuario e esposa), com identificador e nome exibivel.
- **MensagemBruta**: Registro textual original com autor, data e conteudo antes da validacao financeira.
- **LancamentoCompartilhado**: Mensagem validada como compra dividida, contendo autor, descricao, valor da cota individual e referencia temporal.
- **FechamentoMensal**: Resultado consolidado do periodo com totais por participante, saldo liquido e instrucao de repasse.
- **InconsistenciaDeLancamento**: Item nao processado financeiramente, com classificacao (invalido ou ignorado) e motivo.

## User Experience Consistency *(mandatory)*

- **UX-001**: A terminologia exibida ao usuario DEVE ser consistente em todo o fluxo (`lancamento`, `saldo`, `fechamento`, `repasse`).
- **UX-002**: O resultado DEVE sempre apresentar primeiro o resumo executivo (quem paga quanto para quem) e depois o detalhamento.
- **UX-003**: Mensagens de erro/validacao DEVEM indicar causa e proximo passo recomendado para correcao.
- **UX-004**: A formatacao monetaria DEVE seguir padrao BRL legivel para usuario final em todas as telas/saidas da skill.

## Performance Requirements *(mandatory)*

- **PR-001**: O fechamento de ate 500 mensagens no periodo DEVE ser concluido em ate 10 segundos em execucao normal.
- **PR-002**: O fechamento de ate 2.000 mensagens no periodo DEVE ser concluido em ate 30 segundos sem interromper o fluxo do usuario.
- **PR-003**: Um reprocessamento com alteracao de ate 50 mensagens DEVE ser concluido em ate 5 segundos.
- **PR-004**: A validacao de performance DEVE ser registrada com medicao cronometrada em cenarios de 100, 500 e 2.000 mensagens antes da liberacao.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em base de teste com resultado esperado conhecido, o saldo final mensal calculado bate com o esperado em 100% dos casos.
- **SC-002**: O usuario conclui o fechamento mensal completo (entrada dos dados ate resultado final) em menos de 5 minutos na maioria dos meses.
- **SC-003**: Pelo menos 90% dos lancamentos validos em formatos comuns de WhatsApp sao reconhecidos sem ajuste manual.
- **SC-004**: O tempo gasto com contabilidade mensal manual e reduzido em pelo menos 80% apos adocao da skill.
