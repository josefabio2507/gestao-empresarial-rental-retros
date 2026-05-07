# Hotfix 12.0.1 — WhatsApp sem valores por item no Pedido de Refeição

## 1. Contexto

Projeto **Gestão Empresarial Rental Retros**, em produção parcial no Render, com fluxo oficial:

```text
ChatGPT/Squad → planeja a missão/hotfix
Codex → implementa em branch separada
Pull Request → revisão antes de entrar na main
Fábio → testa, aprova e faz merge/deploy
```

Antes de iniciar a Missão 12.1 — Documentos > Holerites, foi identificado um ajuste necessário em produção no módulo:

```text
Departamento Pessoal
└── Pedido de Refeições
    └── Envio de pedido via WhatsApp
```

Atualmente, o texto enviado ao restaurante via WhatsApp exibe no resumo do pedido os itens de refeições e bebidas com quantidade e valor.

Exemplo atual:

```text
🍽️ Refeições
· MARMITEX GRANDE | Qtd: 1 | Valor: R$ 25,50
```

A regra desejada é remover os valores por item no resumo enviado ao restaurante, mantendo apenas as quantidades.

Exemplo desejado:

```text
🍽️ Refeições
· MARMITEX GRANDE | Qtd: 1
```

O valor total geral do pedido deve continuar aparecendo no final da mensagem.

Exemplo:

```text
💰 Total geral: R$ 25,50
```

---

## 2. Objetivo do hotfix

Ajustar exclusivamente a montagem da mensagem enviada pelo WhatsApp ao restaurante para que:

```text
Refeições e bebidas exibam apenas quantidade por item.
O valor total geral do pedido permaneça no final.
```

---

## 3. Análise da Squad

### 3.1 Agente de Desenvolvimento / Arquitetura

O ajuste é pontual e deve ser tratado como hotfix, pois afeta um módulo já em produção.

A alteração deve ficar restrita à função, rota, service ou helper responsável pela montagem da mensagem de WhatsApp.

Não deve alterar:

- banco de dados;
- cálculo interno do pedido;
- fechamento do pedido;
- reenvio;
- relatório;
- PDF;
- permissões;
- migrations;
- models.py.

Aprovado pelo Agente de Desenvolvimento / Arquitetura.

---

### 3.2 Agente de Design / Experiência do Usuário

A mensagem enviada ao restaurante deve permanecer clara e objetiva.

O restaurante precisa receber:

- identificação do pedido;
- data;
- equipe;
- restaurante;
- consumo por colaborador;
- resumo por item com quantidade;
- total geral do pedido.

A remoção do valor por item no resumo deixa o pedido mais limpo para operação, sem perder o total geral necessário para controle.

Aprovado pelo Agente de Design / Experiência do Usuário.

---

### 3.3 Agente de Código / Programação

A implementação deve localizar a montagem da mensagem enviada ao WhatsApp.

Arquivos prováveis:

```text
app/departamento_pessoal/pedido_refeicoes/routes.py
```

ou eventual service/helper usado para montar o texto do WhatsApp, se existir.

A alteração esperada é remover da linha de resumo dos itens a parte:

```text
| Valor: R$ ...
```

Mantendo:

```text
| Qtd: ...
```

A lógica de cálculo do total geral deve permanecer intacta.

Aprovado pelo Agente de Código / Programação.

---

### 3.4 Agente de Revisão / Qualidade

O hotfix deve ser validado com pedido contendo:

- apenas refeição;
- apenas bebida;
- refeição e bebida;
- mais de um colaborador;
- total geral diferente de zero.

Também deve ser validado que:

- o total geral continua aparecendo;
- os relatórios não foram afetados;
- o PDF não foi afetado;
- o fechamento/reenvio do pedido não foi afetado;
- `/status` continua 200;
- nenhuma migration foi criada.

Aprovado pelo Agente de Revisão / Qualidade.

---

## 4. Decisão consolidada da Squad

A Squad aprova a abertura do:

```text
Hotfix 12.0.1 — WhatsApp sem valores por item no Pedido de Refeição
```

com a seguinte regra:

```text
No resumo do pedido enviado via WhatsApp, remover valores dos itens de refeições e bebidas, mantendo apenas quantidades. O total geral do pedido deve permanecer no final da mensagem.
```

---

## 5. Escopo aprovado

Entram neste hotfix:

- ajustar o texto enviado ao WhatsApp;
- remover valor por item no resumo de refeições;
- remover valor por item no resumo de bebidas;
- manter quantidade por item;
- manter total geral no final;
- preservar cálculo interno do pedido.

Não entram neste hotfix:

- alteração de banco de dados;
- migration;
- alteração de permissões;
- alteração em PDF;
- alteração em relatórios;
- alteração na regra de fechamento;
- alteração na regra de reenvio;
- alteração em cardápio;
- alteração em restaurantes;
- alteração na estrutura de Pedido de Refeições;
- alteração em Documentos/Holerites.

---

## 6. Regra funcional

### 6.1 Resumo de refeições

Antes:

```text
· MARMITEX GRANDE | Qtd: 1 | Valor: R$ 25,50
```

Depois:

```text
· MARMITEX GRANDE | Qtd: 1
```

### 6.2 Resumo de bebidas

Antes:

```text
· COCA-COLA | Qtd: 2 | Valor: R$ 12,00
```

Depois:

```text
· COCA-COLA | Qtd: 2
```

### 6.3 Total geral

Deve permanecer:

```text
💰 Total geral: R$ 25,50
```

---

## 7. Branch e PR

Criar ou utilizar a branch:

```text
hotfix-12-0-1-whatsapp-sem-valores-itens
```

Ao finalizar, abrir Pull Request para:

```text
main
```

---

## 8. Arquivos prováveis

Verificar a estrutura real antes de alterar.

Arquivos prováveis:

```text
app/departamento_pessoal/pedido_refeicoes/routes.py
```

ou service/helper responsável pela montagem da mensagem de WhatsApp.

---

## 9. Não alterar

Não alterar:

- `models.py`;
- migrations;
- permissões;
- relatórios;
- PDF;
- cardápio;
- restaurantes;
- colaboradores;
- fechamento do pedido;
- reenvio;
- cálculo financeiro;
- tela de Holerites;
- Missão 12.1.

---

## 10. Critérios de aceite

O hotfix será considerado concluído quando:

1. Mensagem de WhatsApp não mostrar valor por item em Refeições.
2. Mensagem de WhatsApp não mostrar valor por item em Bebidas.
3. Quantidade dos itens continuar aparecendo.
4. Total geral do pedido continuar aparecendo no final.
5. Cálculo interno do pedido não for alterado.
6. Relatórios não forem alterados.
7. PDF não for alterado.
8. Fechamento/reenvio do pedido não for alterado.
9. `/status` continuar 200.
10. Nenhuma migration for criada.
11. PR for aberto antes do merge.

---

## 11. Testes locais

Testar localmente:

1. Criar ou usar pedido com refeição.
2. Gerar mensagem de WhatsApp.
3. Confirmar que a refeição aparece com quantidade e sem valor por item.
4. Criar ou usar pedido com bebida.
5. Gerar mensagem de WhatsApp.
6. Confirmar que a bebida aparece com quantidade e sem valor por item.
7. Confirmar que o total geral aparece no final.
8. Confirmar que o pedido fecha/reenvia normalmente.
9. Confirmar que relatório/PDF não foram alterados.
10. Confirmar `/status` 200.

---

## 12. Deploy e produção

Após PR aprovado, merge e deploy no Render:

1. Aguardar deploy automático.
2. Testar em produção um pedido de refeição.
3. Gerar envio por WhatsApp.
4. Confirmar que o resumo não exibe valores por item.
5. Confirmar que o total geral permanece.

Não executar migration, pois este hotfix não deve criar migration.

---

## 13. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos criados.
2. Arquivos alterados.
3. Se houve ou não migration.
4. Qual trecho/regra foi alterado.
5. Testes executados.
6. Confirmação de que os valores por item foram removidos.
7. Confirmação de que o total geral permanece.
8. Confirmação de que relatórios/PDF não foram alterados.
9. Link do Pull Request.
