# Ambiente local isolado — BR Mobilidade

O ambiente usa `instance/br_mobilidade_teste.db`, separado do banco local
principal, e abre a aplicação em `http://127.0.0.1:5001`.

Iniciar ou reutilizar o ambiente:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar_ambiente_teste_br_mobilidade.ps1
```

Recriar o banco de teste a partir do banco local principal:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar_ambiente_teste_br_mobilidade.ps1 -RecriarBanco
```

O segundo comando substitui todos os dados previamente cadastrados no ambiente
de teste. O banco principal não é alterado.

O cabeçalho vermelho identifica claramente o ambiente isolado. A integração é
ativada apenas nesse processo e cada envio ainda exige confirmação manual na
tela do pedido.
