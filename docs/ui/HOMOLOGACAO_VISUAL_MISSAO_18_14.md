# Missão 18.14 — Homologação Visual Local

Status: em homologação local; aguardando conferência e aprovação explícita do responsável.

## Objetivo

Validar em ambiente local a versão modernizada antes de qualquer preparação para produção.

## Roteiro de aceite

| Área | Verificações | Situação |
| --- | --- | --- |
| Navegação global | Sidebar, topo, usuário, saída e menu mobile. | Pendente |
| Financeiro | Contas a Pagar, Contas a Receber, Fluxo de Caixa, filtros, tabelas e ações. | Pendente |
| Departamento Pessoal | Colaboradores, documentos, vale-transporte e telas de apoio. | Pendente |
| Pedido de Refeição | Pedidos, consumo, cardápio, restaurantes, resumo e ação de WhatsApp. | Pendente |
| Suprimentos e Fiscal | Cadastros, compras, tabelas extensas, XML, DANFE e telas fiscais. | Pendente |
| Operação | Veículos/equipamentos, abastecimentos, custos, multas e impostos. | Pendente |
| Administração | Usuários, permissões, cargos, equipes e logs. | Pendente |
| Responsividade | Desktop, tablet e mobile; menus, filtros, cartões e rolagem de tabelas. | Pendente |
| Regressão visual | Não há sobreposição, corte de conteúdo, botões inacessíveis ou contraste insuficiente. | Pendente |

## Critérios de aprovação

- Nenhuma regra de negócio, rota, permissão, formulário ou integração apresenta alteração de comportamento.
- A navegação e as ações principais continuam acessíveis em tela grande e pequena.
- Tabelas extensas continuam utilizáveis por rolagem horizontal em dispositivos menores.
- A identidade visual se mantém consistente entre os módulos modernizados.

## Contexto de testes locais

A missão de paridade local foi concluída antes desta etapa. O ambiente isolado com Python 3.13 executou a suíte automatizada com cache limpo, sem falhas registradas (481 testes aprovados). A produção permanece funcional e não foi alterada nesta missão.

Para a conferência visual, a instância local está disponível em `http://127.0.0.1:5003`.

## Próximo passo

Após a conferência local, registrar a aprovação explícita para encerrar esta homologação e, somente então, iniciar a preparação de publicação em produção (Missão 18.15).
