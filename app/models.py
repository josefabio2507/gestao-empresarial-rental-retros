from app.utils.datas import agora_brasil

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class NivelAcesso(db.Model):
    __tablename__ = "niveis_acesso"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    usuarios = db.relationship("Usuario", back_populates="nivel_acesso")

    def __repr__(self):
        return f"<NivelAcesso {self.slug}>"


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)

    nivel_acesso_id = db.Column(
        db.Integer,
        db.ForeignKey("niveis_acesso.id"),
        nullable=False
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=True,
        index=True
    )

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    precisa_trocar_senha = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    nivel_acesso = db.relationship("NivelAcesso", back_populates="usuarios")
    colaborador = db.relationship("Colaborador", back_populates="usuarios")
    permissoes = db.relationship(
        "PermissaoUsuarioModulo",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )
    logs = db.relationship("LogAcesso", back_populates="usuario")
    tokens_recuperacao_senha = db.relationship(
        "TokenRecuperacaoSenha",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )
    holerites_criados = db.relationship(
        "HoleriteColaborador",
        back_populates="criado_por",
        foreign_keys="HoleriteColaborador.criado_por_usuario_id"
    )

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def normalizar_email(self):
        if self.email:
            self.email = self.email.strip().lower()

    @property
    def is_active(self):
        return self.ativo

    @property
    def is_admin(self):
        return (
            self.nivel_acesso
            and self.nivel_acesso.slug == "administrador"
        )

    def __repr__(self):
        return f"<Usuario {self.email}>"


class Departamento(db.Model):
    __tablename__ = "departamentos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    icone = db.Column(db.String(80), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    modulos = db.relationship(
        "Modulo",
        back_populates="departamento",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Departamento {self.slug}>"


class Modulo(db.Model):
    __tablename__ = "modulos"

    id = db.Column(db.Integer, primary_key=True)

    departamento_id = db.Column(
        db.Integer,
        db.ForeignKey("departamentos.id"),
        nullable=False
    )

    nome = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    icone = db.Column(db.String(80), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    departamento = db.relationship("Departamento", back_populates="modulos")
    permissoes = db.relationship(
        "PermissaoUsuarioModulo",
        back_populates="modulo",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "departamento_id",
            "slug",
            name="uq_modulo_departamento_slug"
        ),
    )

    def __repr__(self):
        return f"<Modulo {self.departamento.slug if self.departamento else ''}/{self.slug}>"


class OperacaoVeiculoEquipamento(db.Model):
    __tablename__ = "operacao_veiculos_equipamentos"

    id = db.Column(db.Integer, primary_key=True)
    identificacao = db.Column(db.String(120), nullable=False, index=True)
    placa = db.Column(db.String(20), nullable=True, index=True)
    descricao = db.Column(db.String(220), nullable=False)
    chassi = db.Column(db.String(80), nullable=True, unique=True, index=True)
    renavam = db.Column(db.String(40), nullable=True)
    centro_custo = db.Column(db.String(360), nullable=False, index=True)
    centro_custo_id = db.Column(db.Integer, db.ForeignKey("centros_custo.id"), nullable=True, index=True)
    situacao_aquisicao = db.Column(db.String(30), nullable=False)
    tipo = db.Column(db.String(40), nullable=False)
    status_operacional = db.Column(db.String(30), default="Disponivel", nullable=False, index=True)
    motivo_indisponibilidade = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "identificacao",
            name="uq_operacao_veiculos_equipamentos_identificacao",
        ),
        db.CheckConstraint(
            "situacao_aquisicao in ('Quitado', 'Financiado')",
            name="ck_operacao_veiculos_situacao_aquisicao",
        ),
        db.CheckConstraint(
            "tipo in ('Veiculo leve', 'Caminhao', 'Maquina', 'Equipamento', 'EGP', 'Outro')",
            name="ck_operacao_veiculos_tipo",
        ),
        db.CheckConstraint(
            "status_operacional in ('Disponivel', 'Em uso', 'Indisponivel')",
            name="ck_operacao_veiculos_status_operacional",
        ),
    )

    centro_custo_ref = db.relationship("CentroCusto")
    vinculos_responsaveis = db.relationship(
        "OperacaoVeiculoResponsavel",
        back_populates="veiculo",
        order_by="OperacaoVeiculoResponsavel.iniciado_em.desc()",
    )
    leituras = db.relationship(
        "OperacaoLeituraAtivo",
        back_populates="veiculo",
        order_by="OperacaoLeituraAtivo.registrada_em.desc()",
    )
    planos_manutencao = db.relationship(
        "OperacaoPlanoManutencaoPreventiva",
        back_populates="veiculo",
    )
    historicos_manutencao = db.relationship(
        "OperacaoHistoricoManutencao",
        back_populates="veiculo",
    )

    abastecimentos = db.relationship(
        "OperacaoAbastecimento",
        back_populates="veiculo",
        order_by="OperacaoAbastecimento.data_abastecimento.desc()",
    )
    multas_transito = db.relationship(
        "OperacaoMultaTransito",
        back_populates="veiculo",
        order_by="OperacaoMultaTransito.data_infracao.desc()",
    )
    impostos_taxas = db.relationship(
        "OperacaoImpostoTaxa",
        back_populates="veiculo",
        order_by="OperacaoImpostoTaxa.data_vencimento.desc()",
    )
    @property
    def vinculo_ativo(self):
        for vinculo in self.vinculos_responsaveis:
            if vinculo.ativo:
                return vinculo
        return None

    @staticmethod
    def calcular_centro_custo(identificacao, descricao):
        return f"{(identificacao or '').strip()}-{(descricao or '').strip()}"

    def recalcular_centro_custo(self):
        self.centro_custo = self.calcular_centro_custo(
            self.identificacao,
            self.descricao,
        )

    def __repr__(self):
        return f"<OperacaoVeiculoEquipamento {self.identificacao}>"


class OperacaoVeiculoResponsavel(db.Model):
    __tablename__ = "operacao_veiculos_responsaveis"

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("operacao_veiculos_equipamentos.id"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=False, index=True)
    equipe_id = db.Column(db.Integer, db.ForeignKey("equipes.id"), nullable=True, index=True)
    usuario_responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    iniciado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False, index=True)
    encerrado_em = db.Column(db.DateTime, nullable=True, index=True)
    leitura_inicial = db.Column(db.Numeric(12, 2), nullable=True)
    leitura_final = db.Column(db.Numeric(12, 2), nullable=True)
    tipo_leitura = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(30), default="Ativo", nullable=False, index=True)
    motivo_correcao = db.Column(db.Text, nullable=True)
    corrigido_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    corrigido_em = db.Column(db.DateTime, nullable=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    veiculo = db.relationship("OperacaoVeiculoEquipamento", back_populates="vinculos_responsaveis")
    colaborador = db.relationship("Colaborador")
    equipe = db.relationship("Equipe")
    usuario_responsavel = db.relationship("Usuario", foreign_keys=[usuario_responsavel_id])
    corrigido_por = db.relationship("Usuario", foreign_keys=[corrigido_por_usuario_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    leituras = db.relationship("OperacaoLeituraAtivo", back_populates="vinculo")

    __table_args__ = (
        db.CheckConstraint(
            "status in ('Ativo', 'Encerrado', 'Corrigido', 'Cancelado', 'Retificado')",
            name="ck_operacao_vinculos_status",
        ),
        db.CheckConstraint(
            "tipo_leitura is null or tipo_leitura in ('odometro', 'horimetro')",
            name="ck_operacao_vinculos_tipo_leitura",
        ),
    )

    @property
    def ativo(self):
        return self.status == "Ativo" and self.encerrado_em is None

    def __repr__(self):
        return f"<OperacaoVeiculoResponsavel veiculo={self.veiculo_id} colaborador={self.colaborador_id}>"


class OperacaoLeituraAtivo(db.Model):
    __tablename__ = "operacao_leituras_ativos"

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("operacao_veiculos_equipamentos.id"),
        nullable=False,
        index=True,
    )
    vinculo_id = db.Column(
        db.Integer,
        db.ForeignKey("operacao_veiculos_responsaveis.id"),
        nullable=True,
        index=True,
    )
    tipo = db.Column(db.String(20), nullable=False, index=True)
    leitura = db.Column(db.Numeric(12, 2), nullable=False)
    origem = db.Column(db.String(30), nullable=False, index=True)
    registrada_em = db.Column(db.DateTime, default=agora_brasil, nullable=False, index=True)
    valida = db.Column(db.Boolean, default=True, nullable=False, index=True)
    motivo_correcao = db.Column(db.Text, nullable=True)
    registrado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)

    veiculo = db.relationship("OperacaoVeiculoEquipamento", back_populates="leituras")
    vinculo = db.relationship("OperacaoVeiculoResponsavel", back_populates="leituras")
    registrado_por = db.relationship("Usuario")

    __table_args__ = (
        db.CheckConstraint("tipo in ('odometro', 'horimetro')", name="ck_operacao_leituras_tipo"),
        db.CheckConstraint(
            "origem in ('pool', 'abastecimento', 'manutencao', 'correcao')",
            name="ck_operacao_leituras_origem",
        ),
        db.CheckConstraint("leitura >= 0", name="ck_operacao_leituras_valor"),
    )

    def __repr__(self):
        return f"<OperacaoLeituraAtivo veiculo={self.veiculo_id} leitura={self.leitura}>"



class OperacaoAbastecimento(db.Model):
    __tablename__ = "operacao_abastecimentos"

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(db.Integer, db.ForeignKey("operacao_veiculos_equipamentos.id"), nullable=False, index=True)
    vinculo_id = db.Column(db.Integer, db.ForeignKey("operacao_veiculos_responsaveis.id"), nullable=False, index=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=False, index=True)
    equipe_id = db.Column(db.Integer, db.ForeignKey("equipes.id"), nullable=True, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    data_abastecimento = db.Column(db.Date, nullable=False, index=True)
    tipo_combustivel = db.Column(db.String(40), nullable=False, index=True)
    qtd_litros = db.Column(db.Numeric(12, 3), nullable=False)
    preco = db.Column(db.Numeric(12, 2), nullable=False)
    cupom_drive_file_id = db.Column(db.String(255), nullable=True)
    cupom_nome_arquivo = db.Column(db.String(255), nullable=True)
    cupom_link = db.Column(db.String(500), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    veiculo = db.relationship("OperacaoVeiculoEquipamento", back_populates="abastecimentos")
    vinculo = db.relationship("OperacaoVeiculoResponsavel")
    colaborador = db.relationship("Colaborador")
    equipe = db.relationship("Equipe")
    usuario = db.relationship("Usuario")

    __table_args__ = (
        db.CheckConstraint(
            "tipo_combustivel in ('Diesel S10', 'Etanol', 'Etanol aditivado', 'Gasolina comum', 'Gasolina aditivada', 'Gasolina Premium')",
            name="ck_operacao_abastecimentos_tipo_combustivel",
        ),
        db.CheckConstraint("qtd_litros > 0", name="ck_operacao_abastecimentos_qtd_litros"),
        db.CheckConstraint("preco >= 0", name="ck_operacao_abastecimentos_preco"),
    )

    def __repr__(self):
        return f"<OperacaoAbastecimento veiculo={self.veiculo_id} data={self.data_abastecimento}>"

class OperacaoMultaTransito(db.Model):
    __tablename__ = "operacao_multas_transito"

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(db.Integer, db.ForeignKey("operacao_veiculos_equipamentos.id"), nullable=False, index=True)
    motorista_vinculado_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=True, index=True)
    motorista_indicado_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=True, index=True)
    motorista_indicado_nome = db.Column(db.String(160), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    data_infracao = db.Column(db.Date, nullable=False, index=True)
    hora_infracao = db.Column(db.Time, nullable=False)
    numero_auto_infracao = db.Column(db.String(80), nullable=False, unique=True, index=True)
    local_infracao = db.Column(db.String(255), nullable=False)
    cidade = db.Column(db.String(80), nullable=False, index=True)
    descricao_infracao = db.Column(db.Text, nullable=False)
    valor_multa = db.Column(db.Numeric(12, 2), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    gravidade = db.Column(db.String(40), nullable=False)
    pontuacao = db.Column(db.Integer, nullable=False)
    data_vencimento_segunda_cobranca = db.Column(db.Date, nullable=True)
    valor_segunda_cobranca = db.Column(db.Numeric(12, 2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    veiculo = db.relationship("OperacaoVeiculoEquipamento", back_populates="multas_transito")
    motorista_vinculado = db.relationship("Colaborador", foreign_keys=[motorista_vinculado_id])
    motorista_indicado = db.relationship("Colaborador", foreign_keys=[motorista_indicado_id])
    usuario = db.relationship("Usuario")

    __table_args__ = (
        db.CheckConstraint(
            "cidade in ('CUBATAO', 'SANTOS', 'SAO VICENTE', 'GUARUJA', 'PRAIA GRANDE', 'ITANHAEM', 'MONGAGUA', 'SAO PAULO')",
            name="ck_operacao_multas_transito_cidade",
        ),
        db.CheckConstraint(
            "gravidade in ('Leve', 'Media', 'Grave', 'Gravissima')",
            name="ck_operacao_multas_transito_gravidade",
        ),
        db.CheckConstraint("valor_multa >= 0", name="ck_operacao_multas_transito_valor"),
        db.CheckConstraint(
            "valor_segunda_cobranca is null or valor_segunda_cobranca >= 0",
            name="ck_operacao_multas_transito_valor_segunda",
        ),
        db.CheckConstraint("pontuacao >= 0", name="ck_operacao_multas_transito_pontuacao"),
    )

    @property
    def custo_total(self):
        return (self.valor_multa or 0) + (self.valor_segunda_cobranca or 0)

    def __repr__(self):
        return f"<OperacaoMultaTransito veiculo={self.veiculo_id} auto={self.numero_auto_infracao}>"


class OperacaoImpostoTaxa(db.Model):
    __tablename__ = "operacao_impostos_taxas"

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(db.Integer, db.ForeignKey("operacao_veiculos_equipamentos.id"), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    tipo_custo = db.Column(db.String(30), nullable=False, index=True)
    numero_parcela = db.Column(db.String(20), nullable=False, index=True)
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    veiculo = db.relationship("OperacaoVeiculoEquipamento", back_populates="impostos_taxas")
    usuario = db.relationship("Usuario")

    __table_args__ = (
        db.CheckConstraint("tipo_custo in ('IPVA', 'Licenciamento')", name="ck_operacao_impostos_taxas_tipo_custo"),
        db.CheckConstraint("numero_parcela in ('Cota Unica', '1a', '2a', '3a', '4a', '5a')", name="ck_operacao_impostos_taxas_numero_parcela"),
        db.CheckConstraint("valor >= 0", name="ck_operacao_impostos_taxas_valor"),
    )

    def __repr__(self):
        return f"<OperacaoImpostoTaxa veiculo={self.veiculo_id} tipo={self.tipo_custo} parcela={self.numero_parcela}>"

class OperacaoPlanoManutencaoPreventiva(db.Model):
    __tablename__ = "operacao_planos_manutencao_preventiva"

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("operacao_veiculos_equipamentos.id"),
        nullable=False,
        index=True,
    )
    descricao = db.Column(db.String(220), nullable=False)
    periodicidade_km = db.Column(db.Integer, nullable=True)
    periodicidade_horimetro = db.Column(db.Integer, nullable=True)
    periodicidade_dias = db.Column(db.Integer, nullable=True)
    antecedencia_km = db.Column(db.Integer, nullable=True)
    antecedencia_horimetro = db.Column(db.Integer, nullable=True)
    antecedencia_dias = db.Column(db.Integer, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    veiculo = db.relationship("OperacaoVeiculoEquipamento", back_populates="planos_manutencao")

    def __repr__(self):
        return f"<OperacaoPlanoManutencaoPreventiva veiculo={self.veiculo_id}>"


class OperacaoHistoricoManutencao(db.Model):
    __tablename__ = "operacao_historico_manutencao"

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("operacao_veiculos_equipamentos.id"),
        nullable=False,
        index=True,
    )
    centro_custo_id = db.Column(db.Integer, db.ForeignKey("centros_custo.id"), nullable=True, index=True)
    requisicao_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_requisicoes_compra.id"),
        nullable=True,
        index=True,
    )
    ordem_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordens_compra.id"),
        nullable=True,
        index=True,
    )
    origem_financeira = db.Column(db.String(30), default="Suprimentos", nullable=False)
    descricao = db.Column(db.String(220), nullable=False)
    realizada_em = db.Column(db.DateTime, nullable=True, index=True)
    leitura_odometro = db.Column(db.Numeric(12, 2), nullable=True)
    leitura_horimetro = db.Column(db.Numeric(12, 2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    veiculo = db.relationship("OperacaoVeiculoEquipamento", back_populates="historicos_manutencao")
    centro_custo = db.relationship("CentroCusto")
    requisicao_compra = db.relationship("SuprimentosRequisicaoCompra")
    ordem_compra = db.relationship("SuprimentosOrdemCompra")

    __table_args__ = (
        db.CheckConstraint(
            "origem_financeira = 'Suprimentos'",
            name="ck_operacao_historico_manutencao_origem_financeira",
        ),
    )

    def __repr__(self):
        return f"<OperacaoHistoricoManutencao veiculo={self.veiculo_id}>"

class PermissaoUsuarioModulo(db.Model):
    __tablename__ = "permissoes_usuario_modulo"

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    modulo_id = db.Column(
        db.Integer,
        db.ForeignKey("modulos.id"),
        nullable=False
    )

    pode_visualizar = db.Column(db.Boolean, default=False, nullable=False)
    pode_criar = db.Column(db.Boolean, default=False, nullable=False)
    pode_editar = db.Column(db.Boolean, default=False, nullable=False)
    pode_excluir = db.Column(db.Boolean, default=False, nullable=False)
    pode_aprovar = db.Column(db.Boolean, default=False, nullable=False)
    pode_exportar = db.Column(db.Boolean, default=False, nullable=False)

    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    usuario = db.relationship("Usuario", back_populates="permissoes")
    modulo = db.relationship("Modulo", back_populates="permissoes")

    __table_args__ = (
        db.UniqueConstraint(
            "usuario_id",
            "modulo_id",
            name="uq_permissao_usuario_modulo"
        ),
    )

    def garantir_visualizacao(self):
        if (
            self.pode_criar
            or self.pode_editar
            or self.pode_excluir
            or self.pode_aprovar
            or self.pode_exportar
        ):
            self.pode_visualizar = True

    def __repr__(self):
        return f"<Permissao usuario={self.usuario_id} modulo={self.modulo_id}>"


class LogAcesso(db.Model):
    __tablename__ = "logs_acesso"

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True
    )

    acao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    rota = db.Column(db.String(255), nullable=True)
    ip = db.Column(db.String(80), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)

    usuario = db.relationship("Usuario", back_populates="logs")

    def __repr__(self):
        return f"<LogAcesso {self.acao}>"


class TokenRecuperacaoSenha(db.Model):
    __tablename__ = "tokens_recuperacao_senha"

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expira_em = db.Column(db.DateTime, nullable=False, index=True)
    usado_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    ip_solicitacao = db.Column(db.String(80), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    usuario = db.relationship("Usuario", back_populates="tokens_recuperacao_senha")

    @property
    def foi_usado(self):
        return self.usado_em is not None

    @property
    def expirou(self):
        return agora_brasil() > self.expira_em

    def __repr__(self):
        return f"<TokenRecuperacaoSenha usuario={self.usuario_id}>"

class Equipe(db.Model):
    __tablename__ = "equipes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    colaboradores = db.relationship(
        "Colaborador",
        back_populates="equipe"
    )

    def __repr__(self):
        return f"<Equipe {self.slug}>"


class Cargo(db.Model):
    __tablename__ = "cargos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    def __repr__(self):
        return f"<Cargo {self.nome}>"


class Colaborador(db.Model):
    __tablename__ = "colaboradores"

    id = db.Column(db.Integer, primary_key=True)

    matricula = db.Column(db.String(40), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    cargo = db.Column(db.String(120), nullable=True)
    vale_transporte_optante = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    equipe_id = db.Column(
        db.Integer,
        db.ForeignKey("equipes.id"),
        nullable=False
    )

    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    equipe = db.relationship(
        "Equipe",
        back_populates="colaboradores"
    )
    usuarios = db.relationship(
        "Usuario",
        back_populates="colaborador"
    )
    holerites = db.relationship(
        "HoleriteColaborador",
        back_populates="colaborador"
    )
    linhas_vale_transporte = db.relationship(
        "ValeTransporteColaboradorLinha",
        back_populates="colaborador"
    )
    itens_pedidos_vale_transporte = db.relationship(
        "ValeTransportePedidoItem",
        back_populates="colaborador"
    )

    def __repr__(self):
        return f"<Colaborador {self.matricula} - {self.nome}>"


class LinhaOnibus(db.Model):
    __tablename__ = "linhas_onibus"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    codigo = db.Column(db.String(60), nullable=True)
    empresa_transporte = db.Column(db.String(150), nullable=False)
    valor_tarifa_dia = db.Column(db.Numeric(10, 2), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    vinculos_colaboradores = db.relationship(
        "ValeTransporteColaboradorLinha",
        back_populates="linha_onibus"
    )
    itens_pedidos_vale_transporte = db.relationship(
        "ValeTransportePedidoItem",
        back_populates="linha_onibus"
    )

    def __repr__(self):
        return f"<LinhaOnibus {self.codigo or ''} {self.nome}>"


class ValeTransporteColaboradorLinha(db.Model):
    __tablename__ = "vale_transporte_colaborador_linhas"

    id = db.Column(db.Integer, primary_key=True)

    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=False,
        index=True
    )

    linha_onibus_id = db.Column(
        db.Integer,
        db.ForeignKey("linhas_onibus.id"),
        nullable=False,
        index=True
    )

    tipo_pagamento = db.Column(db.String(30), nullable=False)
    periodicidade_pagamento = db.Column(
        db.String(20),
        default="mensal",
        nullable=False,
    )
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    colaborador = db.relationship(
        "Colaborador",
        back_populates="linhas_vale_transporte"
    )
    linha_onibus = db.relationship(
        "LinhaOnibus",
        back_populates="vinculos_colaboradores"
    )

    __table_args__ = (
        db.CheckConstraint(
            "tipo_pagamento in ('dinheiro', 'cartao_transporte')",
            name="ck_vale_transporte_tipo_pagamento",
        ),
        db.CheckConstraint(
            "periodicidade_pagamento in ('mensal', 'semanal')",
            name="ck_vale_transporte_periodicidade_pagamento",
        ),
    )

    def __repr__(self):
        return (
            f"<ValeTransporteColaboradorLinha "
            f"colaborador={self.colaborador_id} linha={self.linha_onibus_id}>"
        )


class ValeTransportePedido(db.Model):
    __tablename__ = "vale_transporte_pedidos"

    id = db.Column(db.Integer, primary_key=True)
    competencia = db.Column(db.String(7), nullable=False, index=True)
    data_inicial = db.Column(db.Date, nullable=False)
    data_final = db.Column(db.Date, nullable=False)
    quantidade_dias_padrao = db.Column(db.Integer, nullable=False)

    equipe_id = db.Column(
        db.Integer,
        db.ForeignKey("equipes.id"),
        nullable=True,
        index=True
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=True,
        index=True
    )
    forma_pagamento_filtro = db.Column(db.String(30), nullable=True)
    empresa_transporte_filtro = db.Column(db.String(150), nullable=True)
    prazo_pagamento = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), default="Gerado", nullable=False, index=True)

    criado_por_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True
    )

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    equipe = db.relationship("Equipe")
    colaborador = db.relationship("Colaborador")
    criado_por = db.relationship("Usuario")
    itens = db.relationship(
        "ValeTransportePedidoItem",
        back_populates="pedido",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "status in ('Rascunho', 'Gerado', 'Cancelado')",
            name="ck_vale_transporte_pedidos_status",
        ),
        db.CheckConstraint(
            "prazo_pagamento in ('mensal', 'semanal')",
            name="ck_vale_transporte_pedidos_prazo_pagamento",
        ),
        db.CheckConstraint(
            "quantidade_dias_padrao > 0",
            name="ck_vale_transporte_pedidos_quantidade_dias",
        ),
    )

    def __repr__(self):
        return f"<ValeTransportePedido competencia={self.competencia} status={self.status}>"


class ValeTransportePedidoItem(db.Model):
    __tablename__ = "vale_transporte_pedido_itens"

    id = db.Column(db.Integer, primary_key=True)

    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("vale_transporte_pedidos.id"),
        nullable=False,
        index=True
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=False,
        index=True
    )
    linha_onibus_id = db.Column(
        db.Integer,
        db.ForeignKey("linhas_onibus.id"),
        nullable=False,
        index=True
    )

    matricula_snapshot = db.Column(db.String(40), nullable=False)
    nome_colaborador_snapshot = db.Column(db.String(150), nullable=False)
    equipe_snapshot = db.Column(db.String(120), nullable=True)
    empresa_transporte_snapshot = db.Column(db.String(150), nullable=False)
    linha_transporte_snapshot = db.Column(db.String(220), nullable=False)
    forma_pagamento = db.Column(db.String(30), nullable=False)
    tarifa_diaria = db.Column(db.Numeric(10, 2), nullable=False)
    quantidade_dias = db.Column(db.Integer, nullable=False)
    valor_base = db.Column(db.Numeric(10, 2), nullable=False)
    valor_acrescimo = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    valor_desconto = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    pedido = db.relationship("ValeTransportePedido", back_populates="itens")
    colaborador = db.relationship(
        "Colaborador",
        back_populates="itens_pedidos_vale_transporte"
    )
    linha_onibus = db.relationship(
        "LinhaOnibus",
        back_populates="itens_pedidos_vale_transporte"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "pedido_id",
            "colaborador_id",
            "linha_onibus_id",
            name="uq_vale_transporte_pedido_item_colaborador_linha",
        ),
        db.CheckConstraint(
            "forma_pagamento in ('dinheiro', 'cartao_transporte')",
            name="ck_vale_transporte_pedido_itens_forma_pagamento",
        ),
        db.CheckConstraint(
            "quantidade_dias > 0",
            name="ck_vale_transporte_pedido_itens_quantidade_dias",
        ),
        db.CheckConstraint(
            "valor_acrescimo >= 0",
            name="ck_vale_transporte_pedido_itens_acrescimo",
        ),
        db.CheckConstraint(
            "valor_desconto >= 0",
            name="ck_vale_transporte_pedido_itens_desconto",
        ),
        db.CheckConstraint(
            "valor_total >= 0",
            name="ck_vale_transporte_pedido_itens_total",
        ),
    )

    def __repr__(self):
        return (
            f"<ValeTransportePedidoItem pedido={self.pedido_id} "
            f"colaborador={self.colaborador_id} linha={self.linha_onibus_id}>"
        )


class HoleriteColaborador(db.Model):
    __tablename__ = "holerites_colaboradores"

    id = db.Column(db.Integer, primary_key=True)

    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=False,
        index=True
    )

    competencia = db.Column(db.String(7), nullable=False, index=True)
    tipo = db.Column(db.String(80), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    origem_arquivo = db.Column(db.String(50), nullable=True)
    google_drive_file_id = db.Column(db.String(255), nullable=True)
    google_drive_url = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True
    )

    colaborador = db.relationship(
        "Colaborador",
        back_populates="holerites"
    )
    criado_por = db.relationship(
        "Usuario",
        back_populates="holerites_criados",
        foreign_keys=[criado_por_usuario_id]
    )

    def __repr__(self):
        return f"<HoleriteColaborador colaborador={self.colaborador_id} competencia={self.competencia}>"

class Restaurante(db.Model):
    __tablename__ = "restaurantes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    itens_cardapio = db.relationship(
        "ItemCardapio",
        back_populates="restaurante"
    )

    def __repr__(self):
        return f"<Restaurante {self.nome}>"


class ItemCardapio(db.Model):
    __tablename__ = "itens_cardapio"

    id = db.Column(db.Integer, primary_key=True)

    restaurante_id = db.Column(
        db.Integer,
        db.ForeignKey("restaurantes.id"),
        nullable=False
    )

    tipo = db.Column(db.String(30), nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    dia_semana = db.Column(db.String(30), default="Todos os Dias", nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    restaurante = db.relationship(
        "Restaurante",
        back_populates="itens_cardapio"
    )

    def __repr__(self):
        return f"<ItemCardapio {self.tipo} - {self.nome}>"

class PedidoRefeicao(db.Model):
    __tablename__ = "pedidos_refeicao"

    id = db.Column(db.Integer, primary_key=True)

    numero_pedido = db.Column(
        db.String(30),
        unique=True,
        nullable=True,
        index=True
    )

    equipe_id = db.Column(
        db.Integer,
        db.ForeignKey("equipes.id"),
        nullable=False
    )

    restaurante_id = db.Column(
        db.Integer,
        db.ForeignKey("restaurantes.id"),
        nullable=False
    )

    data_pedido = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default="Aberto", nullable=False)
    observacao = db.Column(db.Text, nullable=True)

    enviado_whatsapp = db.Column(db.Boolean, default=False, nullable=False)
    quantidade_envios = db.Column(db.Integer, default=0, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    equipe = db.relationship("Equipe")
    restaurante = db.relationship("Restaurante")

    def __repr__(self):
        return f"<PedidoRefeicao {self.numero_pedido}>"

class ConsumoRefeicao(db.Model):
    __tablename__ = "consumos_refeicao"

    id = db.Column(db.Integer, primary_key=True)

    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos_refeicao.id"),
        nullable=False
    )

    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=False
    )

    item_cardapio_id = db.Column(
        db.Integer,
        db.ForeignKey("itens_cardapio.id"),
        nullable=False
    )

    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    observacao = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    pedido = db.relationship("PedidoRefeicao", backref="consumos")
    colaborador = db.relationship("Colaborador")
    item_cardapio = db.relationship("ItemCardapio")

    def __repr__(self):
        return f"<ConsumoRefeicao pedido={self.pedido_id} colaborador={self.colaborador_id}>"


class SuprimentosFornecedor(db.Model):
    __tablename__ = "suprimentos_fornecedores"

    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(180), nullable=False)
    nome_fantasia = db.Column(db.String(180), nullable=True)
    tipo_pessoa = db.Column(db.String(20), nullable=False)
    cnpj_cpf = db.Column(db.String(14), unique=True, nullable=True, index=True)
    inscricao_estadual = db.Column(db.String(40), nullable=True)
    telefone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    pessoa_contato = db.Column(db.String(120), nullable=True)
    endereco = db.Column(db.String(255), nullable=True)
    cidade = db.Column(db.String(120), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    itens = db.relationship(
        "SuprimentosFornecedorItem",
        back_populates="fornecedor",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "tipo_pessoa in ('juridica', 'fisica')",
            name="ck_suprimentos_fornecedores_tipo_pessoa",
        ),
    )

    def __repr__(self):
        return f"<SuprimentosFornecedor {self.razao_social}>"


class SuprimentosCategoriaItem(db.Model):
    __tablename__ = "suprimentos_categorias_itens"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    itens = db.relationship("SuprimentosItem", back_populates="categoria")

    def __repr__(self):
        return f"<SuprimentosCategoriaItem {self.slug}>"


class SuprimentosUnidadeMedida(db.Model):
    __tablename__ = "suprimentos_unidades_medida"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    sigla = db.Column(db.String(20), unique=True, nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    itens = db.relationship("SuprimentosItem", back_populates="unidade_medida")

    def __repr__(self):
        return f"<SuprimentosUnidadeMedida {self.sigla}>"


class CentroCusto(db.Model):
    __tablename__ = "centros_custo"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(40), unique=True, nullable=True, index=True)
    nome = db.Column(db.String(120), nullable=False)
    classe = db.Column(db.String(40), default="CENTRO DE CUSTO", nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    itens_suprimentos = db.relationship(
        "SuprimentosItem",
        back_populates="centro_custo_padrao",
    )

    def __repr__(self):
        return f"<CentroCusto {self.codigo or ''} {self.nome}>"

class FinanceiroCartaoCredito(db.Model):
    __tablename__ = "financeiro_cartoes_credito"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, index=True)
    banco = db.Column(db.String(120), nullable=False, index=True)
    bandeira = db.Column(db.String(60), nullable=True, index=True)
    ultimos_4_digitos = db.Column(db.String(4), nullable=True)
    titular_responsavel = db.Column(db.String(120), nullable=True)
    dia_fechamento = db.Column(db.Integer, nullable=False)
    dia_vencimento = db.Column(db.Integer, nullable=False)
    limite = db.Column(db.Numeric(12, 2), nullable=True)
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    observacoes = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    atualizado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False,
    )

    centro_custo = db.relationship("CentroCusto")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    faturas = db.relationship(
        "FinanceiroCartaoFatura",
        back_populates="cartao_credito",
        cascade="all, delete-orphan",
    )
    titulos = db.relationship("FinanceiroContaPagarTitulo", back_populates="cartao_credito")

    __table_args__ = (
        db.CheckConstraint("dia_fechamento between 1 and 31", name="ck_fin_cartao_dia_fechamento"),
        db.CheckConstraint("dia_vencimento between 1 and 31", name="ck_fin_cartao_dia_vencimento"),
        db.CheckConstraint("limite is null or limite >= 0", name="ck_fin_cartao_limite"),
        db.CheckConstraint("ultimos_4_digitos is null or length(ultimos_4_digitos) = 4", name="ck_fin_cartao_ultimos_4"),
    )

    @property
    def identificacao_segura(self):
        final = f" - final {self.ultimos_4_digitos}" if self.ultimos_4_digitos else ""
        return f"{self.nome} - {self.banco}{final}"

    def __repr__(self):
        return f"<FinanceiroCartaoCredito {self.id} {self.nome}>"


class FinanceiroCartaoFatura(db.Model):
    __tablename__ = "financeiro_cartoes_faturas"

    id = db.Column(db.Integer, primary_key=True)
    cartao_credito_id = db.Column(
        db.Integer,
        db.ForeignKey("financeiro_cartoes_credito.id"),
        nullable=False,
        index=True,
    )
    competencia = db.Column(db.Date, nullable=False, index=True)
    data_fechamento = db.Column(db.Date, nullable=False, index=True)
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    valor_total = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    valor_pago = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="Aberta", index=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    atualizado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False,
    )

    cartao_credito = db.relationship("FinanceiroCartaoCredito", back_populates="faturas")
    titulos = db.relationship("FinanceiroContaPagarTitulo", back_populates="fatura_cartao")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])

    __table_args__ = (
        db.UniqueConstraint("cartao_credito_id", "competencia", name="uq_fin_cartao_fatura_competencia"),
        db.CheckConstraint("valor_total >= 0", name="ck_fin_fatura_valor_total"),
        db.CheckConstraint("valor_pago >= 0", name="ck_fin_fatura_valor_pago"),
        db.CheckConstraint(
            "status in ('Aberta', 'Fechada', 'Agendada', 'Paga', 'Vencida', 'Cancelada')",
            name="ck_fin_fatura_status",
        ),
    )

    @property
    def competencia_formatada(self):
        return self.competencia.strftime("%m/%Y") if self.competencia else "-"

    def status_exibicao(self, hoje=None):
        from datetime import date

        hoje = hoje or date.today()
        if self.status not in ("Paga", "Cancelada") and self.data_vencimento and self.data_vencimento < hoje:
            return "Vencida"
        return self.status

    def __repr__(self):
        return f"<FinanceiroCartaoFatura {self.id} {self.competencia}>"


class FinanceiroContaPagarTitulo(db.Model):
    __tablename__ = "financeiro_contas_pagar_titulos"

    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_fornecedores.id"),
        nullable=True,
        index=True,
    )
    fornecedor_nome_snapshot = db.Column(db.String(180), nullable=False, index=True)
    fornecedor_cnpj_cpf_snapshot = db.Column(db.String(14), nullable=True, index=True)
    descricao = db.Column(db.String(220), nullable=False, index=True)
    numero_documento = db.Column(db.String(80), nullable=True, index=True)
    numero_nfe = db.Column(db.String(20), nullable=True, index=True)
    chave_acesso_nfe = db.Column(db.String(44), nullable=True, index=True)
    ordem_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordens_compra.id"),
        nullable=True,
        index=True,
    )
    fiscal_documento_id = db.Column(
        db.Integer,
        db.ForeignKey("fiscal_documentos.id"),
        nullable=True,
        index=True,
    )
    cartao_credito_id = db.Column(
        db.Integer,
        db.ForeignKey("financeiro_cartoes_credito.id"),
        nullable=True,
        index=True,
    )
    fatura_cartao_id = db.Column(
        db.Integer,
        db.ForeignKey("financeiro_cartoes_faturas.id"),
        nullable=True,
        index=True,
    )
    origem_lancamento = db.Column(db.String(30), nullable=False, index=True)
    tipo_pagamento = db.Column(db.String(30), nullable=False, index=True)
    forma_pagamento = db.Column(db.String(30), nullable=False, index=True)
    competencia = db.Column(db.Date, nullable=True, index=True)
    data_emissao = db.Column(db.Date, nullable=True)
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    data_compra_cartao = db.Column(db.Date, nullable=True, index=True)
    competencia_fatura_cartao = db.Column(db.Date, nullable=True, index=True)
    data_pagamento = db.Column(db.Date, nullable=True, index=True)
    valor_original = db.Column(db.Numeric(12, 2), nullable=False)
    valor_desconto = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    valor_acrescimo = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    valor_juros_multa = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    valor_pago = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    parcela_numero = db.Column(db.Integer, default=1, nullable=False)
    total_parcelas = db.Column(db.Integer, default=1, nullable=False)
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    sub_centro_custo_equipe_id = db.Column(
        db.Integer,
        db.ForeignKey("equipes.id"),
        nullable=True,
        index=True,
    )
    sub_centro_custo_veiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("operacao_veiculos_equipamentos.id"),
        nullable=True,
        index=True,
    )
    status = db.Column(db.String(30), nullable=False, default="Agendado", index=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    atualizado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False,
    )

    fornecedor = db.relationship("SuprimentosFornecedor")
    ordem_compra = db.relationship("SuprimentosOrdemCompra")
    fiscal_documento = db.relationship("FiscalDocumento")
    cartao_credito = db.relationship("FinanceiroCartaoCredito", back_populates="titulos")
    fatura_cartao = db.relationship("FinanceiroCartaoFatura", back_populates="titulos")
    centro_custo = db.relationship("CentroCusto")
    sub_centro_custo_equipe = db.relationship("Equipe")
    sub_centro_custo_veiculo = db.relationship("OperacaoVeiculoEquipamento")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])

    __table_args__ = (
        db.CheckConstraint(
            "origem_lancamento in ('Manual', 'Ordem de Compra', 'XML Fiscal', 'Cartao de Credito')",
            name="ck_financeiro_cp_origem_lancamento",
        ),
        db.CheckConstraint(
            "tipo_pagamento in ('Faturado', 'Cartao de Credito')",
            name="ck_financeiro_cp_tipo_pagamento",
        ),
        db.CheckConstraint(
            "forma_pagamento in ('Boleto', 'Pix', 'Transferencia', 'Deposito', 'Cartao de Credito', 'Outro')",
            name="ck_financeiro_cp_forma_pagamento",
        ),
        db.CheckConstraint(
            "status in ('Rascunho', 'Aguardando conferencia', 'Agendado', 'A vencer', 'Vencido', 'Pago', 'Pago parcialmente', 'Cancelado', 'Estornado')",
            name="ck_financeiro_cp_status",
        ),
        db.CheckConstraint("valor_original > 0", name="ck_financeiro_cp_valor_original"),
        db.CheckConstraint("valor_desconto >= 0", name="ck_financeiro_cp_valor_desconto"),
        db.CheckConstraint("valor_acrescimo >= 0", name="ck_financeiro_cp_valor_acrescimo"),
        db.CheckConstraint("valor_juros_multa >= 0", name="ck_financeiro_cp_valor_juros_multa"),
        db.CheckConstraint("valor_pago >= 0", name="ck_financeiro_cp_valor_pago"),
        db.CheckConstraint("parcela_numero >= 1", name="ck_financeiro_cp_parcela_numero"),
        db.CheckConstraint("total_parcelas >= 1", name="ck_financeiro_cp_total_parcelas"),
        db.CheckConstraint("parcela_numero <= total_parcelas", name="ck_financeiro_cp_parcela_total"),
    )

    @property
    def valor_liquido_previsto(self):
        return (
            (self.valor_original or 0)
            - (self.valor_desconto or 0)
            + (self.valor_acrescimo or 0)
            + (self.valor_juros_multa or 0)
        )

    def status_exibicao(self, hoje=None):
        from datetime import date

        hoje = hoje or date.today()
        status_final = self.status in ("Pago", "Pago parcialmente", "Cancelado", "Estornado")
        if not status_final and self.data_vencimento and self.data_vencimento < hoje:
            return "Vencido"
        return self.status

    def __repr__(self):
        return f"<FinanceiroContaPagarTitulo {self.id} {self.fornecedor_nome_snapshot}>"

class SuprimentosItem(db.Model):
    __tablename__ = "suprimentos_itens"

    id = db.Column(db.Integer, primary_key=True)
    codigo_interno = db.Column(db.String(60), unique=True, nullable=True, index=True)
    descricao = db.Column(db.String(220), nullable=False)
    categoria_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_categorias_itens.id"),
        nullable=True,
        index=True,
    )
    unidade_medida_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_unidades_medida.id"),
        nullable=False,
        index=True,
    )
    centro_custo_padrao_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    tipo = db.Column(db.String(30), nullable=False)
    item_estocavel = db.Column(db.Boolean, default=False, nullable=False)
    ncm = db.Column(db.String(20), nullable=True)
    estoque_minimo = db.Column(db.Numeric(12, 3), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    categoria = db.relationship("SuprimentosCategoriaItem", back_populates="itens")
    unidade_medida = db.relationship("SuprimentosUnidadeMedida", back_populates="itens")
    centro_custo_padrao = db.relationship(
        "CentroCusto",
        back_populates="itens_suprimentos",
    )
    fornecedores = db.relationship(
        "SuprimentosFornecedorItem",
        back_populates="item",
        cascade="all, delete-orphan",
    )
    movimentacoes_estoque = db.relationship(
        "SuprimentosMovimentacaoEstoque",
        back_populates="item",
    )

    __table_args__ = (
        db.CheckConstraint(
            "tipo in ('material', 'servico', 'epi', 'ferramenta', 'peca', 'equipamento', 'consumo')",
            name="ck_suprimentos_itens_tipo",
        ),
        db.CheckConstraint(
            "estoque_minimo is null or estoque_minimo >= 0",
            name="ck_suprimentos_itens_estoque_minimo",
        ),
    )

    @property
    def saldo_estoque(self):
        return sum(
            (
                movimentacao.quantidade
                for movimentacao in self.movimentacoes_estoque
                if movimentacao.status == "Registrada"
            ),
            start=0,
        )

    def __repr__(self):
        return f"<SuprimentosItem {self.codigo_interno or ''} {self.descricao}>"


class SuprimentosFornecedorItem(db.Model):
    __tablename__ = "suprimentos_fornecedor_itens"

    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_fornecedores.id"),
        nullable=False,
        index=True,
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_itens.id"),
        nullable=False,
        index=True,
    )
    codigo_item_fornecedor = db.Column(db.String(80), nullable=True)
    descricao_item_fornecedor = db.Column(db.String(220), nullable=True)
    preco_referencia = db.Column(db.Numeric(12, 2), nullable=True)
    prazo_entrega_dias = db.Column(db.Integer, nullable=True)
    condicao_pagamento = db.Column(db.String(160), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    fornecedor_preferencial = db.Column(db.Boolean, default=False, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    fornecedor = db.relationship("SuprimentosFornecedor", back_populates="itens")
    item = db.relationship("SuprimentosItem", back_populates="fornecedores")

    __table_args__ = (
        db.UniqueConstraint(
            "fornecedor_id",
            "item_id",
            name="uq_suprimentos_fornecedor_item",
        ),
        db.CheckConstraint(
            "preco_referencia is null or preco_referencia >= 0",
            name="ck_suprimentos_fornecedor_itens_preco",
        ),
        db.CheckConstraint(
            "prazo_entrega_dias is null or prazo_entrega_dias >= 0",
            name="ck_suprimentos_fornecedor_itens_prazo",
        ),
    )

    def __repr__(self):
        return (
            f"<SuprimentosFornecedorItem fornecedor={self.fornecedor_id} "
            f"item={self.item_id}>"
        )


class SuprimentosRequisicaoCompra(db.Model):
    __tablename__ = "suprimentos_requisicoes_compra"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False, index=True)
    solicitante_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    sub_centro_custo_equipe_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    sub_centro_custo_veiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    equipe_id = db.Column(
        db.Integer,
        db.ForeignKey("equipes.id"),
        nullable=True,
        index=True,
    )
    veiculo_placa = db.Column(db.String(20), nullable=True)
    justificativa = db.Column(db.Text, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default="Rascunho", nullable=False, index=True)
    enviada_em = db.Column(db.DateTime, nullable=True)
    cancelada_em = db.Column(db.DateTime, nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    solicitante = db.relationship("Usuario")
    centro_custo = db.relationship("CentroCusto", foreign_keys=[centro_custo_id])
    sub_centro_custo_equipe = db.relationship("CentroCusto", foreign_keys=[sub_centro_custo_equipe_id])
    sub_centro_custo_veiculo = db.relationship("CentroCusto", foreign_keys=[sub_centro_custo_veiculo_id])
    equipe = db.relationship("Equipe")
    itens = db.relationship(
        "SuprimentosRequisicaoCompraItem",
        back_populates="requisicao",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "status in ('Rascunho', 'Enviada para Analise', 'Aprovada', 'Cancelada')",
            name="ck_suprimentos_requisicoes_compra_status",
        ),
    )

    @property
    def pode_editar(self):
        return self.status == "Rascunho"

    def __repr__(self):
        return f"<SuprimentosRequisicaoCompra {self.numero}>"


class SuprimentosRequisicaoCompraItem(db.Model):
    __tablename__ = "suprimentos_requisicao_compra_itens"

    id = db.Column(db.Integer, primary_key=True)
    requisicao_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_requisicoes_compra.id"),
        nullable=False,
        index=True,
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_itens.id"),
        nullable=False,
        index=True,
    )
    item_codigo_snapshot = db.Column(db.String(60), nullable=True)
    item_descricao_snapshot = db.Column(db.String(220), nullable=False)
    unidade_medida_snapshot = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    requisicao = db.relationship("SuprimentosRequisicaoCompra", back_populates="itens")
    item = db.relationship("SuprimentosItem")

    __table_args__ = (
        db.UniqueConstraint(
            "requisicao_id",
            "item_id",
            name="uq_suprimentos_requisicao_compra_item",
        ),
        db.CheckConstraint(
            "quantidade > 0",
            name="ck_suprimentos_requisicao_compra_itens_quantidade",
        ),
    )

    def __repr__(self):
        return (
            f"<SuprimentosRequisicaoCompraItem requisicao={self.requisicao_id} "
            f"item={self.item_id}>"
        )


class SuprimentosCotacao(db.Model):
    __tablename__ = "suprimentos_cotacoes"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False, index=True)
    requisicao_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_requisicoes_compra.id"),
        nullable=False,
        index=True,
    )
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(30), default="Aberta", nullable=False, index=True)
    observacoes = db.Column(db.Text, nullable=True)
    aberta_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    encerrada_em = db.Column(db.DateTime, nullable=True)
    enviada_aprovacao_em = db.Column(db.DateTime, nullable=True)
    aprovada_em = db.Column(db.DateTime, nullable=True)
    aprovada_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    aprovador_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    alcada_aprovacao_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_alcadas_aprovacao.id"),
        nullable=True,
        index=True,
    )
    reprovada_em = db.Column(db.DateTime, nullable=True)
    reprovada_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    observacoes_aprovacao = db.Column(db.Text, nullable=True)
    aprovacao_publica_token_hash = db.Column(db.String(64), nullable=True, unique=True, index=True)
    aprovacao_publica_expira_em = db.Column(db.DateTime, nullable=True, index=True)
    aprovacao_publica_usado_em = db.Column(db.DateTime, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    requisicao = db.relationship("SuprimentosRequisicaoCompra")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    aprovada_por = db.relationship("Usuario", foreign_keys=[aprovada_por_usuario_id])
    aprovador = db.relationship("Usuario", foreign_keys=[aprovador_usuario_id])
    alcada_aprovacao = db.relationship("SuprimentosAlcadaAprovacao")
    reprovada_por = db.relationship("Usuario", foreign_keys=[reprovada_por_usuario_id])
    propostas = db.relationship(
        "SuprimentosCotacaoProposta",
        back_populates="cotacao",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "status in ('Aberta', 'Em Aprovacao', 'Aprovada', 'Reprovada', 'Encerrada', 'Cancelada')",
            name="ck_suprimentos_cotacoes_status",
        ),
    )

    @property
    def pode_editar(self):
        return self.status in ["Aberta", "Reprovada"]

    def __repr__(self):
        return f"<SuprimentosCotacao {self.numero}>"


class SuprimentosAlcadaAprovacao(db.Model):
    __tablename__ = "suprimentos_alcadas_aprovacao"

    id = db.Column(db.Integer, primary_key=True)
    usuario_aprovador_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    categoria_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_categorias_itens.id"),
        nullable=True,
        index=True,
    )
    valor_minimo = db.Column(db.Numeric(12, 2), nullable=False)
    valor_maximo = db.Column(db.Numeric(12, 2), nullable=True)
    telefone_whatsapp = db.Column(db.String(20), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    usuario_aprovador = db.relationship("Usuario")
    centro_custo = db.relationship("CentroCusto")
    categoria = db.relationship("SuprimentosCategoriaItem")

    __table_args__ = (
        db.CheckConstraint(
            "valor_minimo >= 0",
            name="ck_suprimentos_alcadas_valor_minimo",
        ),
        db.CheckConstraint(
            "valor_maximo is null or valor_maximo >= valor_minimo",
            name="ck_suprimentos_alcadas_valor_maximo",
        ),
    )

    def __repr__(self):
        return f"<SuprimentosAlcadaAprovacao usuario={self.usuario_aprovador_id}>"


class SuprimentosComprador(db.Model):
    __tablename__ = "suprimentos_compradores"

    id = db.Column(db.Integer, primary_key=True)
    usuario_comprador_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    nome = db.Column(db.String(120), nullable=False)
    telefone_whatsapp = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    usuario_comprador = db.relationship("Usuario")
    centro_custo = db.relationship("CentroCusto")

    def __repr__(self):
        return f"<SuprimentosComprador {self.nome}>"


class SuprimentosCotacaoProposta(db.Model):
    __tablename__ = "suprimentos_cotacao_propostas"

    id = db.Column(db.Integer, primary_key=True)
    cotacao_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_cotacoes.id"),
        nullable=False,
        index=True,
    )
    fornecedor_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_fornecedores.id"),
        nullable=False,
        index=True,
    )
    requisicao_item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_requisicao_compra_itens.id"),
        nullable=False,
        index=True,
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_itens.id"),
        nullable=False,
        index=True,
    )
    fornecedor_razao_social_snapshot = db.Column(db.String(180), nullable=False)
    item_descricao_snapshot = db.Column(db.String(220), nullable=False)
    unidade_medida_snapshot = db.Column(db.String(20), nullable=False)
    quantidade_snapshot = db.Column(db.Numeric(12, 3), nullable=False)
    preco_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    prazo_entrega_dias = db.Column(db.Integer, nullable=True)
    condicao_pagamento = db.Column(db.String(160), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    selecionada = db.Column(db.Boolean, default=False, nullable=False, index=True)
    justificativa_selecao = db.Column(db.Text, nullable=True)
    selecionada_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    selecionada_em = db.Column(db.DateTime, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    cotacao = db.relationship("SuprimentosCotacao", back_populates="propostas")
    fornecedor = db.relationship("SuprimentosFornecedor")
    requisicao_item = db.relationship("SuprimentosRequisicaoCompraItem")
    item = db.relationship("SuprimentosItem")
    selecionada_por = db.relationship("Usuario")

    __table_args__ = (
        db.UniqueConstraint(
            "cotacao_id",
            "fornecedor_id",
            "requisicao_item_id",
            name="uq_suprimentos_cotacao_fornecedor_item",
        ),
        db.CheckConstraint(
            "preco_unitario >= 0",
            name="ck_suprimentos_cotacao_propostas_preco_unitario",
        ),
        db.CheckConstraint(
            "prazo_entrega_dias is null or prazo_entrega_dias >= 0",
            name="ck_suprimentos_cotacao_propostas_prazo",
        ),
    )

    @property
    def valor_total(self):
        return self.quantidade_snapshot * self.preco_unitario

    def __repr__(self):
        return (
            f"<SuprimentosCotacaoProposta cotacao={self.cotacao_id} "
            f"fornecedor={self.fornecedor_id} item={self.item_id}>"
        )


class SuprimentosOrdemCompra(db.Model):
    __tablename__ = "suprimentos_ordens_compra"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False, index=True)
    cotacao_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_cotacoes.id"),
        nullable=False,
        index=True,
    )
    requisicao_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_requisicoes_compra.id"),
        nullable=False,
        index=True,
    )
    fornecedor_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_fornecedores.id"),
        nullable=False,
        index=True,
    )
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    fornecedor_razao_social_snapshot = db.Column(db.String(180), nullable=False)
    fornecedor_cnpj_cpf_snapshot = db.Column(db.String(20), nullable=True)
    condicao_pagamento_snapshot = db.Column(db.String(160), nullable=True)
    status = db.Column(db.String(30), default="Gerada", nullable=False, index=True)
    status_financeiro = db.Column(db.String(30), default="Pendente de Financeiro", nullable=False, index=True)
    previsao_vencimento = db.Column(db.Date, nullable=True, index=True)
    quantidade_parcelas = db.Column(db.Integer, default=1, nullable=False)
    observacoes_financeiras = db.Column(db.Text, nullable=True)
    preparado_financeiro_em = db.Column(db.DateTime, nullable=True)
    provisionado_financeiro_em = db.Column(db.DateTime, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    gerada_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    cancelada_em = db.Column(db.DateTime, nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    cotacao = db.relationship("SuprimentosCotacao")
    requisicao = db.relationship("SuprimentosRequisicaoCompra")
    fornecedor = db.relationship("SuprimentosFornecedor")
    criado_por = db.relationship("Usuario")
    itens = db.relationship(
        "SuprimentosOrdemCompraItem",
        back_populates="ordem_compra",
        cascade="all, delete-orphan",
    )
    evidencias_itens = db.relationship(
        "SuprimentosOrdemCompraItemEvidencia",
        back_populates="ordem_compra",
        cascade="all, delete-orphan",
    )
    recebimentos = db.relationship(
        "SuprimentosRecebimentoCompra",
        back_populates="ordem_compra",
        cascade="all, delete-orphan",
    )
    parcelas_financeiras = db.relationship(
        "SuprimentosOrdemCompraParcela",
        back_populates="ordem_compra",
        cascade="all, delete-orphan",
        order_by="SuprimentosOrdemCompraParcela.numero_parcela",
    )
    documentos_fiscais = db.relationship(
        "FiscalDocumento",
        back_populates="ordem_compra",
        order_by="FiscalDocumento.data_emissao.desc()",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "cotacao_id",
            "fornecedor_id",
            name="uq_suprimentos_ordens_compra_cotacao_fornecedor",
        ),
        db.CheckConstraint(
            "status in ('Gerada', 'Parcialmente Recebida', 'Recebida', 'Cancelada')",
            name="ck_suprimentos_ordens_compra_status",
        ),
        db.CheckConstraint(
            "status_financeiro in ('Pendente de Financeiro', 'Preparado para Financeiro', 'Provisionado', 'Cancelado')",
            name="ck_suprimentos_ordens_compra_status_financeiro",
        ),
        db.CheckConstraint(
            "quantidade_parcelas >= 1",
            name="ck_suprimentos_ordens_compra_qtd_parcelas",
        ),
    )

    @property
    def valor_total(self):
        return sum((item.valor_total for item in self.itens), start=0)

    @property
    def pode_cancelar(self):
        return self.status == "Gerada"

    @property
    def pode_receber(self):
        return self.status in ["Gerada", "Parcialmente Recebida"]

    def __repr__(self):
        return f"<SuprimentosOrdemCompra {self.numero}>"


class FiscalCertificadoA1(db.Model):
    __tablename__ = "fiscal_certificados_a1"

    id = db.Column(db.Integer, primary_key=True)
    cnpj_empresa = db.Column(db.String(14), nullable=False, index=True)
    razao_social = db.Column(db.String(180), nullable=False)
    nome_arquivo_original = db.Column(db.String(180), nullable=False)
    arquivo_path = db.Column(db.String(500), nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    senha_criptografada = db.Column(db.Text, nullable=True)
    validade = db.Column(db.Date, nullable=True, index=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    observacoes = db.Column(db.Text, nullable=True)
    cadastrado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    cadastrado_por = db.relationship("Usuario")

    def __repr__(self):
        return f"<FiscalCertificadoA1 {self.cnpj_empresa}>"


class FiscalControleNSU(db.Model):
    __tablename__ = "fiscal_controles_nsu"

    id = db.Column(db.Integer, primary_key=True)
    cnpj_empresa = db.Column(db.String(14), unique=True, nullable=False, index=True)
    ultimo_nsu = db.Column(db.String(20), default="0", nullable=False)
    max_nsu = db.Column(db.String(20), nullable=True)
    consultado_em = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), default="Pendente", nullable=False, index=True)
    mensagem = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    def __repr__(self):
        return f"<FiscalControleNSU {self.cnpj_empresa} nsu={self.ultimo_nsu}>"


class FiscalDocumento(db.Model):
    __tablename__ = "fiscal_documentos"

    id = db.Column(db.Integer, primary_key=True)
    chave_acesso = db.Column(db.String(44), unique=True, nullable=False, index=True)
    nsu = db.Column(db.String(20), nullable=True, index=True)
    modelo = db.Column(db.String(10), default="55", nullable=False, index=True)
    serie = db.Column(db.String(10), nullable=True)
    numero = db.Column(db.String(20), nullable=False, index=True)
    natureza_operacao = db.Column(db.String(180), nullable=True)
    data_emissao = db.Column(db.DateTime, nullable=True, index=True)
    emitente_nome = db.Column(db.String(180), nullable=False, index=True)
    emitente_cnpj = db.Column(db.String(14), nullable=False, index=True)
    destinatario_nome = db.Column(db.String(180), nullable=True)
    destinatario_cnpj = db.Column(db.String(14), nullable=False, index=True)
    valor_total = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    xml_path = db.Column(db.String(500), nullable=True)
    danfe_path = db.Column(db.String(500), nullable=True)
    tipo_distribuicao = db.Column(db.String(30), default="procNFe", nullable=False, index=True)
    tem_xml_completo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    manifestacao_status = db.Column(db.String(40), nullable=True, index=True)
    manifestacao_evento = db.Column(db.String(40), nullable=True)
    manifestacao_protocolo = db.Column(db.String(80), nullable=True)
    manifestacao_em = db.Column(db.DateTime, nullable=True)
    manifestado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    xml_completo_baixado_em = db.Column(db.DateTime, nullable=True)
    ultima_consulta_em = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(40), default="XML baixado", nullable=False, index=True)
    ordem_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordens_compra.id"),
        nullable=True,
        index=True,
    )
    vinculado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    vinculado_em = db.Column(db.DateTime, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    ordem_compra = db.relationship("SuprimentosOrdemCompra", back_populates="documentos_fiscais")
    vinculado_por = db.relationship("Usuario", foreign_keys=[vinculado_por_usuario_id])
    manifestado_por = db.relationship("Usuario", foreign_keys=[manifestado_por_usuario_id])
    manifestacoes = db.relationship(
        "FiscalManifestacaoNFe",
        back_populates="documento",
        cascade="all, delete-orphan",
        order_by="FiscalManifestacaoNFe.criado_em.desc()",
    )

    __table_args__ = (
        db.CheckConstraint(
            "status in ('Resumo localizado', 'Aguardando manifestacao', 'Ciencia registrada', 'XML baixado', 'Vinculado a OC', 'Confirmada', 'Desconhecida', 'Operacao nao realizada', 'Cancelada')",
            name="ck_fiscal_documentos_status",
        ),
    )

    @property
    def vinculado(self):
        return self.ordem_compra_id is not None

    @property
    def xml_disponivel(self):
        return bool(self.tem_xml_completo and self.xml_path)

    def __repr__(self):
        return f"<FiscalDocumento {self.chave_acesso}>"


class FiscalManifestacaoNFe(db.Model):
    __tablename__ = "fiscal_manifestacoes_nfe"

    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(
        db.Integer,
        db.ForeignKey("fiscal_documentos.id"),
        nullable=False,
        index=True,
    )
    chave_acesso = db.Column(db.String(44), nullable=False, index=True)
    evento = db.Column(db.String(40), nullable=False, index=True)
    status_retorno = db.Column(db.String(20), nullable=True)
    motivo_retorno = db.Column(db.Text, nullable=True)
    protocolo = db.Column(db.String(80), nullable=True)
    xml_evento_path = db.Column(db.String(500), nullable=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)

    documento = db.relationship("FiscalDocumento", back_populates="manifestacoes")
    usuario = db.relationship("Usuario")

    def __repr__(self):
        return f"<FiscalManifestacaoNFe {self.chave_acesso} {self.evento}>"


class SuprimentosOrdemCompraParcela(db.Model):
    __tablename__ = "suprimentos_ordem_compra_parcelas"

    id = db.Column(db.Integer, primary_key=True)
    ordem_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordens_compra.id"),
        nullable=False,
        index=True,
    )
    numero_parcela = db.Column(db.Integer, nullable=False)
    valor_previsto = db.Column(db.Numeric(12, 2), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(30), default="Prevista", nullable=False, index=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    ordem_compra = db.relationship("SuprimentosOrdemCompra", back_populates="parcelas_financeiras")

    __table_args__ = (
        db.UniqueConstraint(
            "ordem_compra_id",
            "numero_parcela",
            name="uq_suprimentos_oc_parcela_numero",
        ),
        db.CheckConstraint(
            "numero_parcela >= 1",
            name="ck_suprimentos_oc_parcelas_numero",
        ),
        db.CheckConstraint(
            "valor_previsto >= 0",
            name="ck_suprimentos_oc_parcelas_valor",
        ),
        db.CheckConstraint(
            "status in ('Prevista', 'Cancelada')",
            name="ck_suprimentos_oc_parcelas_status",
        ),
    )

    def __repr__(self):
        return f"<SuprimentosOrdemCompraParcela ordem={self.ordem_compra_id} parcela={self.numero_parcela}>"


class SuprimentosOrdemCompraItem(db.Model):
    __tablename__ = "suprimentos_ordem_compra_itens"

    id = db.Column(db.Integer, primary_key=True)
    ordem_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordens_compra.id"),
        nullable=False,
        index=True,
    )
    cotacao_proposta_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_cotacao_propostas.id"),
        nullable=False,
        index=True,
    )
    requisicao_item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_requisicao_compra_itens.id"),
        nullable=False,
        index=True,
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_itens.id"),
        nullable=False,
        index=True,
    )
    item_codigo_snapshot = db.Column(db.String(60), nullable=True)
    item_descricao_snapshot = db.Column(db.String(220), nullable=False)
    unidade_medida_snapshot = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    preco_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    prazo_entrega_dias = db.Column(db.Integer, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    ordem_compra = db.relationship("SuprimentosOrdemCompra", back_populates="itens")
    proposta = db.relationship("SuprimentosCotacaoProposta")
    requisicao_item = db.relationship("SuprimentosRequisicaoCompraItem")
    item = db.relationship("SuprimentosItem")
    recebimentos = db.relationship(
        "SuprimentosRecebimentoCompraItem",
        back_populates="ordem_compra_item",
        cascade="all, delete-orphan",
    )
    evidencia = db.relationship(
        "SuprimentosOrdemCompraItemEvidencia",
        back_populates="ordem_compra_item",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "ordem_compra_id",
            "cotacao_proposta_id",
            name="uq_suprimentos_oc_item_proposta",
        ),
        db.CheckConstraint(
            "quantidade > 0",
            name="ck_suprimentos_oc_itens_quantidade",
        ),
        db.CheckConstraint(
            "preco_unitario >= 0",
            name="ck_suprimentos_oc_itens_preco_unitario",
        ),
        db.CheckConstraint(
            "prazo_entrega_dias is null or prazo_entrega_dias >= 0",
            name="ck_suprimentos_oc_itens_prazo",
        ),
    )

    @property
    def valor_total(self):
        return self.quantidade * self.preco_unitario

    @property
    def quantidade_recebida(self):
        return sum(
            (
                recebimento.quantidade_recebida
                for recebimento in self.recebimentos
                if recebimento.recebimento and recebimento.recebimento.status == "Registrado"
            ),
            start=0,
        )

    @property
    def saldo_receber(self):
        return self.quantidade - self.quantidade_recebida

    def __repr__(self):
        return f"<SuprimentosOrdemCompraItem ordem={self.ordem_compra_id} item={self.item_id}>"


class SuprimentosOrdemCompraItemEvidencia(db.Model):
    __tablename__ = "suprimentos_oc_item_evidencias"

    id = db.Column(db.Integer, primary_key=True)
    ordem_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordens_compra.id"),
        nullable=False,
        index=True,
    )
    ordem_compra_item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordem_compra_itens.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    numero_oc_snapshot = db.Column(db.String(30), nullable=False)
    numero_item_snapshot = db.Column(db.String(20), nullable=False)
    descricao_item_snapshot = db.Column(db.String(220), nullable=False)
    unidade_medida_snapshot = db.Column(db.String(20), nullable=False)
    quantidade_snapshot = db.Column(db.Numeric(12, 3), nullable=False)
    destino_real = db.Column(db.Text, nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    data_evidencia = db.Column(db.Date, nullable=False, index=True)
    foto_1_drive_file_id = db.Column(db.String(120), nullable=False)
    foto_1_nome_arquivo = db.Column(db.String(180), nullable=False)
    foto_1_link = db.Column(db.String(500), nullable=True)
    foto_2_drive_file_id = db.Column(db.String(120), nullable=True)
    foto_2_nome_arquivo = db.Column(db.String(180), nullable=True)
    foto_2_link = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(30), default="Evidenciado", nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    ordem_compra = db.relationship("SuprimentosOrdemCompra", back_populates="evidencias_itens")
    ordem_compra_item = db.relationship("SuprimentosOrdemCompraItem", back_populates="evidencia")
    criado_por = db.relationship("Usuario")

    __table_args__ = (
        db.CheckConstraint(
            "status in ('Pendente', 'Evidenciado', 'Cancelado')",
            name="ck_suprimentos_oc_item_evidencias_status",
        ),
    )

    @property
    def possui_foto_2(self):
        return bool(self.foto_2_drive_file_id)

    def __repr__(self):
        return f"<SuprimentosOrdemCompraItemEvidencia oc_item={self.ordem_compra_item_id}>"


class SuprimentosRecebimentoCompra(db.Model):
    __tablename__ = "suprimentos_recebimentos_compra"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False, index=True)
    ordem_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordens_compra.id"),
        nullable=False,
        index=True,
    )
    recebido_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(30), default="Registrado", nullable=False, index=True)
    tipo_documento = db.Column(db.String(30), nullable=False)
    numero_documento = db.Column(db.String(80), nullable=False)
    data_documento = db.Column(db.Date, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    recebido_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    ordem_compra = db.relationship("SuprimentosOrdemCompra", back_populates="recebimentos")
    recebido_por = db.relationship("Usuario")
    itens = db.relationship(
        "SuprimentosRecebimentoCompraItem",
        back_populates="recebimento",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "status in ('Registrado', 'Cancelado')",
            name="ck_suprimentos_recebimentos_compra_status",
        ),
        db.CheckConstraint(
            "tipo_documento in ('Nota Fiscal', 'Cupom Fiscal', 'Romaneio', 'Outro')",
            name="ck_suprimentos_recebimentos_tipo_documento",
        ),
    )

    def __repr__(self):
        return f"<SuprimentosRecebimentoCompra {self.numero}>"


class SuprimentosRecebimentoCompraItem(db.Model):
    __tablename__ = "suprimentos_recebimento_compra_itens"

    id = db.Column(db.Integer, primary_key=True)
    recebimento_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_recebimentos_compra.id"),
        nullable=False,
        index=True,
    )
    ordem_compra_item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordem_compra_itens.id"),
        nullable=False,
        index=True,
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_itens.id"),
        nullable=False,
        index=True,
    )
    item_codigo_snapshot = db.Column(db.String(60), nullable=True)
    item_descricao_snapshot = db.Column(db.String(220), nullable=False)
    unidade_medida_snapshot = db.Column(db.String(20), nullable=False)
    quantidade_recebida = db.Column(db.Numeric(12, 3), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    recebimento = db.relationship("SuprimentosRecebimentoCompra", back_populates="itens")
    ordem_compra_item = db.relationship("SuprimentosOrdemCompraItem", back_populates="recebimentos")
    item = db.relationship("SuprimentosItem")
    movimentacao_estoque = db.relationship(
        "SuprimentosMovimentacaoEstoque",
        back_populates="recebimento_item",
        uselist=False,
    )

    __table_args__ = (
        db.CheckConstraint(
            "quantidade_recebida > 0",
            name="ck_suprimentos_recebimento_itens_quantidade",
        ),
    )

    def __repr__(self):
        return f"<SuprimentosRecebimentoCompraItem recebimento={self.recebimento_id} item={self.item_id}>"


class SuprimentosMovimentacaoEstoque(db.Model):
    __tablename__ = "suprimentos_movimentacoes_estoque"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_itens.id"),
        nullable=False,
        index=True,
    )
    recebimento_item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_recebimento_compra_itens.id"),
        nullable=True,
        unique=True,
        index=True,
    )
    ordem_compra_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_ordens_compra.id"),
        nullable=True,
        index=True,
    )
    fornecedor_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_fornecedores.id"),
        nullable=True,
        index=True,
    )
    responsavel_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    tipo = db.Column(db.String(20), nullable=False)
    origem = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), default="Registrada", nullable=False, index=True)
    documento_tipo = db.Column(db.String(30), nullable=True)
    documento_numero = db.Column(db.String(80), nullable=True)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    valor_unitario = db.Column(db.Numeric(12, 2), nullable=True)
    valor_total_snapshot = db.Column(db.Numeric(12, 2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    movimentado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    item = db.relationship("SuprimentosItem", back_populates="movimentacoes_estoque")
    recebimento_item = db.relationship(
        "SuprimentosRecebimentoCompraItem",
        back_populates="movimentacao_estoque",
    )
    ordem_compra = db.relationship("SuprimentosOrdemCompra")
    fornecedor = db.relationship("SuprimentosFornecedor")
    responsavel = db.relationship("Usuario")

    __table_args__ = (
        db.CheckConstraint(
            "tipo in ('Entrada', 'Saida')",
            name="ck_suprimentos_movimentacoes_estoque_tipo",
        ),
        db.CheckConstraint(
            "status in ('Registrada', 'Cancelada')",
            name="ck_suprimentos_movimentacoes_estoque_status",
        ),
        db.CheckConstraint(
            "quantidade <> 0",
            name="ck_suprimentos_movimentacoes_estoque_quantidade",
        ),
    )

    def __repr__(self):
        return f"<SuprimentosMovimentacaoEstoque {self.tipo} item={self.item_id}>"


class SegurancaTrabalhoEntregaEpi(db.Model):
    __tablename__ = "seguranca_trabalho_entregas_epi"

    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=False,
        index=True,
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_itens.id"),
        nullable=False,
        index=True,
    )
    movimentacao_estoque_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_movimentacoes_estoque.id"),
        nullable=True,
        unique=True,
        index=True,
    )
    entregue_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    tipo_material = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    data_entrega = db.Column(db.Date, nullable=False, index=True)
    ca_numero = db.Column(db.String(80), nullable=True)
    tamanho = db.Column(db.String(40), nullable=True)
    motivo_entrega = db.Column(db.String(160), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    colaborador = db.relationship("Colaborador")
    item = db.relationship("SuprimentosItem")
    movimentacao_estoque = db.relationship("SuprimentosMovimentacaoEstoque")
    entregue_por = db.relationship("Usuario")

    __table_args__ = (
        db.CheckConstraint(
            "tipo_material in ('EPI', 'Uniforme')",
            name="ck_seguranca_entregas_epi_tipo_material",
        ),
        db.CheckConstraint(
            "quantidade > 0",
            name="ck_seguranca_entregas_epi_quantidade",
        ),
    )

    def __repr__(self):
        return f"<SegurancaTrabalhoEntregaEpi colaborador={self.colaborador_id} item={self.item_id}>"
