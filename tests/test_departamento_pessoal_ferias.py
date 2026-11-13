from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.departamento_pessoal.ferias_routes import (
    calcular_estimativa,
    data_limite_concessao,
    situacao_prazo,
)


def registro(**kwargs):
    valores = {
        "periodo_aquisitivo_fim": date(2025, 1, 31),
        "status": "programada",
    }
    valores.update(kwargs)
    return SimpleNamespace(**valores)


def test_data_limite_concessao_e_calculada_em_doze_meses():
    assert data_limite_concessao(registro()) == date(2026, 1, 31)


def test_situacao_prazo_identifica_vencido_e_proximo():
    assert situacao_prazo(registro(), hoje=date(2026, 2, 1)) == "vencido"
    assert situacao_prazo(registro(), hoje=date(2025, 12, 1)) == "proximo"
    assert situacao_prazo(registro(), hoje=date(2025, 6, 1)) == "no_prazo"
    assert situacao_prazo(registro(status="concluida"), hoje=date(2026, 2, 1)) == "encerrado"


def test_calculo_estimado_sem_abono():
    resultado = calcular_estimativa(Decimal("3000"), 30, False)
    assert resultado["remuneracao"] == Decimal("3000.00")
    assert resultado["terco"] == Decimal("1000.00")
    assert resultado["abono_dias"] == 0
    assert resultado["total"] == Decimal("4000.00")


def test_calculo_estimado_com_abono():
    resultado = calcular_estimativa(Decimal("3000"), 30, True)
    assert resultado["abono_dias"] == 10
    assert resultado["abono_valor"] == Decimal("1000.00")
    assert resultado["total"] == Decimal("5333.33")
