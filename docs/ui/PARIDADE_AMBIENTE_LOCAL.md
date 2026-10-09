# Paridade do Ambiente Local

## Objetivo

Estabelecer um ambiente local previsível para validar o Sistema Rental Retros sem alterar a versão em produção.

## Ambiente isolado

- Python local: 3.13.15, compatível com a imagem definida no `Dockerfile`.
- Ambiente virtual: `.venv-paridade` na raiz deste worktree.
- Dependências: instaladas a partir de `requirements.txt` exclusivamente no ambiente isolado.
- Banco de testes: SQLite em memória (`sqlite:///:memory:`).

## Ajustes de confiabilidade dos testes

- A fixture fiscal passou a incluir `modFrete`, campo esperado pelo gerador de DANFE.
- As validações de Operação agora usam datas relativas para respeitar o vínculo vigente do motorista.
- As expectativas de navegação e de mensagens foram alinhadas ao fluxo atual da aplicação.
- A criação de requisição de compra passou a rejeitar equipe inativa.
- Os objetos simulados de WhatsApp foram atualizados com os campos usados no cálculo atual de propostas.

## Limites conhecidos

O `requirements.txt` não fixa versões. Portanto, a reprodução exata das bibliotecas de produção ainda depende de um arquivo de versões gerado a partir do ambiente de produção. Esta missão não altera dependências nem a infraestrutura de produção.

## Execução local

No worktree da paridade, execute:

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'
.\.venv-paridade\Scripts\python.exe -m pytest -q
```

Os avisos legados de SQLAlchemy são conhecidos e não representam falhas de execução.
