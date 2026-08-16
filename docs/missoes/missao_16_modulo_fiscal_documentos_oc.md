# Missao 16 - Modulo Fiscal / Documentos Fiscais + vinculo com O.C.

## Escopo implementado

- Central Fiscal com departamento `fiscal` e modulo `documentos_fiscais`.
- Cadastro de certificado e-CNPJ A1 em `.pfx` ou `.p12`, com senha armazenada como hash e arquivo fora de `static`.
- Importacao de XML de NF-e, extracao de metadados, armazenamento do XML e geracao automatica de DANFE/PDF.
- Controle de NSU por CNPJ da empresa, preparado para integracao Sefaz homologada.
- Preparacao da integracao gratuita com PyNFe para Consulta Distribuicao DF-e por NSU.
- Tela de documentos fiscais com filtros, download de XML e download de DANFE.
- Busca de NF-e na O.C. pelo CNPJ do fornecedor.
- Vinculo da NF-e a O.C. e associacao automatica do DANFE/PDF ao mesmo documento fiscal.

## Pastas padrao

Ambiente local Windows:

```text
FISCAL_XML_DIR=G:\Meu Drive\App Rental Retros\XMLs
FISCAL_DANFE_DIR=G:\Meu Drive\App Rental Retros\DANFs
```

## Render

O Render roda em Linux e nao acessa a unidade local `G:\` diretamente. Para producao, configurar caminhos Linux persistentes ou integrar o Google Drive por API/credencial:

```text
FISCAL_XML_DIR=/var/data/app-rental-retros/xmls
FISCAL_DANFE_DIR=/var/data/app-rental-retros/danfes
FISCAL_CERTIFICADOS_DIR=/var/data/app-rental-retros/certificados
FISCAL_SEFAZ_UF=sp
FISCAL_SEFAZ_HOMOLOGACAO=false
FISCAL_CERTIFICADO_CRYPTO_KEY=<chave-fernet-estavel>
```

Se o armazenamento definitivo for Google Drive, o proximo passo tecnico e trocar a gravacao local por upload via API usando uma conta de servico com acesso as pastas compartilhadas.

Para gerar `FISCAL_CERTIFICADO_CRYPTO_KEY`, usar uma chave Fernet e manter o valor fixo no Render. Se essa chave mudar, sera necessario recadastrar o certificado A1 para recriptografar a senha.

## Fora do escopo

- Missao 15 Operacao nao foi alterada.
- Missao 17 Fiscal Financeiro nao foi iniciada.
- Consulta Sefaz real depende da instalacao das dependencias do `requirements.txt`, do certificado recadastrado apos esta preparacao e de internet liberada no ambiente.
