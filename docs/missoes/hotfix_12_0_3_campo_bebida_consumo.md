# Hotfix 12.0.3 — Campo separado de Bebida na tela Incluir Consumo

## 1. Contexto

Projeto **Gestão Empresarial Rental Retros**, em produção parcial no Render, com fluxo oficial:

```text
ChatGPT/Squad → planeja a missão/hotfix
Codex → implementa em branch separada
Pull Request → revisão antes de entrar na main
Fábio → testa, aprova e faz merge/deploy
```

Após o Hotfix 12.0.2, foi identificado que a tela de **Incluir Consumo** do módulo Pedido de Refeições ainda não atende à metodologia desejada.

A tela atual continua trabalhando com um único campo de seleção de item do cardápio:

```text
Item do cardápio
```

Esse campo permite escolher refeição ou bebida, mas não permite selecionar, no mesmo formulário, uma refeição e uma bebida para o mesmo colaborador.

O que se deseja é uma alteração funcional clara na tela:

```text
Colaborador
Refeição / Prato
Bebida
Quantidade da refeição
Quantidade da bebida
Observação opcional
Salvar consumo
```

Assim, o usuário consegue lançar o consumo completo do colaborador em uma única inclusão, sem precisar selecionar o mesmo colaborador duas vezes.

---

## 2. Problema atual

Fluxo ainda inadequado:

```text
1. Usuário clica em Incluir Consumo.
2. Seleciona o colaborador.
3. Seleciona um único item no campo "Item do cardápio".
4. Se selecionar refeição, não consegue selecionar bebida na mesma tela.
5. Para lançar bebida, precisa salvar e depois incluir consumo novamente para o mesmo colaborador.
```

Isso continua gerando retrabalho operacional.

---

## 3. Objetivo do hotfix

Corrigir a tela de **Incluir Consumo** para exibir campos separados:

```text
Colaborador
Refeição / Prato
Bebida
Quantidade da refeição
Quantidade da bebida
Observação
```

O usuário deve conseguir salvar, em uma única ação, a refeição e a bebida consumidas pelo colaborador.

---

## 4. Análise da Squad

### 4.1 Agente de Desenvolvimento / Arquitetura

O Hotfix 12.0.2 não entregou a mudança funcional esperada. A alteração precisa ser mais explícita: o formulário deve ter **dois seletores separados**, um para refeição/prato e outro para bebida.

A arquitetura recomendada é preservar a estrutura atual do banco e dos registros de consumo, evitando migration.

A tela deve separar visualmente:

```text
Refeição / Prato
Bebida
```

No backend, ao salvar:

```text
Se refeição foi selecionada:
    criar ou registrar o consumo da refeição.

Se bebida foi selecionada:
    criar ou registrar o consumo da bebida.

Se refeição e bebida foram selecionadas:
    criar os dois registros/itens para o mesmo colaborador no mesmo POST.
```

A solução deve respeitar o modelo real existente. Se hoje o sistema grava um consumo por item, então o backend deve criar dois registros quando houver refeição + bebida. Se o sistema já trabalhar com itens vinculados, deve criar dois itens vinculados ao consumo do colaborador.

O hotfix não deve alterar a regra estrutural do módulo, não deve criar migration e não deve alterar histórico já existente.

Aprovado pelo Agente de Desenvolvimento / Arquitetura.

---

### 4.2 Agente de Design / Experiência do Usuário

A tela deve deixar claro para o usuário que ele pode selecionar refeição e bebida no mesmo lançamento.

Layout desejado:

```text
Colaborador

Refeição / Prato
Quantidade da refeição

Bebida
Quantidade da bebida

Observação
Salvar consumo
```

Regras de usabilidade:

- Refeição deve ser opcional se uma bebida for selecionada.
- Bebida deve ser opcional se uma refeição for selecionada.
- Pelo menos um dos dois campos deve ser obrigatório.
- Quantidade padrão deve ser 1.
- Quantidade da refeição pode ficar desabilitada ou ignorada quando nenhuma refeição for selecionada.
- Quantidade da bebida pode ficar desabilitada ou ignorada quando nenhuma bebida for selecionada.
- Observação continua opcional.

Mensagem amigável quando nada for selecionado:

```text
Selecione uma refeição ou uma bebida para cadastrar o consumo.
```

Aprovado pelo Agente de Design / Experiência do Usuário.

---

### 4.3 Agente de Código / Programação

O Codex deve corrigir a implementação anterior.

O formulário não deve ter apenas um campo genérico `Item do cardápio`.

Devem existir campos separados, por exemplo:

```text
refeicao_id
bebida_id
quantidade_refeicao
quantidade_bebida
observacao
```

Os nomes devem respeitar o padrão real do projeto.

O backend deve:

1. Receber o colaborador selecionado.
2. Receber a refeição selecionada, se houver.
3. Receber a bebida selecionada, se houver.
4. Validar que pelo menos refeição ou bebida foi selecionada.
5. Criar o registro da refeição, se selecionada.
6. Criar o registro da bebida, se selecionada.
7. Aplicar a observação conforme a estrutura atual.
8. Recalcular/atualizar total do pedido conforme regra já existente.
9. Redirecionar de volta para os detalhes do pedido.

A consulta dos itens deve separar:

```text
Itens do tipo refeição/prato
Itens do tipo bebida
```

e deve respeitar o restaurante do pedido.

Aprovado pelo Agente de Código / Programação.

---

### 4.4 Agente de Revisão / Qualidade

Este hotfix deve ser tratado como correção do Hotfix 12.0.2.

Testes obrigatórios:

```text
1. A tela de Incluir Consumo exibe campo separado para Refeição / Prato.
2. A tela de Incluir Consumo exibe campo separado para Bebida.
3. É possível salvar apenas refeição.
4. É possível salvar apenas bebida.
5. É possível salvar refeição + bebida no mesmo lançamento.
6. Ao salvar refeição + bebida, o colaborador aparece com os dois consumos no pedido.
7. Não é possível salvar sem refeição e sem bebida.
8. Quantidades são aplicadas corretamente.
9. Total do pedido permanece correto.
10. WhatsApp continua sem valores por item.
11. WhatsApp mantém total geral.
12. Relatório/PDF continuam funcionando.
13. Fechamento/reenvio continuam funcionando.
14. Nenhuma migration é criada.
15. /status continua 200.
```

Aprovado pelo Agente de Revisão / Qualidade.

---

## 5. Decisão consolidada da Squad

A Squad aprova a abertura do:

```text
Hotfix 12.0.3 — Campo separado de Bebida na tela Incluir Consumo
```

Regra consolidada:

```text
A tela de Incluir Consumo deve ter campos separados para Refeição/Prato e Bebida, permitindo cadastrar ambos para o mesmo colaborador no mesmo lançamento.
```

---

## 6. Escopo aprovado

Entram neste hotfix:

- alterar a tela de Incluir Consumo;
- substituir ou complementar o campo genérico "Item do cardápio";
- criar campo específico para Refeição / Prato;
- criar campo específico para Bebida;
- permitir quantidade da refeição;
- permitir quantidade da bebida;
- validar que pelo menos refeição ou bebida seja selecionada;
- salvar refeição e bebida no mesmo POST;
- preservar cálculo do pedido;
- preservar WhatsApp sem valores por item;
- preservar total geral no WhatsApp;
- preservar relatório/PDF;
- preservar fechamento/reenvio.

Não entram neste hotfix:

- alteração de banco de dados;
- migration;
- alteração estrutural ampla do Pedido de Refeições;
- alteração em permissões;
- alteração em Documentos/Holerites;
- alteração em Google Drive;
- alteração na Missão 12.1.

---

## 7. Regra funcional detalhada

### 7.1 Campos obrigatórios/opcionais

Obrigatório:

```text
Colaborador
```

Opcional individualmente:

```text
Refeição / Prato
Bebida
Observação
```

Regra de validação:

```text
Pelo menos Refeição / Prato ou Bebida deve ser selecionado.
```

### 7.2 Quantidades

Quantidade da refeição:

```text
Padrão: 1
Aplicável somente se refeição/prato estiver selecionado.
```

Quantidade da bebida:

```text
Padrão: 1
Aplicável somente se bebida estiver selecionada.
```

### 7.3 Salvamento

Se apenas refeição for selecionada:

```text
Salvar consumo da refeição para o colaborador.
```

Se apenas bebida for selecionada:

```text
Salvar consumo da bebida para o colaborador.
```

Se refeição e bebida forem selecionadas:

```text
Salvar os dois consumos/itens para o mesmo colaborador no mesmo envio do formulário.
```

---

## 8. Regras do WhatsApp

Preservar o Hotfix 12.0.1:

```text
No resumo enviado ao restaurante via WhatsApp:
- mostrar quantidades por item;
- não mostrar valores por item;
- manter total geral no final.
```

---

## 9. Branch e PR

Criar ou utilizar a branch:

```text
hotfix-12-0-3-campo-bebida-consumo
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
app/templates/departamento_pessoal/pedido_refeicoes/consumo_form.html
app/templates/departamento_pessoal/pedido_refeicoes/*.html
```

---

## 11. Não alterar

Não alterar:

- models.py;
- migrations;
- permissões;
- Documentos/Holerites;
- Missão 12.1;
- regras de relatório/PDF, salvo ajuste mínimo de compatibilidade;
- fechamento/reenvio;
- Hotfix 12.0.1.

---

## 12. Critérios de aceite

O hotfix será considerado concluído quando:

1. A tela Incluir Consumo exibir campo separado para Refeição / Prato.
2. A tela Incluir Consumo exibir campo separado para Bebida.
3. For possível cadastrar apenas refeição.
4. For possível cadastrar apenas bebida.
5. For possível cadastrar refeição + bebida no mesmo lançamento.
6. Não for possível cadastrar sem refeição e sem bebida.
7. Mensagem de validação for amigável.
8. Quantidade da refeição funcionar.
9. Quantidade da bebida funcionar.
10. Total do pedido continuar correto.
11. WhatsApp continuar sem valores por item.
12. WhatsApp manter total geral no final.
13. Relatório/PDF continuarem funcionando.
14. Fechamento/reenvio continuarem funcionando.
15. Nenhuma migration ser criada.
16. /status continuar 200.
17. PR ser aberto antes do merge.

---

## 13. Testes locais

Testar localmente:

1. Abrir Pedido de Refeição.
2. Clicar em Incluir Consumo.
3. Confirmar que existem dois campos separados:
   - Refeição / Prato
   - Bebida
4. Salvar apenas refeição.
5. Salvar apenas bebida.
6. Salvar refeição + bebida.
7. Tentar salvar sem os dois campos.
8. Confirmar mensagem de validação.
9. Confirmar total do pedido.
10. Gerar WhatsApp.
11. Confirmar WhatsApp sem valores por item.
12. Confirmar total geral no WhatsApp.
13. Testar fechamento.
14. Testar reenvio.
15. Testar relatório/PDF.
16. Testar /status.

---

## 14. Deploy e produção

Após PR aprovado, merge e deploy no Render:

1. Aguardar deploy automático.
2. Não executar migration.
3. Testar em produção:
   - apenas refeição;
   - apenas bebida;
   - refeição + bebida;
   - WhatsApp;
   - total geral;
   - fechamento/reenvio.

---

## 15. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos alterados.
2. Confirmação de que não houve migration.
3. Como a tela foi alterada.
4. Como os campos de refeição e bebida foram separados.
5. Como o backend salva refeição + bebida no mesmo POST.
6. Testes executados.
7. Confirmação de que o WhatsApp permanece sem valores por item.
8. Confirmação de que total geral permanece correto.
9. Link do Pull Request.
