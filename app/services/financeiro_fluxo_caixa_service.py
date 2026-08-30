import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import joinedload

from app.models import CentroCusto, FinanceiroContaPagarBaixa, FinanceiroContaPagarTitulo, FinanceiroContaReceberBaixa, FinanceiroContaReceberTitulo
from app.services.financeiro_contas_pagar_service import calcular_saldo_titulo as calcular_saldo_pagar

STATUS_CP_INATIVOS = {"Pago", "Cancelado", "Estornado"}
STATUS_CR_INATIVOS = {"Recebido", "Cancelado", "Estornado"}
STATUS_BAIXA_ATIVA = "Ativa"
TIPOS_MOVIMENTO = [("", "Todos"), ("Entrada", "Entrada"), ("Saída", "Saída")]
NATUREZAS_MOVIMENTO = [("", "Todas"), ("Previsto", "Previsto"), ("Realizado", "Realizado")]
ORIGENS_ENTRADA = ["Contas a Receber", "Nota Fiscal Emitida", "Contrato", "Medição", "Reembolso", "Manual"]
ORIGENS_SAIDA = ["Contas a Pagar", "Ordem de Compra", "XML Fiscal", "Cartão de Crédito", "Fatura de Cartão", "Manual"]


def valor_decimal(valor):
    return Decimal(valor or 0).quantize(Decimal("0.01"))


def moeda(valor):
    texto = f"{valor_decimal(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_data(valor):
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_int(valor):
    try:
        return int(valor) if valor not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _inicio_mes(data_base):
    return data_base.replace(day=1)


def _fim_mes(data_base):
    if data_base.month == 12:
        return data_base.replace(year=data_base.year + 1, month=1, day=1) - timedelta(days=1)
    return data_base.replace(month=data_base.month + 1, day=1) - timedelta(days=1)


def filtros_padrao_fluxo(args=None):
    args = args or {}
    hoje = date.today()
    inicio = _parse_data(args.get("data_inicio"))
    fim = _parse_data(args.get("data_fim"))
    if not inicio and not fim and not args.get("sem_periodo"):
        inicio = _inicio_mes(hoje)
        fim = _fim_mes(hoje)
    return {
        "data_inicio": inicio,
        "data_fim": fim,
        "tipo": args.get("tipo") or "",
        "natureza": args.get("natureza") or "",
        "origem": args.get("origem") or "",
        "cliente": (args.get("cliente") or "").strip(),
        "fornecedor": (args.get("fornecedor") or "").strip(),
        "status": args.get("status") or "",
        "centro_custo_id": _parse_int(args.get("centro_custo_id")),
        "sub_centro_custo_equipe_id": _parse_int(args.get("sub_centro_custo_equipe_id")),
        "sub_centro_custo_veiculo_id": _parse_int(args.get("sub_centro_custo_veiculo_id")),
        "forma": args.get("forma") or "",
        "conta": (args.get("conta") or "").strip(),
        "documento": (args.get("documento") or "").strip(),
        "nota_fiscal": (args.get("nota_fiscal") or "").strip(),
        "ordem_compra": (args.get("ordem_compra") or "").strip(),
        "contrato_id": _parse_int(args.get("contrato_id")),
        "medicao_id": _parse_int(args.get("medicao_id")),
    }


def filtros_para_template_fluxo(filtros):
    dados = dict(filtros)
    dados["data_inicio"] = filtros["data_inicio"].isoformat() if filtros.get("data_inicio") else ""
    dados["data_fim"] = filtros["data_fim"].isoformat() if filtros.get("data_fim") else ""
    return dados


def periodo_valido_fluxo(filtros):
    return not (filtros.get("data_inicio") and filtros.get("data_fim") and filtros["data_inicio"] > filtros["data_fim"])


def opcoes_fluxo_caixa():
    origens = sorted(set(ORIGENS_ENTRADA + ORIGENS_SAIDA))
    return {
        "tipos": TIPOS_MOVIMENTO,
        "naturezas": NATUREZAS_MOVIMENTO,
        "origens": [(origem, origem) for origem in origens],
        "status": ["Previsto", "Realizado", "Parcial", "Vencido", "Cancelado", "Estornado"],
        "formas": ["Boleto", "Pix", "Transferencia", "Transferência", "Deposito", "Depósito", "Cartao de Credito", "Cartão", "Dinheiro", "Outro"],
        "centros_custo": CentroCusto.query.filter_by(ativo=True).order_by(CentroCusto.nome.asc()).all(),
    }


def _origem_entrada(titulo):
    origem = titulo.origem_lancamento or "Manual"
    if origem in {"Nota Fiscal Emitida", "Medição", "Contrato", "Reembolso"}:
        return origem
    return "Contas a Receber" if origem == "Manual" else origem


def _origem_saida(titulo):
    origem = titulo.origem_lancamento or "Manual"
    if origem == "Ordem de Compra":
        return "Ordem de Compra"
    if origem == "XML Fiscal":
        return "XML Fiscal"
    if titulo.fatura_cartao_id:
        return "Fatura de Cartão"
    if origem == "Cartao de Credito" or titulo.forma_pagamento == "Cartao de Credito":
        return "Cartão de Crédito"
    return "Contas a Pagar" if origem == "Manual" else origem


def _status_previsto(data_movimento, status_origem, hoje):
    if status_origem in {"Cancelado", "Estornado"}:
        return status_origem
    if data_movimento and data_movimento < hoje:
        return "Vencido"
    return "Previsto"


def _movimento_base(**kwargs):
    valor_previsto = valor_decimal(kwargs.pop("valor_previsto", Decimal("0.00")))
    valor_realizado = valor_decimal(kwargs.pop("valor_realizado", Decimal("0.00")))
    tipo = kwargs.get("tipo")
    natureza = kwargs.get("natureza")
    valor_movimento = valor_realizado if natureza == "Realizado" else valor_previsto
    sinal = Decimal("1.00") if tipo == "Entrada" else Decimal("-1.00")
    movimento = {
        "data": None, "tipo": tipo, "natureza": natureza, "origem": "", "descricao": "", "pessoa": "", "documento": "", "nota_fiscal": "",
        "valor_previsto": valor_previsto, "valor_realizado": valor_realizado, "valor_movimento": valor_movimento,
        "valor_sinalizado": (valor_movimento * sinal).quantize(Decimal("0.01")), "saldo": Decimal("0.00"), "status": "",
        "centro_custo_id": None, "centro_custo": "", "forma": "", "conta": "", "link_endpoint": None, "link_kwargs": {},
        "titulo_id": None, "lote_id": None, "contrato_id": None, "medicao_id": None, "ordem_compra": "",
    }
    movimento.update(kwargs)
    return movimento


def _entradas_previstas(hoje):
    titulos = FinanceiroContaReceberTitulo.query.options(
        joinedload(FinanceiroContaReceberTitulo.centro_custo),
    ).filter(~FinanceiroContaReceberTitulo.status.in_(STATUS_CR_INATIVOS)).all()
    movimentos = []
    for titulo in titulos:
        saldo = valor_decimal(titulo.saldo_aberto)
        if saldo <= 0:
            continue
        movimentos.append(_movimento_base(
            data=titulo.data_vencimento, tipo="Entrada", natureza="Previsto", origem=_origem_entrada(titulo), descricao=titulo.descricao,
            pessoa=titulo.cliente_nome_snapshot, documento=titulo.numero_documento or "", nota_fiscal=titulo.numero_nota_fiscal or "", valor_previsto=saldo,
            status=_status_previsto(titulo.data_vencimento, titulo.status, hoje), centro_custo_id=titulo.centro_custo_id,
            centro_custo=titulo.centro_custo.nome if titulo.centro_custo else "", link_endpoint="financeiro_contas_receber.detalhe",
            link_kwargs={"titulo_id": titulo.id}, titulo_id=titulo.id, contrato_id=titulo.contrato_id, medicao_id=titulo.medicao_id,
        ))
    return movimentos


def _entradas_realizadas():
    baixas = FinanceiroContaReceberBaixa.query.options(
        joinedload(FinanceiroContaReceberBaixa.titulo).joinedload(FinanceiroContaReceberTitulo.centro_custo),
        joinedload(FinanceiroContaReceberBaixa.lote_baixa),
    ).filter(FinanceiroContaReceberBaixa.status == STATUS_BAIXA_ATIVA).all()
    movimentos = []
    for baixa in baixas:
        titulo = baixa.titulo
        if not titulo or titulo.status in {"Cancelado", "Estornado"}:
            continue
        movimentos.append(_movimento_base(
            data=baixa.data_recebimento, tipo="Entrada", natureza="Realizado", origem=_origem_entrada(titulo), descricao=titulo.descricao,
            pessoa=titulo.cliente_nome_snapshot, documento=titulo.numero_documento or "", nota_fiscal=titulo.numero_nota_fiscal or "", valor_realizado=baixa.valor_recebido,
            status="Realizado", centro_custo_id=titulo.centro_custo_id, centro_custo=titulo.centro_custo.nome if titulo.centro_custo else "",
            forma=baixa.forma_recebimento or "", conta=baixa.conta_recebimento_descricao or "", link_endpoint="financeiro_contas_receber.detalhe",
            link_kwargs={"titulo_id": titulo.id}, titulo_id=titulo.id, lote_id=baixa.lote_baixa_id, contrato_id=titulo.contrato_id, medicao_id=titulo.medicao_id,
        ))
    return movimentos


def _saidas_previstas(hoje):
    titulos = FinanceiroContaPagarTitulo.query.options(
        joinedload(FinanceiroContaPagarTitulo.centro_custo),
    ).filter(~FinanceiroContaPagarTitulo.status.in_(STATUS_CP_INATIVOS)).all()
    movimentos = []
    for titulo in titulos:
        saldo = valor_decimal(calcular_saldo_pagar(titulo))
        if saldo <= 0:
            continue
        movimentos.append(_movimento_base(
            data=titulo.data_vencimento, tipo="Saída", natureza="Previsto", origem=_origem_saida(titulo), descricao=titulo.descricao,
            pessoa=titulo.fornecedor_nome_snapshot, documento=titulo.numero_documento or "", nota_fiscal=titulo.numero_nfe or "", valor_previsto=saldo,
            status=_status_previsto(titulo.data_vencimento, titulo.status, hoje), centro_custo_id=titulo.centro_custo_id,
            centro_custo=titulo.centro_custo.nome if titulo.centro_custo else "", forma=titulo.forma_pagamento or "", link_endpoint="financeiro_contas_pagar.detalhes",
            link_kwargs={"titulo_id": titulo.id}, titulo_id=titulo.id,
        ))
    return movimentos


def _saidas_realizadas():
    baixas = FinanceiroContaPagarBaixa.query.options(
        joinedload(FinanceiroContaPagarBaixa.titulo).joinedload(FinanceiroContaPagarTitulo.centro_custo),
        joinedload(FinanceiroContaPagarBaixa.lote_baixa),
    ).filter(FinanceiroContaPagarBaixa.status == STATUS_BAIXA_ATIVA).all()
    movimentos = []
    for baixa in baixas:
        titulo = baixa.titulo
        if not titulo or titulo.status in {"Cancelado", "Estornado"}:
            continue
        movimentos.append(_movimento_base(
            data=baixa.data_pagamento, tipo="Saída", natureza="Realizado", origem=_origem_saida(titulo), descricao=titulo.descricao,
            pessoa=titulo.fornecedor_nome_snapshot, documento=titulo.numero_documento or "", nota_fiscal=titulo.numero_nfe or "", valor_realizado=baixa.valor_pago,
            status="Realizado", centro_custo_id=titulo.centro_custo_id, centro_custo=titulo.centro_custo.nome if titulo.centro_custo else "",
            forma=baixa.forma_pagamento or titulo.forma_pagamento or "", conta=baixa.conta_pagamento_descricao or "", link_endpoint="financeiro_contas_pagar.detalhes",
            link_kwargs={"titulo_id": titulo.id}, titulo_id=titulo.id, lote_id=baixa.lote_baixa_id,
        ))
    return movimentos


def _aplicar_filtros(movimentos, filtros):
    inicio = filtros.get("data_inicio")
    fim = filtros.get("data_fim")
    resultado = []
    for mov in movimentos:
        data_mov = mov.get("data")
        if inicio and (not data_mov or data_mov < inicio):
            continue
        if fim and (not data_mov or data_mov > fim):
            continue
        if filtros.get("tipo") and mov["tipo"] != filtros["tipo"]:
            continue
        if filtros.get("natureza") and mov["natureza"] != filtros["natureza"]:
            continue
        if filtros.get("origem") and mov["origem"] != filtros["origem"]:
            continue
        if filtros.get("cliente") and (mov["tipo"] != "Entrada" or filtros["cliente"].lower() not in mov["pessoa"].lower()):
            continue
        if filtros.get("fornecedor") and (mov["tipo"] != "Saída" or filtros["fornecedor"].lower() not in mov["pessoa"].lower()):
            continue
        if filtros.get("status") and mov["status"] != filtros["status"]:
            continue
        if filtros.get("centro_custo_id") and mov.get("centro_custo_id") != filtros["centro_custo_id"]:
            continue
        if filtros.get("forma") and mov.get("forma") != filtros["forma"]:
            continue
        if filtros.get("conta") and filtros["conta"].lower() not in (mov.get("conta") or "").lower():
            continue
        if filtros.get("documento") and filtros["documento"].lower() not in (mov.get("documento") or "").lower():
            continue
        if filtros.get("nota_fiscal") and filtros["nota_fiscal"].lower() not in (mov.get("nota_fiscal") or "").lower():
            continue
        if filtros.get("ordem_compra") and filtros["ordem_compra"].lower() not in (mov.get("ordem_compra") or "").lower():
            continue
        if filtros.get("contrato_id") and mov.get("contrato_id") != filtros["contrato_id"]:
            continue
        if filtros.get("medicao_id") and mov.get("medicao_id") != filtros["medicao_id"]:
            continue
        resultado.append(mov)
    resultado.sort(key=lambda item: (item.get("data") or date.min, item["tipo"], item["natureza"], item.get("titulo_id") or 0))
    saldo = Decimal("0.00")
    for mov in resultado:
        saldo = (saldo + mov["valor_sinalizado"]).quantize(Decimal("0.01"))
        mov["saldo"] = saldo
    return resultado


def movimentos_fluxo_caixa(filtros=None):
    filtros = filtros or filtros_padrao_fluxo({})
    hoje = date.today()
    movimentos = []
    movimentos.extend(_entradas_previstas(hoje))
    movimentos.extend(_entradas_realizadas())
    movimentos.extend(_saidas_previstas(hoje))
    movimentos.extend(_saidas_realizadas())
    return _aplicar_filtros(movimentos, filtros)


def _totais(movimentos):
    entradas_previstas = sum((m["valor_previsto"] for m in movimentos if m["tipo"] == "Entrada" and m["natureza"] == "Previsto"), Decimal("0.00"))
    saidas_previstas = sum((m["valor_previsto"] for m in movimentos if m["tipo"] == "Saída" and m["natureza"] == "Previsto"), Decimal("0.00"))
    entradas_realizadas = sum((m["valor_realizado"] for m in movimentos if m["tipo"] == "Entrada" and m["natureza"] == "Realizado"), Decimal("0.00"))
    saidas_realizadas = sum((m["valor_realizado"] for m in movimentos if m["tipo"] == "Saída" and m["natureza"] == "Realizado"), Decimal("0.00"))
    return {
        "entradas_previstas": entradas_previstas.quantize(Decimal("0.01")),
        "saidas_previstas": saidas_previstas.quantize(Decimal("0.01")),
        "entradas_realizadas": entradas_realizadas.quantize(Decimal("0.01")),
        "saidas_realizadas": saidas_realizadas.quantize(Decimal("0.01")),
        "saldo_previsto": (entradas_previstas - saidas_previstas).quantize(Decimal("0.01")),
        "saldo_realizado": (entradas_realizadas - saidas_realizadas).quantize(Decimal("0.01")),
        "diferenca_previsto_realizado": ((entradas_previstas - saidas_previstas) - (entradas_realizadas - saidas_realizadas)).quantize(Decimal("0.01")),
        "quantidade": len(movimentos),
    }


def _entre_datas(movimentos, inicio, fim):
    return [m for m in movimentos if m.get("data") and inicio <= m["data"] <= fim]


def dashboard_fluxo_caixa(filtros=None):
    filtros = filtros or filtros_padrao_fluxo({})
    movimentos = movimentos_fluxo_caixa(filtros)
    hoje = date.today()
    totais = _totais(movimentos)
    proximos_7 = _totais(_entre_datas(movimentos, hoje, hoje + timedelta(days=7)))
    proximos_30 = _totais(_entre_datas(movimentos, hoje, hoje + timedelta(days=30)))
    entradas_previstas = [m for m in movimentos if m["tipo"] == "Entrada" and m["natureza"] == "Previsto"]
    saidas_previstas = [m for m in movimentos if m["tipo"] == "Saída" and m["natureza"] == "Previsto"]
    entradas_realizadas = [m for m in movimentos if m["tipo"] == "Entrada" and m["natureza"] == "Realizado"]
    saidas_realizadas = [m for m in movimentos if m["tipo"] == "Saída" and m["natureza"] == "Realizado"]
    dias = agrupar_fluxo(movimentos, "dia")
    return {
        "cards": {
            **totais,
            "contas_receber_vencidas": sum((m["valor_previsto"] for m in entradas_previstas if m["status"] == "Vencido"), Decimal("0.00")),
            "contas_pagar_vencidas": sum((m["valor_previsto"] for m in saidas_previstas if m["status"] == "Vencido"), Decimal("0.00")),
            "saldo_7_dias": proximos_7["saldo_previsto"],
            "saldo_30_dias": proximos_30["saldo_previsto"],
            "maior_entrada_prevista": max((m["valor_previsto"] for m in entradas_previstas), default=Decimal("0.00")),
            "maior_saida_prevista": max((m["valor_previsto"] for m in saidas_previstas), default=Decimal("0.00")),
        },
        "tabelas": {
            "proximas_entradas": sorted(entradas_previstas, key=lambda m: (m["data"] or date.max, -m["valor_previsto"]))[:50],
            "proximas_saidas": sorted(saidas_previstas, key=lambda m: (m["data"] or date.max, -m["valor_previsto"]))[:50],
            "maiores_entradas": sorted(entradas_previstas, key=lambda m: m["valor_previsto"], reverse=True)[:50],
            "maiores_saidas": sorted(saidas_previstas, key=lambda m: m["valor_previsto"], reverse=True)[:50],
            "entradas_realizadas": sorted(entradas_realizadas, key=lambda m: (m["data"] or date.min), reverse=True)[:50],
            "saidas_realizadas": sorted(saidas_realizadas, key=lambda m: (m["data"] or date.min), reverse=True)[:50],
            "dias_saldo_negativo": [linha for linha in dias if linha["saldo_previsto"] < 0][:50],
            "resumo_mes": agrupar_fluxo(movimentos, "mes"),
        },
    }


def agrupar_fluxo(movimentos, periodo="dia"):
    grupos = {}
    for mov in movimentos:
        data_mov = mov.get("data")
        if not data_mov:
            continue
        if periodo == "semana":
            ano, semana, _ = data_mov.isocalendar()
            inicio = data_mov - timedelta(days=data_mov.weekday())
            fim = inicio + timedelta(days=6)
            chave = (ano, semana)
            label = f"Semana {semana:02d}/{ano}"
            ordem = inicio
        elif periodo == "mes":
            chave = (data_mov.year, data_mov.month)
            label = f"{data_mov.month:02d}/{data_mov.year}"
            inicio = data_mov.replace(day=1)
            fim = _fim_mes(inicio)
            ordem = inicio
        else:
            chave = data_mov
            label = data_mov.strftime("%d/%m/%Y")
            inicio = fim = data_mov
            ordem = data_mov
        if chave not in grupos:
            grupos[chave] = {"chave": chave, "ordem": ordem, "label": label, "data": data_mov if periodo == "dia" else None, "periodo_inicio": inicio, "periodo_fim": fim, "entradas_previstas": Decimal("0.00"), "saidas_previstas": Decimal("0.00"), "entradas_realizadas": Decimal("0.00"), "saidas_realizadas": Decimal("0.00"), "movimentos": []}
        grupo = grupos[chave]
        grupo["movimentos"].append(mov)
        if mov["tipo"] == "Entrada" and mov["natureza"] == "Previsto":
            grupo["entradas_previstas"] += mov["valor_previsto"]
        elif mov["tipo"] == "Saída" and mov["natureza"] == "Previsto":
            grupo["saidas_previstas"] += mov["valor_previsto"]
        elif mov["tipo"] == "Entrada" and mov["natureza"] == "Realizado":
            grupo["entradas_realizadas"] += mov["valor_realizado"]
        elif mov["tipo"] == "Saída" and mov["natureza"] == "Realizado":
            grupo["saidas_realizadas"] += mov["valor_realizado"]
    linhas = sorted(grupos.values(), key=lambda item: item["ordem"])
    acumulado_previsto = Decimal("0.00")
    acumulado_realizado = Decimal("0.00")
    for linha in linhas:
        linha["saldo_previsto"] = (linha["entradas_previstas"] - linha["saidas_previstas"]).quantize(Decimal("0.01"))
        linha["saldo_realizado"] = (linha["entradas_realizadas"] - linha["saidas_realizadas"]).quantize(Decimal("0.01"))
        linha["diferenca"] = (linha["saldo_previsto"] - linha["saldo_realizado"]).quantize(Decimal("0.01"))
        acumulado_previsto = (acumulado_previsto + linha["saldo_previsto"]).quantize(Decimal("0.01"))
        acumulado_realizado = (acumulado_realizado + linha["saldo_realizado"]).quantize(Decimal("0.01"))
        linha["saldo_acumulado_previsto"] = acumulado_previsto
        linha["saldo_acumulado_realizado"] = acumulado_realizado
    return linhas


def visao_fluxo_caixa(periodo, filtros=None):
    movimentos = movimentos_fluxo_caixa(filtros or filtros_padrao_fluxo({}))
    return {"periodo": periodo, "linhas": agrupar_fluxo(movimentos, periodo), "totais": _totais(movimentos)}


def valor_coluna_fluxo(linha, coluna):
    valor = linha.get(coluna) if isinstance(linha, dict) else getattr(linha, coluna, None)
    if isinstance(valor, Decimal) or coluna.startswith("valor") or coluna.startswith("saldo") or coluna in {"entradas_previstas", "saidas_previstas", "entradas_realizadas", "saidas_realizadas", "diferenca"}:
        return moeda(valor)
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return valor or "-"


def gerar_csv_movimentos(movimentos):
    saida = io.StringIO()
    writer = csv.writer(saida, delimiter=";")
    writer.writerow(["Fluxo de Caixa - Movimentos"])
    writer.writerow(["Data", "Tipo", "Natureza", "Origem", "Descricao", "Cliente/Fornecedor", "Documento", "Nota fiscal", "Valor previsto", "Valor realizado", "Saldo", "Status", "Centro de custo", "Forma", "Conta"])
    for mov in movimentos:
        writer.writerow([valor_coluna_fluxo(mov, "data"), mov["tipo"], mov["natureza"], mov["origem"], mov["descricao"], mov["pessoa"], mov["documento"], mov["nota_fiscal"], moeda(mov["valor_previsto"]), moeda(mov["valor_realizado"]), moeda(mov["saldo"]), mov["status"], mov["centro_custo"], mov["forma"], mov["conta"]])
    return "\ufeff" + saida.getvalue()


def nome_arquivo_fluxo(prefixo="movimentos"):
    return f"fluxo_caixa_{prefixo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
