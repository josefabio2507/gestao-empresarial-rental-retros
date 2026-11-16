from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from app.departamento_pessoal.pedido_tiquete.excel_service import gerar_planilha_pedido


MODELO = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "departamento_pessoal"
    / "pedido_tiquete"
    / "modelo_pedido_ticket.xlsx"
)


def _dados_teste():
    empresa = SimpleNamespace(
        cnpj="12345678000190",
        nome_empresa="EMPRESA TESTE",
        numero_contrato="0000123456",
        produto="TAE",
        data_credito=date(2026, 12, 10),
    )
    unidade = SimpleNamespace(
        cnpj=empresa.cnpj,
        codigo_unidade="000123",
        nome_unidade="UNIDADE TESTE",
        tipo_logradouro="R.",
        logradouro="RUA TESTE",
        numero="10",
        complemento="",
        bairro="CENTRO",
        estado="SP",
        cidade="SANTOS",
        cep="11000000",
        interlocutor="CONTATO TESTE",
        cpf_interlocutor="",
        rg_interlocutor="",
        ddd="13",
        telefone="999999999",
        ramal="",
    )
    beneficiario = SimpleNamespace(
        matricula="000001",
        cpf="12345678901",
        nome="COLABORADOR TESTE",
        data_nascimento=date(1990, 1, 1),
        departamento="OPERACAO",
        unidade_entrega="000123 - UNIDADE TESTE",
        valor_mensal=Decimal("125.50"),
        contrato_produto="0000123456 - TAE",
        numero_parcelas=1,
    )
    return empresa, unidade, beneficiario


def test_gera_copia_sem_perder_estrutura_do_modelo():
    empresa, unidade, beneficiario = _dados_teste()
    original = load_workbook(MODELO, data_only=False)
    esperado = {
        "abas": original.sheetnames,
        "estados": [sheet.sheet_state for sheet in original.worksheets],
        "nomes": list(original.defined_names),
        "validacoes": [len(sheet.data_validations.dataValidation) for sheet in original.worksheets],
        "formulas_auxiliares": sum(
            isinstance(cell.value, str) and cell.value.startswith("=")
            for cell in original["FonteDados"]._cells.values()
        ),
    }

    arquivo = gerar_planilha_pedido(
        MODELO, "00000042", [empresa], [unidade], [beneficiario]
    )
    gerado = load_workbook(arquivo, data_only=False)

    assert gerado.sheetnames == esperado["abas"]
    assert [sheet.sheet_state for sheet in gerado.worksheets] == esperado["estados"]
    assert list(gerado.defined_names) == esperado["nomes"]
    assert [len(sheet.data_validations.dataValidation) for sheet in gerado.worksheets] == esperado["validacoes"]
    assert sum(
        isinstance(cell.value, str) and cell.value.startswith("=")
        for cell in gerado["FonteDados"]._cells.values()
    ) == esperado["formulas_auxiliares"]
    assert gerado["Empresa"]["E2"].value == "00000042"
    assert gerado["Empresa"]["A5"].value == empresa.cnpj
    assert gerado["Unidade(s) de Entrega"]["B4"].value == unidade.codigo_unidade
    assert gerado["Beneficiarios"]["A4"].value == beneficiario.matricula
    assert gerado["Beneficiarios"]["G4"].value == 125.5
    gerado.close()
    original.close()


def test_rejeita_unidade_que_nao_corresponde_ao_contrato():
    empresa, unidade, beneficiario = _dados_teste()
    unidade.cnpj = "99999999000199"

    with pytest.raises(ValueError, match="vínculo válido"):
        gerar_planilha_pedido(MODELO, "42", [empresa], [unidade], [beneficiario])
