# Hotfix 12.0.2 — Inclusão de Refeição e Bebida no mesmo Consumo

## 1. Contexto

Projeto **Gestão Empresarial Rental Retros**, em produção parcial no Render, com fluxo oficial:

```text
ChatGPT/Squad → planeja a missão/hotfix
Codex → implementa em branch separada
Pull Request → revisão antes de entrar na main
Fábio → testa, aprova e faz merge/deploy
```

Antes de iniciar a Missão 12.1 — Departamento Pessoal > Documentos > Holerites, foi identificado mais um ajuste necessário em produção no módulo:

```text
Departamento Pessoal
└── Pedido de Refeições
    └── Pedidos
        └── Inclusão de Consumo
```

Atualmente, o usuário cria um Pedido de Refeição e, dentro do pedido, inclui o consumo de cada colaborador.

Fluxo atual:

```text
1. Criar pedido
2. Incluir consumo
3. Selecionar colaborador
4. Selecionar prato/refeição
5. Preencher observação, se houver
6. Cadastrar
7. Incluir consumo novamente
8. Selecionar o mesmo colaborador
9. Selecionar bebida
10. Cadastrar
```

Esse fluxo gera retrabalho quando o mesmo colaborador terá refeição e bebida no mesmo pedido.

Fluxo desejado:

```text
1. Criar pedido
2. Incluir consumo
3. Selecionar colaborador
4. Selecionar prato/refeição
5. Selecionar bebida
6. Preencher observação, se houver
7. Cadastrar
8. Incluir consumo novamente apenas para o próximo colaborador
```

---

## 2. Objetivo do hotfix

Permitir que, na mesma sessão/formulário de **Incluir Consumo**, o usuário consiga registrar para o mesmo colaborador:

```text
Colaborador
Refeição/prato
Bebida
Observação opcional
```

evitando que o usuário precise lançar o mesmo colaborador duas vezes quando houver prato e bebida.

---

## 3. Análise da Squad

### 3.1 Agente de Desenvolvimento / Arquitetura

O ajuste é operacional e melhora o fluxo já existente do módulo Pedido de Refeições.

A alteração deve ser tratada como hotfix por afetar uma tela já em produção.

A arquitetura precisa preservar o modelo atual de consumo e os cálculos já existentes.

Antes de alterar, o Codex deve analisar como o sistema hoje registra:

```text
consumo de refeição
consumo de bebida
itens do pedido
quantidades
valores
total geral
relatórios
PDF
mensagem WhatsApp
```

A solução deve preferir reaproveitar a estrutura atual.

Possíveis abordagens aceitáveis:

```text
Opção A:
O formulário recebe colaborador, prato e bebida; no backend, cria dois registros de consumo separados para o mesmo colaborador, um para refeição e outro para bebida, preservando a estrutura atual.

Opção B:
O formulário recebe colaborador, prato e bebida; no backend, cria um consumo principal e seus itens vinculados, se essa já for a estrutura real do projeto.
```

A decisão técnica deve respeitar o modelo real existente no projeto.

Importante:

- Não quebrar pedidos já cadastrados.
- Não alterar histórico.
- Não alterar cálculo financeiro.
- Não alterar relatório/PDF, salvo se necessário para continuar compatível.
- Não alterar mensagem WhatsApp além do necessário para refletir os registros corretamente.
- Não criar migration, salvo se o Codex comprovar que é indispensável. A preferência é não criar migration.

Aprovado pelo Agente de Desenvolvimento / Arquitetura.

---

### 3.2 Agente de Design / Experiência do Usuário

A experiência desejada é reduzir retrabalho.

Na tela de **Incluir Consumo**, o usuário deve ver um formulário simples:

```text
Colaborador
Refeição / Prato
Bebida
Observação
Botão Cadastrar
```

A bebida deve ser opcional, assim como a observação.

A refeição/prato também pode ser opcional se o colaborador consumir apenas bebida, desde que o sistema valide que pelo menos um item foi selecionado.

Regra de UX recomendada:

```text
O usuário deve selecionar pelo menos uma opção:
- Refeição/prato
- Bebida
```

Mensagem amigável:

```text
Selecione uma refeição ou uma bebida para cadastrar o consumo.
```

Após salvar, o usuário retorna para a tela do pedido/detalhes do pedido, onde poderá incluir o próximo colaborador.

Aprovado pelo Agente de Design / Experiência do Usuário.

---

### 3.3 Agente de Código / Programação

A implementação deve localizar:

```text
rota de incluir consumo
template/formulário de incluir consumo
validação do POST
consulta de pratos/refeições
consulta de bebidas
cálculo do total do pedido
listagem de consumos do pedido
```

Arquivos prováveis:

```text
app/departamento_pessoal/pedido_refeicoes/routes.py
app/templates/departamento_pessoal/pedido_refeicoes/pedido_detalhes.html
app/templates/departamento_pessoal/pedido_refeicoes/consumo_form.html
app/templates/departamento_pessoal/pedido_refeicoes/*.html
```

O Codex deve verificar os nomes reais dos templates.

Regras técnicas:

- A tela deve carregar pratos/refeições e bebidas disponíveis conforme restaurante selecionado no pedido.
- O formulário deve permitir selecionar refeição e bebida na mesma inclusão.
- Bebida deve ser opcional.
- Refeição deve ser opcional somente se bebida tiver sido selecionada.
- Pelo menos um item deve ser obrigatório.
- Observação permanece opcional.
- O preço deve continuar vindo do cadastro/cardápio, sem edição manual.
- O total do pedido deve continuar correto.
- A mensagem WhatsApp deve continuar correta após o Hotfix 12.0.1, mostrando quantidades por item e total geral.

Aprovado pelo Agente de Código / Programação.

---

### 3.4 Agente de Revisão / Qualidade

O hotfix deve ser testado em cenários operacionais reais.

Testes obrigatórios:

```text
1. Incluir consumo com apenas refeição.
2. Incluir consumo com apenas bebida.
3. Incluir consumo com refeição e bebida no mesmo formulário.
4. Incluir consumo com observação.
5. Tentar cadastrar sem refeição e sem bebida.
6. Confirmar mensagem de validação amigável.
7. Confirmar que o total do pedido soma corretamente.
8. Confirmar que o resumo do pedido/listagem mostra corretamente os itens.
9. Confirmar que o envio WhatsApp continua correto.
10. Confirmar que o WhatsApp não voltou a exibir valores por item.
11. Confirmar que o total geral permanece no WhatsApp.
12. Confirmar que relatório/PDF continuam funcionando.
13. Confirmar que fechamento e reenvio continuam funcionando.
14. Confirmar `/status` 200.
15. Confirmar que nenhuma migration foi criada, salvo justificativa técnica expressa.
```

Aprovado pelo Agente de Revisão / Qualidade.

---

## 4. Decisão consolidada da Squad

A Squad aprova a abertura do:

```text
Hotfix 12.0.2 — Inclusão de Refeição e Bebida no mesmo Consumo
```

com a seguinte regra:

```text
Ao clicar em Incluir Consumo, o usuário deve conseguir selecionar colaborador, refeição/prato, bebida e observação no mesmo formulário, cadastrando o consumo do colaborador de uma só vez.
```

---

## 5. Escopo aprovado

Entram neste hotfix:

- ajustar a tela/formulário de inclusão de consumo;
- permitir selecionar refeição/prato e bebida no mesmo formulário;
- permitir cadastrar apenas refeição;
- permitir cadastrar apenas bebida;
- permitir cadastrar refeição + bebida;
- manter observação opcional;
- validar que pelo menos refeição ou bebida seja selecionada;
- preservar cálculos do pedido;
- preservar fechamento/reenvio;
- preservar WhatsApp;
- preservar relatório/PDF.

Não entram neste hotfix:

- alteração estrutural ampla do módulo Pedido de Refeições;
- criação de novo módulo;
- alteração em colaboradores;
- alteração em restaurantes/cardápio fora do necessário para consulta;
- alteração em permissões;
- alteração em Documentos/Holerites;
- integração com Google Drive;
- migration, salvo se tecnicamente indispensável e justificado.

---

## 6. Regra funcional detalhada

### 6.1 Formulário desejado

A tela de inclusão de consumo deve conter:

```text
Colaborador
Refeição / Prato
Bebida
Observação
Botão Cadastrar
```

### 6.2 Refeição / Prato

Deve listar apenas itens do tipo refeição/prato disponíveis para o restaurante do pedido, conforme regra atual do cardápio.

Deve ser opcional se uma bebida for selecionada.

### 6.3 Bebida

Deve listar apenas itens do tipo bebida disponíveis para o restaurante do pedido, conforme regra atual do cardápio.

Deve ser opcional se uma refeição/prato for selecionada.

### 6.4 Validação mínima

Não permitir cadastro quando ambos estiverem vazios:

```text
Refeição/prato vazio
Bebida vazia
```

Mensagem sugerida:

```text
Selecione uma refeição ou uma bebida para cadastrar o consumo.
```

### 6.5 Observação

A observação continua opcional.

Se houver refeição e bebida na mesma inclusão, a observação pode ser aplicada ao consumo do colaborador ou ao item principal, conforme estrutura real do sistema.

O Codex deve preservar a lógica atual de observação da forma mais compatível possível.

---

## 7. Regras de cálculo

O preço continua vindo do cardápio.

Não permitir alteração manual de preço no formulário.

O total do pedido deve considerar corretamente:

```text
valor da refeição selecionada
valor da bebida selecionada
soma dos itens
total geral do pedido
```

Não alterar regras financeiras já existentes.

---

## 8. Regras do WhatsApp

Preservar o ajuste do Hotfix 12.0.1:

```text
No resumo enviado ao restaurante via WhatsApp:
- mostrar quantidades por item;
- não mostrar valores por item;
- manter total geral no final.
```

Após este hotfix, se o colaborador tiver refeição e bebida cadastradas no mesmo formulário, ambos devem aparecer corretamente no pedido/mensagem, conforme estrutura atual.

---

## 9. Branch e PR

Criar ou utilizar a branch:

```text
hotfix-12-0-2-consumo-refeicao-bebida
```

Ao finalizar, abrir Pull Request para:

```text
main
```

---

## 10. Arquivos prováveis

Verificar a estrutura real antes de alterar.

Arquivos prováveis:

```text
app/departamento_pessoal/pedido_refeicoes/routes.py
app/templates/departamento_pessoal/pedido_refeicoes/pedido_detalhes.html
app/templates/departamento_pessoal/pedido_refeicoes/consumo_form.html
app/templates/departamento_pessoal/pedido_refeicoes/*.html
```

---

## 11. Não alterar

Não alterar:

- `models.py`, salvo se tecnicamente indispensável e justificado;
- migrations, salvo se tecnicamente indispensável e justificado;
- permissões;
- colaboradores;
- restaurantes;
- cardápio, exceto consulta já existente;
- relatório/PDF, salvo ajuste mínimo de compatibilidade se necessário;
- cálculo financeiro do cardápio;
- Hotfix 12.0.1;
- Missão 12.1 Documentos/Holerites.

---

## 12. Critérios de aceite

O hotfix será considerado concluído quando:

1. A tela de Incluir Consumo permitir selecionar colaborador, refeição/prato, bebida e observação no mesmo formulário.
2. For possível cadastrar apenas refeição.
3. For possível cadastrar apenas bebida.
4. For possível cadastrar refeição e bebida juntos.
5. Não for possível cadastrar consumo sem refeição e sem bebida.
6. Mensagem de validação for amigável.
7. Total do pedido continuar correto.
8. Listagem/detalhe do pedido continuar correto.
9. Envio WhatsApp continuar funcionando.
10. WhatsApp não exibir valores por item.
11. WhatsApp manter total geral no final.
12. Relatório/PDF continuarem funcionando.
13. Fechamento/reenvio continuarem funcionando.
14. `/status` continuar 200.
15. Nenhuma migration ser criada, salvo justificativa técnica.
16. PR ser aberto antes do merge.

---

## 13. Testes locais

Testar localmente:

1. Criar ou abrir pedido de refeição.
2. Clicar em Incluir Consumo.
3. Selecionar colaborador + refeição.
4. Cadastrar.
5. Selecionar colaborador + bebida.
6. Cadastrar.
7. Selecionar colaborador + refeição + bebida.
8. Cadastrar.
9. Tentar cadastrar sem refeição e sem bebida.
10. Confirmar mensagem de validação.
11. Confirmar total do pedido.
12. Gerar WhatsApp.
13. Confirmar que WhatsApp não mostra valores por item.
14. Confirmar que WhatsApp mostra total geral.
15. Testar fechamento.
16. Testar reenvio.
17. Testar relatório/PDF.
18. Testar `/status`.

---

## 14. Deploy e produção

Após PR aprovado, merge e deploy no Render:

1. Aguardar deploy automático.
2. Não executar migration, salvo se o Codex justificar criação de migration.
3. Testar em produção:
   - inclusão apenas refeição;
   - inclusão apenas bebida;
   - inclusão refeição + bebida;
   - WhatsApp;
   - total geral;
   - fechamento/reenvio.

---

## 15. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos criados.
2. Arquivos alterados.
3. Se houve ou não migration.
4. Qual regra/formulário foi alterado.
5. Como refeição e bebida passaram a ser tratadas no mesmo consumo.
6. Testes executados.
7. Confirmação de que o total do pedido permanece correto.
8. Confirmação de que WhatsApp permanece sem valores por item.
9. Confirmação de que relatório/PDF não foram quebrados.
10. Link do Pull Request.
