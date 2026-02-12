# Feature Specification: Transacoes Recorrentes no Compras Divididas

**Feature Branch**: `[001-add-recurring-transactions]`  
**Created**: 2026-02-11  
**Status**: Draft  
**Input**: User description: "Eu preciso que o compras_divididas suporte transacoes recorrentes."

## Clarifications

### Session 2026-02-11

- Q: Como o sistema deve tratar edicao concorrente da mesma recorrencia? → A: Last-write-wins: ultima edicao salva substitui a anterior sem bloqueio.
- Q: Quais campos podem ser editados apos existir primeira geracao da recorrencia? → A: Permitir editar tudo, mas bloquear competencia inicial apos primeira geracao.
- Q: Exclusao de recorrencia deve ser permitida? → A: Nao permitir exclusao; apenas encerrar/inativar.
- Q: Quando uma edicao deve passar a valer? → A: Aplicar imediatamente na competencia corrente ainda nao gerada.
- Q: Qual regra aplicar quando o dia configurado nao existir na competencia? → A: Ajustar para o ultimo dia valido da competencia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cadastrar transacao recorrente (Priority: P1)

Como pessoa usuaria do compras_divididas, quero cadastrar uma transacao recorrente para nao precisar lancar manualmente despesas fixas todo mes.

**Why this priority**: Sem cadastro de recorrencia, o objetivo principal da funcionalidade nao e atendido e continua existindo retrabalho mensal.

**Independent Test**: Cadastrar uma recorrencia valida e verificar que ela fica ativa, com proxima competencia prevista e pronta para gerar lancamentos futuros.

**Acceptance Scenarios**:

1. **Given** participantes ativos existentes, **When** a pessoa usuaria cadastra uma recorrencia mensal com descricao, valor, pagador, regra de divisao e competencia inicial, **Then** a recorrencia e salva como ativa com todas as informacoes registradas.
2. **Given** tentativa de cadastro com dados invalidos, **When** a pessoa usuaria confirma o envio, **Then** o sistema rejeita o cadastro, informa os campos inconsistentes e nao cria a recorrencia.

---

### User Story 2 - Gerar lancamentos recorrentes por competencia (Priority: P2)

Como pessoa usuaria, quero que o sistema gere automaticamente os lancamentos recorrentes de cada competencia para acelerar o fechamento mensal.

**Why this priority**: Depois de cadastrar recorrencias, o maior valor vem da geracao automatica sem duplicidade e sem esquecimentos.

**Independent Test**: Com recorrencias ativas cadastradas, executar a geracao para uma competencia e validar que os lancamentos esperados sao criados uma unica vez.

**Acceptance Scenarios**:

1. **Given** recorrencias ativas validas para uma competencia alvo, **When** a geracao de recorrencias da competencia e executada, **Then** o sistema cria lancamentos correspondentes com os mesmos dados de valor, pagador e divisao da recorrencia.
2. **Given** uma competencia ja processada anteriormente, **When** a geracao e executada novamente para a mesma competencia, **Then** o sistema nao cria lancamentos duplicados.
3. **Given** recorrencia fora do periodo de vigencia para a competencia alvo, **When** a geracao e executada, **Then** nenhum lancamento e criado para essa recorrencia.

---

### User Story 3 - Gerenciar ciclo de vida da recorrencia (Priority: P3)

Como pessoa usuaria, quero pausar, reativar, editar e encerrar recorrencias para refletir mudancas reais sem perder historico ja consolidado.

**Why this priority**: A manutencao da recorrencia reduz erros operacionais e evita exclusoes manuais recorrentes ao longo do tempo.

**Independent Test**: Alterar o estado e os dados de uma recorrencia ativa e validar que apenas geracoes futuras respeitam a mudanca, mantendo historico anterior inalterado.

**Acceptance Scenarios**:

1. **Given** uma recorrencia ativa, **When** a pessoa usuaria pausa a recorrencia antes da proxima competencia, **Then** novas geracoes deixam de ocorrer enquanto o status permanecer pausado.
2. **Given** uma recorrencia ativa com lancamentos ja gerados, **When** a pessoa usuaria altera valor ou descricao, **Then** apenas lancamentos gerados apos a alteracao usam os novos dados.
3. **Given** uma recorrencia pausada, **When** a pessoa usuaria reativa a recorrencia, **Then** a geracao volta a ocorrer a partir da proxima competencia elegivel.

### Edge Cases

- Quando o dia configurado da recorrencia nao existe na competencia (ex.: dia 31 em fevereiro), o sistema deve ajustar para o ultimo dia valido da competencia.
- Quando participantes vinculados a recorrencia ficam inativos antes de uma nova geracao, o sistema deve bloquear a geracao dessa recorrencia e informar a necessidade de ajuste.
- Quando uma geracao de competencia e interrompida no meio do processo, a nova execucao deve retomar com seguranca sem criar duplicidades.
- Quando uma recorrencia e encerrada no mesmo mes da competencia alvo, o sistema deve respeitar a vigencia configurada e gerar apenas se ainda estiver dentro do periodo valido.
- Quando duas edicoes concorrentes da mesma recorrencia forem confirmadas com sucesso, a ultima persistencia deve prevalecer como estado final.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir criar uma recorrencia com, no minimo, descricao, valor, pagador, regra de divisao, periodicidade mensal, competencia inicial e data de referencia no mes.
- **FR-002**: O sistema DEVE validar regras de cadastro antes de salvar, incluindo valor maior que zero, participantes validos, competencia inicial obrigatoria e periodo final nao anterior ao inicial.
- **FR-003**: O sistema DEVE permitir definir vigencia da recorrencia com opcao de sem data final ou com competencia final explicita.
- **FR-004**: O sistema DEVE disponibilizar a listagem de recorrencias com status (ativa, pausada, encerrada), proxima competencia prevista e ultimo processamento.
- **FR-005**: O sistema DEVE gerar lancamentos de recorrencia para uma competencia alvo preservando os dados de negocio definidos na recorrencia.
- **FR-006**: O sistema DEVE garantir idempotencia por recorrencia e competencia, criando no maximo um lancamento gerado por combinacao.
- **FR-007**: O sistema DEVE permitir pausar, reativar, editar e encerrar recorrencias sem remover lancamentos historicos ja gerados.
- **FR-008**: O sistema DEVE aplicar alteracoes de recorrencia para competencias ainda nao geradas (incluindo a competencia corrente quando ainda nao processada), mantendo inalterados os lancamentos ja criados anteriormente.
- **FR-009**: O sistema DEVE registrar historico de eventos relevantes de recorrencia (criacao, alteracao, pausa, reativacao, encerramento e geracao) com data e responsavel pela acao.
- **FR-010**: O sistema DEVE apresentar mensagens de validacao e erro claras, acionaveis e consistentes com o padrao atual do produto.
- **FR-011**: O sistema DEVE permitir executar a geracao de recorrencias sob demanda para uma competencia especifica e informar quantidade de itens gerados, ignorados e bloqueados.
- **FR-012**: O sistema DEVE impedir geracao de recorrencia quando houver inconsistencias de dados obrigatorios, orientando como corrigir antes de nova tentativa.
- **FR-013**: O sistema DEVE adotar last-write-wins para edicao concorrente de recorrencia, considerando valida a ultima alteracao persistida com sucesso.
- **FR-014**: O sistema DEVE permitir edicao de todos os campos da recorrencia, exceto competencia inicial apos a primeira geracao concluida para essa recorrencia.
- **FR-015**: O sistema NAO DEVE permitir exclusao de recorrencia; a descontinuacao DEVE ocorrer apenas por encerramento ou inativacao com preservacao de historico.
- **FR-016**: O sistema DEVE ajustar a data de referencia para o ultimo dia valido da competencia quando o dia configurado da recorrencia nao existir no mes alvo.

### Key Entities *(include if feature involves data)*

- **Recorrencia**: Regra que representa uma despesa repetitiva com dados de descricao, valor, pagador, divisao, periodicidade, vigencia e status.
- **Ocorrencia de Recorrencia**: Resultado da aplicacao de uma recorrencia em uma competencia especifica, incluindo referencia a recorrencia de origem e status de processamento.
- **Evento de Recorrencia**: Registro historico de mudancas de estado e de geracao, usado para auditoria funcional e rastreabilidade.

### Assumptions

- O escopo inicial cobre recorrencias mensais, pois o produto e orientado a conciliacao por competencia mensal.
- O valor e a regra de divisao da recorrencia permanecem fixos ate que a pessoa usuaria edite a recorrencia.
- Lancamentos ja gerados podem ser ajustados manualmente sem alterar retroativamente a regra de recorrencia.

### Dependencies

- Participantes e regras de divisao ja existentes no compras_divididas devem estar disponiveis e validos.
- O fluxo atual de consolidacao por competencia deve continuar sendo a base para fechamento mensal.

## User Experience Consistency *(mandatory)*

- **UX-001**: A terminologia exibida deve usar de forma consistente os termos "recorrencia", "competencia" e "lancamento" em todos os pontos de contato.
- **UX-002**: Validacoes devem informar claramente o problema, o campo afetado e a acao de correcao recomendada, mantendo o mesmo tom usado hoje no produto.
- **UX-003**: A diferenca entre "editar recorrencia" (impacta futuro) e "editar lancamento gerado" (impacta item pontual) deve ser explicita para evitar confusao.
- **UX-004**: Estados de recorrencia (ativa, pausada, encerrada) devem ser visiveis e compreensiveis sem necessidade de treinamento adicional.
- **UX-005**: Qualquer desvio intencional de comportamento atual deve ser documentado previamente com criterio de aceitacao de negocio.

## Performance Requirements *(mandatory)*

- **PR-001**: Cadastro, edicao e alteracao de status de recorrencia devem ser concluidos em ate 2 segundos em 95% das tentativas sob carga de ate 100 usuarios ativos simultaneamente.
- **PR-002**: A geracao de recorrencias para uma competencia com ate 1.000 recorrencias elegiveis deve concluir em ate 30 segundos com taxa de falha menor que 1%.
- **PR-003**: A consulta de uma competencia com ate 2.000 lancamentos totais deve apresentar os dados completos em ate 2 segundos em 95% das tentativas.
- **PR-004**: O desempenho deve ser validado antes de liberacao por cenarios de teste representando cadastro, consulta e processamento mensal em volume realista.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pelo menos 95% das despesas recorrentes cadastradas sao geradas automaticamente na competencia correta sem lancamento manual adicional.
- **SC-002**: O tempo medio para preparar o fechamento mensal cai no minimo 40% apos dois ciclos mensais de uso da funcionalidade.
- **SC-003**: Pelo menos 90% das pessoas usuarias conseguem cadastrar sua primeira recorrencia com sucesso na primeira tentativa em menos de 2 minutos.
- **SC-004**: O volume de ocorrencias de "despesa fixa esquecida" reduz em pelo menos 60% nos tres primeiros meses apos a adocao.
