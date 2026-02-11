# Feature Specification: Reconciliação Mensal de Compras Compartilhadas

**Feature Branch**: `[002-whatsapp-split-reconciliation]`  
**Created**: 2026-02-11  
**Status**: Draft  
**Input**: User description: "Eu tenho um grupo no whatsapp com a minha esposa onde enviamos ao decorrer dos dias as compras que estamos dividindo entre nós dois. O problema é que a contabilidade no final do mês é ainda manual e eu gostaria de automatizar isso. Eu preciso de uma API na qual possamos registrar cada uma das nossas transações, estornos e etc. Ao final de cada mês, quero gerar um relatório contendo um resumo dos gastos mensal e quem deve transferir quanto ao outro."

## Clarifications

### Session 2026-02-11

- Q: Qual abordagem de autenticação para a v1 da API? → A: Sem autenticação na v1; cada registro deve informar o participante responsável.
- Q: Enquanto o mês está aberto, movimentações podem ser editadas/excluídas? → A: Não; correções devem ser feitas via estorno e novo lançamento.
- Q: Qual estratégia de arredondamento deve ser usada nos cálculos? → A: Arredondar cada movimentação para 2 casas antes de acumular os saldos.
- Q: Como tratar duplicidade com mesmo identificador externo? → A: Retornar erro de duplicidade para mesmo identificador externo e participante no mesmo mês.
- Q: Qual fuso horário define o mês de competência? → A: America/Sao_Paulo para todos os cálculos mensais.
- Q: O campo de data da movimentação é obrigatório? → A: Não; quando ausente, usar o timestamp atual do registro (America/Sao_Paulo).
- Q: O pagador deve ser sempre informado? → A: Não; quando ausente, usar o mesmo participante de `requested_by`.
- Q: Como obter `purchase_id` para registrar estorno quando ele não foi guardado? → A: A API deve permitir busca de movimentações por filtros (mês, tipo, descrição, valor e identificadores).
- Q: O estorno pode referenciar compra por identificador externo? → A: Sim; além de `original_purchase_id`, aceitar `original_purchase_external_id`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar compras e estornos (Priority: P1)

Como participante do casal, quero registrar compras e estornos no momento em que acontecem para manter o histórico financeiro correto durante o mês.

**Why this priority**: Sem registro confiável das movimentações, não existe base para fechar o mês e calcular quem deve transferir para quem.

**Independent Test**: Pode ser testado de forma independente cadastrando compras e estornos de um único mês e verificando se o extrato mensal reflete os valores líquidos corretamente.

**Acceptance Scenarios**:

1. **Given** um mês aberto com dois participantes ativos, **When** um participante registra uma compra com valor, descrição e participante solicitante (com data/pagador opcionais), **Then** a compra é armazenada e passa a compor o saldo mensal compartilhado usando valores padrão quando faltantes.
2. **Given** uma compra já registrada, **When** um participante registra um estorno vinculado a essa compra, **Then** o valor líquido da compra é reduzido e o saldo mensal é recalculado.
3. **Given** uma compra previamente registrada com `external_id`, **When** um participante registra um estorno informando `original_purchase_external_id`, **Then** o sistema resolve a compra original e aplica o estorno sem exigir `purchase_id` explícito.
4. **Given** uma tentativa de registro com valor igual ou menor que zero, **When** o envio é realizado, **Then** o sistema rejeita o lançamento com mensagem de validação clara.

---

### User Story 2 - Acompanhar saldo mensal parcial (Priority: P2)

Como participante do casal, quero consultar o resumo parcial do mês para saber em tempo real o total gasto, o saldo de cada pessoa e a projeção de transferência.

**Why this priority**: Esse acompanhamento reduz surpresas no fechamento e permite corrigir erros de lançamento antes do fim do mês.

**Independent Test**: Pode ser testado de forma independente consultando o resumo de um mês com e sem movimentações e verificando os totais e saldos apresentados.

**Acceptance Scenarios**:

1. **Given** um mês com compras e estornos registrados, **When** o resumo mensal é solicitado, **Then** o sistema retorna total bruto, total de estornos, total líquido, participação individual e saldo entre os participantes.
2. **Given** um mês sem movimentações, **When** o resumo mensal é solicitado, **Then** o sistema retorna valores zerados e indica que não há transferência pendente.
3. **Given** um participante que precisa localizar uma compra do mês, **When** consulta movimentações com filtros (mês, tipo, descrição e valor), **Then** o sistema retorna a lista paginada com os `id`s necessários para ações futuras.

---

### User Story 3 - Fechar mês com relatório final (Priority: P3)

Como participante do casal, quero fechar o mês e gerar um relatório final para ter uma instrução objetiva de quem deve transferir quanto ao outro.

**Why this priority**: O fechamento automatiza a etapa hoje manual, reduz erro humano e formaliza o resultado mensal em um documento único.

**Independent Test**: Pode ser testado de forma independente fechando um mês com movimentações conhecidas e verificando se o relatório final contém os valores esperados e a instrução de transferência.

**Acceptance Scenarios**:

1. **Given** um mês aberto com movimentações válidas, **When** o fechamento mensal é solicitado, **Then** o sistema gera um relatório final com totais consolidados e a instrução de transferência entre os participantes.
2. **Given** um mês já fechado, **When** um novo fechamento é solicitado, **Then** o sistema retorna o mesmo resultado final sem duplicar ou alterar os valores.

---

### Edge Cases

- Compra ou estorno com data fora do mês consultado deve aparecer apenas no mês correspondente.
- Estornos acumulados não podem ultrapassar o valor original da compra vinculada.
- Para estorno por `original_purchase_external_id`, a compra original deve ser encontrada de forma única no contexto aplicável; ausência deve gerar erro de validação.
- Fechamento de mês sem movimentações deve gerar relatório com saldo zero e sem transferência.
- Quando os dois participantes terminam o mês com contribuição líquida equivalente, o relatório deve indicar que não há valor a transferir.
- Após o fechamento do mês, novos lançamentos para aquele período devem ser rejeitados para preservar a consistência do relatório.
- Tentativas duplicadas de registro da mesma movimentação (mesmo identificador externo, quando informado) devem ser tratadas para evitar contagem em dobro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST manter exatamente dois participantes ativos por contexto de divisão mensal.
- **FR-002**: O sistema MUST permitir registrar movimentações financeiras dos tipos "compra" e "estorno" com descrição, valor e participante solicitante; data e participante pagador MAY ser omitidos na requisição.
- **FR-003**: O sistema MUST validar obrigatoriedade dos campos mínimos (`tipo`, `valor`, `descrição`, `requested_by`) e rejeitar movimentações com valor menor ou igual a zero.
- **FR-004**: O sistema MUST exigir que cada estorno esteja vinculado a uma compra existente e limitar a soma dos estornos ao valor original da compra.
- **FR-004**: O sistema MUST exigir que cada estorno esteja vinculado a uma compra existente por `original_purchase_id` ou `original_purchase_external_id`, e limitar a soma dos estornos ao valor original da compra.
- **FR-005**: O sistema MUST calcular automaticamente, a cada movimentação, o impacto no saldo compartilhado considerando divisão igualitária entre os dois participantes.
- **FR-006**: O sistema MUST disponibilizar resumo mensal parcial com total bruto de compras, total de estornos, total líquido, contribuição individual e saldo entre participantes.
- **FR-006**: O sistema MUST disponibilizar resumo mensal parcial com total bruto de compras, total de estornos, total líquido, contribuição individual e saldo entre participantes.
- **FR-006A**: O sistema MUST disponibilizar consulta de movimentações por filtros (competência mensal obrigatória, e filtros opcionais por tipo, descrição, valor, participante e identificadores) retornando lista paginada com `id` de cada movimentação.
- **FR-007**: O sistema MUST permitir fechamento mensal e gerar relatório final contendo período, movimentações consolidadas, total líquido do mês e instrução explícita de transferência.
- **FR-008**: O sistema MUST tornar o mês imutável após o fechamento, impedindo inclusão, alteração ou exclusão de movimentações daquele período.
- **FR-009**: O sistema MUST retornar sempre o mesmo relatório final quando o fechamento do mesmo mês for solicitado novamente.
- **FR-010**: O sistema MUST manter histórico consultável de relatórios mensais fechados por, no mínimo, 24 meses.
- **FR-011**: O sistema MUST registrar trilha de auditoria mínima para cada movimentação e fechamento (identificador do participante informado na requisição e timestamp).
- **FR-012**: O sistema MUST exibir valores monetários em Real brasileiro com duas casas decimais em todos os resumos e relatórios.
- **FR-013**: A API v1 MUST operar sem autenticação/autorização; ao registrar movimentações e solicitar fechamento, a requisição MUST informar explicitamente o identificador do participante responsável.
- **FR-014**: O sistema MUST adotar histórico append-only para movimentações: não permitir edição nem exclusão, inclusive com mês aberto; correções MUST ocorrer por estorno vinculado e novo lançamento, quando necessário.
- **FR-015**: O sistema MUST arredondar cada movimentação para duas casas decimais (BRL) no momento do registro e utilizar esses valores arredondados para todos os cálculos acumulados de resumo e fechamento.
- **FR-016**: O sistema MUST rejeitar como duplicada qualquer nova movimentação que repita o mesmo identificador externo para o mesmo participante dentro do mesmo mês de competência.
- **FR-017**: O sistema MUST determinar o mês de competência pela data/hora da movimentação no fuso fixo America/Sao_Paulo, usando o timestamp atual do registro quando a data não for informada.
- **FR-018**: Quando `payer_participant_id` não for informado, o sistema MUST assumir automaticamente o mesmo valor de `requested_by_participant_id`.
- **FR-019**: Ao receber estorno com `original_purchase_external_id`, o sistema MUST resolver a compra original por contexto de competência mensal e participante pagador efetivo; se não encontrar correspondência única, MUST rejeitar com erro claro.

### Key Entities *(include if feature involves data)*

- **Participante**: Pessoa que compõe a divisão de despesas do casal; atributos principais incluem identificador, nome e status ativo.
- **Movimentação Financeira**: Registro de compra ou estorno; inclui identificador, tipo, valor, descrição, participante solicitante, data da transação (informada ou inferida no registro), participante pagador (informado ou inferido de `requested_by`) e referência opcional para deduplicação, com unicidade por (mês de competência, participante, identificador externo) quando informada.
- **Filtro de Movimentações**: Conjunto de critérios para localizar lançamentos (`ano`, `mês`, `tipo`, `descrição`, `valor`, `participante`, `external_id`) com paginação.
- **Vínculo de Estorno**: Relação entre estorno e compra original para controle de limite de estorno acumulado.
- **Resumo Mensal**: Visão consolidada de um mês em andamento com totais bruto, estornos, líquido, contribuição individual e saldo entre participantes.
- **Relatório de Fechamento Mensal**: Resultado final de um mês fechado com registro congelado dos cálculos, indicação de devedor/credor e valor de transferência.

### Assumptions and Dependencies

- **ASSUMPTION-001**: A divisão de despesas entre os dois participantes é sempre 50/50 para este escopo inicial.
- **ASSUMPTION-002**: A moeda operacional é Real brasileiro (BRL).
- **ASSUMPTION-003**: O mês de competência é definido pela data da movimentação no fuso fixo America/Sao_Paulo; quando a data não for enviada, usa-se o timestamp de registro.
- **ASSUMPTION-004**: A v1 é utilizada em contexto de confiança entre os dois participantes, aceitando identidade declarada na requisição.
- **DEPENDENCY-001**: Os dois participantes precisam estar previamente cadastrados e ativos para registrar movimentações e fechar mês.
- **DEPENDENCY-002**: Para evitar duplicidade, integrações externas devem enviar identificador de referência quando disponível.

## User Experience Consistency *(mandatory)*

- **UX-001**: A terminologia exibida ao usuário MUST ser consistente em todos os fluxos: "compra", "estorno", "fechamento", "saldo" e "transferência".
- **UX-002**: Mensagens de validação e erro MUST indicar causa do problema e ação de correção em linguagem simples.
- **UX-003**: O cálculo e os rótulos de saldo MUST permanecer idênticos entre resumo parcial e relatório final, evitando interpretações conflitantes.
- **UX-004**: Datas e valores monetários MUST seguir formato consistente em todas as respostas voltadas ao usuário.

## Performance Requirements *(mandatory)*

- **PR-001**: O registro de compra ou estorno MUST ser confirmado em até 2 segundos para 95% das solicitações, sob carga de até 20 lançamentos por minuto.
- **PR-002**: A geração de resumo mensal parcial MUST concluir em até 3 segundos para meses com até 5.000 movimentações.
- **PR-003**: A geração de relatório de fechamento mensal MUST concluir em até 5 segundos para meses com até 5.000 movimentações.
- **PR-004**: A validação de desempenho MUST ser executada antes da liberação com testes de carga representativos dos cenários de registro, consulta de resumo e fechamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos meses fechados, o relatório final informa claramente quem deve transferir, para quem e o valor exato.
- **SC-002**: Os participantes conseguem registrar uma compra ou estorno em até 30 segundos, em média, do início do preenchimento até a confirmação.
- **SC-003**: Para meses com até 200 movimentações, o processo completo de fechamento e conferência do relatório final é concluído em até 5 minutos por um participante.
- **SC-004**: Em auditoria de amostra de 3 meses consecutivos, a divergência entre cálculo manual e cálculo do sistema é de no máximo R$0,01 por mês.
