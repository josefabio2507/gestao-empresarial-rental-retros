from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook


ABAS_ESPERADAS = (
    "Empresa",
    "Unidade(s) de Entrega",
    "Beneficiarios",
    "FonteDados",
)


def gerar_planilha_pedido(modelo: Path, numero_pedido, empresas, unidades, beneficiarios):
    """Preenche uma c�pia do modelo oficial sem alterar o arquivo base."""
    workbook = load_workbook(modelo, data_only=False)
    if tuple(workbook.sheetnames) != ABAS_ESPERADAS:
        raise ValueError("O modelo da planilha n�o corresponde � estrutura esperada.")

    empresa_sheet = workbook["Empresa"]
    unidade_sheet = workbook["Unidade(s) de Entrega"]
    beneficiario_sheet = workbook["Beneficiarios"]
    fontes_sheet = workbook["FonteDados"]

    max_contratos = sum(
        1 for cell in fontes_sheet._cells.values()
        if cell.column == 1 and isinstance(cell.value, str) and cell.value.startswith("=")
    )
    max_unidades = sum(
        1 for cell in fontes_sheet._cells.values()
        if cell.column == 3 and isinstance(cell.value, str) and cell.value.startswith("=")
    )
    if len(empresas) > max_contratos or len(unidades) > max_unidades:
        raise ValueError("O modelo atingiu o limite de contratos ou unidades nas listas auxiliares.")

    empresa_por_contrato = {
        f"{item.numero_contrato} - {item.produto}": item for item in empresas
    }
    unidade_por_empresa = {
        (item.cnpj, f"{item.codigo_unidade} - {item.nome_unidade}"): item
        for item in unidades
    }

    empresa_sheet["E2"] = str(numero_pedido)
    for row, item in enumerate(empresas, start=5):
        values = (
            item.cnpj,
            item.nome_empresa,
            item.numero_contrato,
            item.produto,
            item.data_credito,
        )
        for column, value in enumerate(values, start=1):
            empresa_sheet.cell(row, column, value)

    for row, item in enumerate(unidades, start=4):
        values = (
            item.cnpj,
            item.codigo_unidade,
            item.nome_unidade,
            item.tipo_logradouro,
            item.logradouro,
            item.numero,
            item.complemento,
            item.bairro,
            item.estado,
            item.cidade,
            item.cep,
            item.interlocutor,
            item.cpf_interlocutor,
            item.rg_interlocutor,
            item.ddd,
            item.telefone,
            item.ramal,
        )
        for column, value in enumerate(values, start=1):
            unidade_sheet.cell(row, column, value)

    for row, item in enumerate(beneficiarios, start=4):
        empresa = empresa_por_contrato.get(item.contrato_produto)
        unidade = unidade_por_empresa.get((empresa.cnpj, item.unidade_entrega)) if empresa else None
        if not empresa or not unidade:
            raise ValueError("Um benefici�rio est� sem v�nculo v�lido de contrato ou unidade.")
        values = (
            item.matricula,
            item.cpf,
            item.nome,
            item.data_nascimento,
            item.departamento,
            item.unidade_entrega,
            float(item.valor_mensal),
            item.contrato_produto,
            item.numero_parcelas,
        )
        for column, value in enumerate(values, start=1):
            beneficiario_sheet.cell(row, column, value)

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    output.seek(0)
    return output
