from sqlalchemy import or_

from app.extensions import db
from app.models import OperacaoVeiculoEquipamento


SITUACOES_AQUISICAO = ["Quitado", "Financiado"]
TIPOS_VEICULO_EQUIPAMENTO = [
    "Veículo leve",
    "Caminhão",
    "Máquina",
    "Equipamento",
    "EPG",
    "Outro",
]


VEICULOS_EQUIPAMENTOS_INICIAIS = [
    ("STG7D96", "CITROEN JUMPY", "9V7VBYHVERA007070", "Quitado", "Veículo leve"),
    ("RMJ4E07", "M BENZ - ACCELO 1016", "9BM979078LB191211", "Quitado", "Caminhão"),
    ("QNH0H80", "M BENZ - ACCELO 1016", "9BM979026JB075295", "Quitado", "Caminhão"),
    ("FUV6F90", "FORD - CARGO 816", "9BFVEADS1EBS69487", "Quitado", "Caminhão"),
    ("IWQ7F41", "FORD - CARGO 1319", "9BFXEB1B1FBS73432", "Quitado", "Caminhão"),
    ("SWLC90", "VOLKS - EXPRESS", "95355FTEXPR042128", "Quitado", "Caminhão"),
    ("SUD8D27", "CASE - 580N SERIE 2", "HBZN580NPRAH34224", "Quitado", "Máquina"),
    ("SWO7D00", "CASE - 580N SERIE 2", "HBZN580NJPAH31968", "Quitado", "Máquina"),
    ("FDE3E21", "CASE - 580N TC", "HBZN580NHNAH30415", "Quitado", "Máquina"),
    ("FKC0H21", "CASE - 580N TC", "HBZN580NKNAH30413", "Quitado", "Máquina"),
    ("FCT4A64", "JOHN DEERE - 310L", "1BZ310LAKJD001386", "Quitado", "Máquina"),
    ("EXR7I36", "JOHN DEERE - 310L", "1BZ310LAJKD002105", "Quitado", "Máquina"),
    ("TKG7G47", "NEW HOLLAND - B95C", "HBZNB95CTRAH34101", "Quitado", "Máquina"),
    ("DED1G69", "NEW HOLLAND - B95B", "HBZNB95BLGAH15935", "Quitado", "Máquina"),
    ("RVP9D49", "FIAT MOBI LIKE", "9BD341ACZPY851075", "Quitado", "Veículo leve"),
    ("RFD7B93", "FIAT MOBI LIKE", "9BD341A5XLY680113", "Quitado", "Veículo leve"),
    ("RFD1D62", "FIAT MOBI LIKE", "9BD341A5XLY680509", "Quitado", "Veículo leve"),
    ("QXN5F52", "FIAT MOBI LIKE", "9BD341A5XLY669544", "Quitado", "Veículo leve"),
    ("SDS7F82", "VOLKS VOYAGE", "9BWDG45U1PT055300", "Quitado", "Veículo leve"),
    ("GAG9B93", "VOLKS SAVEIRO", "9BWKB45U5KP017849", "Quitado", "Veículo leve"),
    ("TKS5F97", "CITROEN BASALT", "935CPFCA7SB556035", "Quitado", "Veículo leve"),
    ("ESC HIDRÁULICA", "JOHN DEERE - 200G", "1F9200GXPND020551", "Financiado", "Máquina"),
    ("TJF7D14", "VW/EXPRESS DRF 4X2", "95355FTE9SR015706", "Financiado", "Caminhão"),
    ("SWU3F73", "VOLKS - DELIVERY 11.180", "9535E6TB4PR054099", "Financiado", "Caminhão"),
    ("FJJ3E14", "VOLKS - CONSTELATION 31320", "9536C8TL9SR002684", "Financiado", "Caminhão"),
]


def _limpar_texto(valor):
    valor = (valor or "").strip()
    return valor or None


def _normalizar_form(form_data):
    identificacao = _limpar_texto(form_data.get("identificacao"))
    placa = _limpar_texto(form_data.get("placa"))
    descricao = _limpar_texto(form_data.get("descricao"))
    chassi = _limpar_texto(form_data.get("chassi"))
    renavam = _limpar_texto(form_data.get("renavam"))
    situacao_aquisicao = _limpar_texto(form_data.get("situacao_aquisicao"))
    tipo = _limpar_texto(form_data.get("tipo"))
    observacoes = _limpar_texto(form_data.get("observacoes"))
    ativo = "ativo" in form_data

    return {
        "identificacao": identificacao,
        "placa": placa,
        "descricao": descricao,
        "chassi": chassi,
        "renavam": renavam,
        "situacao_aquisicao": situacao_aquisicao,
        "tipo": tipo,
        "observacoes": observacoes,
        "ativo": ativo,
    }


def buscar_veiculos_equipamentos(filtros):
    query = OperacaoVeiculoEquipamento.query

    identificacao = _limpar_texto(filtros.get("identificacao"))
    placa = _limpar_texto(filtros.get("placa"))
    descricao = _limpar_texto(filtros.get("descricao"))
    chassi = _limpar_texto(filtros.get("chassi"))
    centro_custo = _limpar_texto(filtros.get("centro_custo"))
    situacao = _limpar_texto(filtros.get("situacao_aquisicao"))
    tipo = _limpar_texto(filtros.get("tipo"))
    status = _limpar_texto(filtros.get("status"))

    if identificacao:
        query = query.filter(OperacaoVeiculoEquipamento.identificacao.ilike(f"%{identificacao}%"))
    if placa:
        query = query.filter(OperacaoVeiculoEquipamento.placa.ilike(f"%{placa}%"))
    if descricao:
        query = query.filter(OperacaoVeiculoEquipamento.descricao.ilike(f"%{descricao}%"))
    if chassi:
        query = query.filter(OperacaoVeiculoEquipamento.chassi.ilike(f"%{chassi}%"))
    if centro_custo:
        query = query.filter(OperacaoVeiculoEquipamento.centro_custo.ilike(f"%{centro_custo}%"))
    if situacao in SITUACOES_AQUISICAO:
        query = query.filter(OperacaoVeiculoEquipamento.situacao_aquisicao == situacao)
    if tipo in TIPOS_VEICULO_EQUIPAMENTO:
        query = query.filter(OperacaoVeiculoEquipamento.tipo == tipo)
    if status == "ativos":
        query = query.filter(OperacaoVeiculoEquipamento.ativo.is_(True))
    elif status == "inativos":
        query = query.filter(OperacaoVeiculoEquipamento.ativo.is_(False))

    return (
        query
        .order_by(
            OperacaoVeiculoEquipamento.ativo.desc(),
            OperacaoVeiculoEquipamento.identificacao.asc(),
        )
        .all()
    )


def buscar_por_id(veiculo_id):
    return OperacaoVeiculoEquipamento.query.get(veiculo_id)


def salvar_veiculo_equipamento(form_data, veiculo=None):
    dados = _normalizar_form(form_data)

    if not veiculo and "ativo" not in form_data:
        dados["ativo"] = True

    if not dados["identificacao"]:
        return False, "Informe a identificação.", veiculo

    if not dados["descricao"]:
        return False, "Informe a descrição.", veiculo

    if dados["situacao_aquisicao"] not in SITUACOES_AQUISICAO:
        return False, "Informe uma situação de aquisição válida.", veiculo

    if dados["tipo"] not in TIPOS_VEICULO_EQUIPAMENTO:
        return False, "Informe um tipo válido.", veiculo

    duplicado = OperacaoVeiculoEquipamento.query.filter(
        OperacaoVeiculoEquipamento.identificacao == dados["identificacao"],
    )
    if veiculo:
        duplicado = duplicado.filter(OperacaoVeiculoEquipamento.id != veiculo.id)
    if duplicado.first():
        return False, "Já existe veículo/equipamento com essa identificação.", veiculo

    if dados["chassi"]:
        duplicado_chassi = OperacaoVeiculoEquipamento.query.filter(
            OperacaoVeiculoEquipamento.chassi == dados["chassi"],
        )
        if veiculo:
            duplicado_chassi = duplicado_chassi.filter(OperacaoVeiculoEquipamento.id != veiculo.id)
        if duplicado_chassi.first():
            return False, "Já existe veículo/equipamento com esse chassi.", veiculo

    if not veiculo:
        veiculo = OperacaoVeiculoEquipamento()
        db.session.add(veiculo)

    for campo, valor in dados.items():
        setattr(veiculo, campo, valor)

    veiculo.recalcular_centro_custo()
    db.session.commit()

    return True, "Veículo/equipamento salvo com sucesso.", veiculo


def alterar_status(veiculo):
    veiculo.ativo = not veiculo.ativo
    db.session.commit()

    acao = "reativado" if veiculo.ativo else "inativado"
    return True, f"Veículo/equipamento {acao} com sucesso."


def buscar_existente(chassi, identificacao):
    filtros = []

    if chassi:
        filtros.append(OperacaoVeiculoEquipamento.chassi == chassi)

    if identificacao:
        filtros.append(OperacaoVeiculoEquipamento.identificacao == identificacao)

    if not filtros:
        return None

    return OperacaoVeiculoEquipamento.query.filter(or_(*filtros)).first()


def executar_carga_inicial():
    resumo = {
        "processados": 0,
        "criados": 0,
        "existentes": 0,
        "ignorados": 0,
        "centros_recalculados": 0,
        "divergencias": 0,
        "erros": [],
    }

    for identificacao, descricao, chassi, situacao, tipo in VEICULOS_EQUIPAMENTOS_INICIAIS:
        resumo["processados"] += 1

        try:
            centro_calculado = OperacaoVeiculoEquipamento.calcular_centro_custo(
                identificacao,
                descricao,
            )
            centro_planilha = f"{identificacao}-{descricao}"

            if centro_planilha != centro_calculado:
                resumo["divergencias"] += 1

            existente = buscar_existente(chassi, identificacao)

            if existente:
                resumo["existentes"] += 1
                centro_anterior = existente.centro_custo
                existente.recalcular_centro_custo()

                if existente.centro_custo != centro_anterior:
                    resumo["centros_recalculados"] += 1

                continue

            veiculo = OperacaoVeiculoEquipamento(
                identificacao=identificacao,
                placa=identificacao if identificacao != "ESC HIDRÁULICA" else None,
                descricao=descricao,
                chassi=chassi,
                renavam=None,
                situacao_aquisicao=situacao,
                tipo=tipo,
                ativo=True,
            )
            veiculo.recalcular_centro_custo()
            db.session.add(veiculo)
            resumo["criados"] += 1
            resumo["centros_recalculados"] += 1

        except Exception as erro:
            resumo["ignorados"] += 1
            resumo["erros"].append(f"{identificacao}: {erro}")

    db.session.commit()
    return resumo


def imprimir_resumo_carga(resumo):
    print("Carga inicial de veículos/equipamentos concluída.")
    print("Total de registros processados:", resumo["processados"])
    print("Registros criados:", resumo["criados"])
    print("Registros já existentes:", resumo["existentes"])
    print("Registros ignorados:", resumo["ignorados"])
    print("Centros de custo recalculados:", resumo["centros_recalculados"])
    print("Divergências entre planilha e cálculo:", resumo["divergencias"])
    print("Erros:", len(resumo["erros"]))

    for erro in resumo["erros"]:
        print("-", erro)
