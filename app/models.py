Warning: truncated output (original token count: 45622)
Total output lines: 4332

from decimal import Decimal
import uuid

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
    vinculo_id = db.Column(db.Integer, db.ForeignKey("operacao_veiculos_responsaveis.id"), nullable=True, index=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=True, index=True)
    equipe_id = db.Column(db.Integer, db.ForeignKey("equipes.id"), nullable=True, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    data_abastecimento = db.Column(db.Date, nullable=False, index=True)
    tipo_leitura = db.Column(db.String(20), nullable=False, default="odometro")
    leitura_atual = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    tipo_combustivel = db.Column(db.String(40), nullable=False, index=True)
    qtd_litros = db.Column(db.Numeric(12, 3), nullable=False)
    preco = db.Column(db.Numeric(12, 2), nullable=False)
    cupom_drive_file_id = db.Column(db.String(255), nullable=True)
    cupom_nome_arquivo = db.Column(db.String(255), nullable=True)
    cupom_link = db.Column(db.String(500), nullable=True)
    numero_nota_fiscal = db.Column(db.String(80), nullable=True)
    chave_acesso_nfe = db.Column(db.String(44), nullable=True)
    fiscal_documento_id = db.Column(db.Integer, db.ForeignKey("fiscal_documentos.id"), nullable=True, index=True)
    valor_total_nota_fiscal = db.Column(db.Numeric(12, 2), nullable=True)
    observacoes_conferencia = db.Column(db.Text, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    veiculo = db.relationship("OperacaoVeiculoEquipamento", back_populates="abastecimentos")
    vinculo = db.relationship("OperacaoVeiculoResponsavel")
    colaborador = db.relationship("Colaborador")
    equipe = db.relationship("Equipe")
    usuario = db.relationship("Usuario")
    fiscal_documento = db.relationship("FiscalDocumento")
    custos_extras = db.relationship(
        "OperacaoAbastecimentoCustoExtra",
        back_populates="abastecimento",
        order_by="OperacaoAbastecimentoCustoExtra.id.asc()",
    )

    @property
    def valor_total_combustivel(self):
        """Total do combust�vel: quantidade abastecida multiplicada pelo pre�o unit�rio."""
        return ((self.qtd_litros or 0) * (self.preco or 0)).quantize(Decimal("0.01"))

    @property
    def custos_extras_ativos(self):
        return [custo for custo in self.custos_extras if custo.status == "Ativo"]

    @property
    def valor_total_custos_extras(self):
        return sum((custo.valor_total or 0 for custo in self.custos_extras_ativos), start=0)

    @property
    def valor_total_geral(self):
        return (self.valor_total_combustivel or 0) + (self.valor_total_custos_extras or 0)

    @property
    def diferenca_nota_fiscal(self):
        if self.valor_total_nota_fiscal is None:
            return None
        return self.valor_total_nota_fiscal - self.valor_total_geral

    @property
    def status_conferencia_nota_fiscal(self):
        if self.valor_total_nota_fiscal is None:
            return "Sem valor da NF"
        return "Conferido" if self.diferenca_nota_fiscal == 0 else "Divergente"

    __table_args__ = (
        db.CheckConstraint(
            "tipo_combustivel in ('Diesel S10', 'Etanol', 'Etanol aditivado', 'Gasolina comum', 'Gasolina aditivada', 'Gasolina Premium')",
            name="ck_operacao_abastecimentos_tipo_combustivel",
        ),
        db.CheckConstraint(
            "tipo_leitura in ('odometro', 'horimetro')",
            name="ck_operacao_abastecimentos_tipo_leitura",
        ),
        db.CheckConstraint("leitura_atual >= 0", name="ck_operacao_abastecimentos_leitura_atual"),
        db.CheckConstraint("qtd_litros > 0", name="ck_operacao_abastecimentos_qtd_litros"),
        db.CheckConstraint("preco >= 0", name="ck_operacao_abastecimentos_preco"),
    )

    def __repr__(self):
        return f"<OperacaoAbastecimento veiculo={self.veiculo_id} data={self.data_abastecimento}>"

class OperacaoAbastecimentoCustoExtra(db.Model):
    __tablename__ = "operacao_abastecimento_custos_extras"

    id = db.Column(db.Integer, primary_key=True)
    abastecimento_id = db.Column(db.Integer, db.ForeignKey("operacao_abastecimentos.id"), nullable=False, index=True)
    categoria = db.Column(db.String(80), nullable=True, index=True)
    descricao = db.Column(db.String(255), nullable=True)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    valor_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="Ativo", nullable=False, index=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    atualizado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    cancelado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False, index=True)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    abastecimento = db.relationship("OperacaoAbastecimento", back_populates="custos_extras")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_usuario_id])

    __table_args__ = (
        db.CheckConstraint("quantidade > 0", name="ck_operacao_abast_extra_quantidade"),
        db.CheckConstraint("valor_unitario >= 0", name="ck_operacao_abast_extra_unitario"),
        db.CheckConstraint("valor_total >= 0", name="ck_operacao_abast_extra_total"),
        db.CheckConstraint("status in ('Ativo', 'Cancelado')", name="ck_operacao_abast_extra_status"),
    )

    def __repr__(self):
        return f"<OperacaoAbastecimentoCustoExtra abastecimento={self.abastecimento_id} categoria={self.categoria}>"

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
    valor_multa = db.Column(db.Numeric(12, 2), nullable=True)
    data_vencimento = db.Column(db.Date, nullable=True)
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

    @property
    def boleto_cadastrado(self):
        return self.valor_multa is not None and self.data_vencimento is not None

    @property
    def status_boleto(self):
        return "Boleto cadastrado" if self.boleto_cadastrado else "Aguardando boleto"

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


class FinanceiroCliente(db.Model):
    __tablename__ = "financeiro_clientes"

    id = db.Column(db.Integer, primary_key=True)
    tipo_pessoa = db.Column(db.String(20), nullable=False, default="juridica")
    cnpj_cpf = db.Column(db.String(20), nullable=False)
    cnpj_cpf_normalizado = db.Column(db.String(14), nullable=False, unique=True, index=True)
    razao_social = db.Column(db.String(180), nullable=False, index=True)
    nome_fantasia = db.Column(db.String(180), nullable=True, index=True)
    inscricao_estadual = db.Column(db.String(40), nullable=True)
    inscricao_municipal = db.Column(db.String(40), nullable=True)
    email_financeiro = db.Column(db.String(150), nullable=True)
    email_alternativo = db.Column(db.String(150), nullable=True)
    telefone_principal = db.Column(db.String(30), nullable=True)
    telefone_alternativo = db.Column(db.String(30), nullable=True)
    contato_responsavel = db.Column(db.String(120), nullable=True)
    cargo_contato = db.Column(db.String(120), nullable=True)
    endereco = db.Column(db.String(255), nullable=True)
    numero = db.Column(db.String(30), nullable=True)
    complemento = db.Column(db.String(120), nullable=True)
    bairro = db.Column(db.String(120), nullable=True)
    cidade = db.Column(db.String(120), nullable=True, index=True)
    uf = db.Column(db.String(2), nullable=True, index=True)
    cep = db.Column(db.String(20), nullable=True)
    condicao_recebimento_padrao = db.Column(db.String(120), nullable=True)
    prazo_vencimento_padrao = db.Column(db.Integer, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    atualizado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    inativado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    inativado_em = db.Column(db.DateTime, nullable=True)
    motivo_inativacao = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    inativado_por = db.relationship("Usuario", foreign_keys=[inativado_por_usuario_id])

    __table_args__ = (
        db.CheckConstraint("tipo_pessoa in ('juridica', 'fisica')", name="ck_fin_clientes_tipo_pessoa"),
        db.CheckConstraint(
            "prazo_vencimento_padrao is null or prazo_vencimento_padrao >= 0",
            name="ck_fin_clientes_prazo_vencimento",
        ),
    )

    def __repr__(self):
        return f"<FinanceiroCliente {self.id} {self.razao_social}>"

class FinanceiroContaReceberTitulo(db.Model):
    __tablename__ = "financeiro_contas_receber_titulos"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("financeiro_clientes.id"), nullable=True, index=True)
    cliente_nome_snapshot = db.Column(db.String(180), nullable=False, index=True)
    cliente_cnpj_cpf_snapshot = db.Column(db.String(20), nullable=True, index=True)
    cliente_email_financeiro_snapshot = db.Column(db.String(150), nullable=True)
    cliente_telefone_snapshot = db.Column(db.String(20), nullable=True)
    descricao = db.Column(db.String(255), nullable=False)
    numero_documento = db.Column(db.String(80), nullable=True, index=True)
    numero_nota_fiscal = db.Column(db.String(80), nullable=True, index=True)
    chave_acesso_nfe_nfse = db.Column(db.String(80), nullable=True)
    codigo_verificacao_nfse = db.Column(db.String(80), nullable=True)
    nota_emitida_id = db.Column(db.Integer, db.ForeignKey("financeiro_notas_fiscais_emitidas.id"), nullable=True, index=True)
    tipo_nota_emitida = db.Column(db.String(30), nullable=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("financeiro_contratos_clientes.id"), nullable=True, index=True)
    medicao_id = db.Column(db.Integer, db.ForeignKey("financeiro_contratos_medicoes.id"), nullable=True, index=True)
    origem_lancamento = db.Column(db.String(40), nullable=False, index=True)
    competencia = db.Column(db.String(7), nullable=True, index=True)
    data_emissao = db.Column(db.Date, nullable=True, index=True)
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    data_recebimento = db.Column(db.Date, nullable=True)
    valor_original = db.Column(db.Numeric(12, 2), nullable=False)
    valor_desconto = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    valor_acrescimo = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    valor_juros_multa = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    valor_recebido = db.Column(db.Numeric(12, 2), default=0, nullable=False)
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
    sub_centro_custo_veiculo_id = db.Column(db.Integer, nullable=True, index=True)
    status = db.Column(db.String(40), nullable=False, index=True)
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
    cancelado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    cancelado_em = db.Column(db.DateTime, nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False,
    )

    cliente = db.relationship("FinanceiroCliente", foreign_keys=[cliente_id])
    centro_custo = db.relationship("CentroCusto")
    sub_centro_custo_equipe = db.relationship("Equipe")
    nota_emitida = db.relationship("FinanceiroNotaFiscalEmitida", back_populates="titulos")
    contrato = db.relationship("FinanceiroContratoCliente", back_populates="titulos")
    medicao = db.relationship("FinanceiroContratoMedicao", back_populates="titulos")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_usuario_id])
    baixas = db.relationship("FinanceiroContaReceberBaixa", back_populates="titulo", order_by="FinanceiroContaReceberBaixa.data_recebimento.desc(), FinanceiroContaReceberBaixa.id.desc()")
    cobrancas = db.relationship("FinanceiroContaReceberCobranca", back_populates="titulo", order_by="FinanceiroContaReceberCobranca.data_contato.desc(), FinanceiroContaReceberCobranca.id.desc()")

    __table_args__ = (
        db.CheckConstraint("valor_original > 0", name="ck_fin_cr_titulos_valor_original"),
        db.CheckConstraint("valor_desconto >= 0", name="ck_fin_cr_titulos_valor_desconto"),
        db.CheckConstraint("valor_acrescimo >= 0", name="ck_fin_cr_titulos_valor_acrescimo"),
        db.CheckConstraint("valor_juros_multa >= 0", name="ck_fin_cr_titulos_valor_juros"),
        db.CheckConstraint("valor_recebido >= 0", name="ck_fin_cr_titulos_valor_recebido"),
        db.CheckConstraint("parcela_numero >= 1", name="ck_fin_cr_titulos_parcela_numero"),
        db.CheckConstraint("total_parcelas >= 1", name="ck_fin_cr_titulos_total_parcelas"),
        db.CheckConstraint(
            "status in ('Rascunho', 'Aguardando faturamento', 'Faturado', 'Agendado', "
            "'A vencer', 'Vencido', 'Recebido', 'Recebido parcialmente', 'Cancelado', "
            "'Estornado', 'Inadimplente')",
            name="ck_fin_cr_titulos_status",
        ),
        db.CheckConstraint(
            "origem_lancamento in ('Manual', 'Nota Fiscal Emitida', 'Medi��o', "
            "'Contrato', 'Reembolso', 'Outro')",
            name="ck_fin_cr_titulos_origem",
        ),
    )

    @property
    def valor_liquido(self):
        return (
            self.valor_original
            + self.valor_acrescimo
            + self.valor_juros_multa
            - self.valor_desconto
        )

    @property
    def saldo_aberto(self):
        saldo = self.valor_liquido - self.valor_recebido
        return saldo if saldo > 0 else 0

    @property
    def esta_cancelado_ou_estornado(self):
        return self.status in ["Cancelado", "Estornado"]

    @property
    def esta_recebido(self):
        return self.status == "Recebido"

    def status_visual(self, hoje=None):
        if self.status in ["Cancelado", "Estornado", "Recebido"]:
            return self.status

        hoje = hoje or agora_brasil().date()

        if self.saldo_aberto > 0 and self.data_vencimento < hoje:
            return "Vencido"

        return self.status

    def __repr__(self):
        return f"<FinanceiroContaReceberTitulo {self.id} {self.cliente_nome_snapshot}>"


class FinanceiroNotaFiscalEmitida(db.Model):
    __tablename__ = "financeiro_notas_fiscais_emitidas"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("financeiro_clientes.id"), nullable=True, index=True)
    tipo_nota = db.Column(db.String(30), nullable=False, index=True)
    numero_nota = db.Column(db.String(80), nullable=False, index=True)
    serie = db.Column(db.String(30), nullable=True, index=True)
    chave_acesso = db.Column(db.String(80), nullable=True, index=True)
    codigo_verificacao_nfse = db.Column(db.String(80), nullable=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("financeiro_contratos_clientes.id"), nullable=True, index=True)
    medicao_id = db.Column(db.Integer, db.ForeignKey("financeiro_contratos_medicoes.id"), nullable=True, index=True)
    cliente_nome_snapshot = db.Column(db.String(180), nullable=False, index=True)
    cliente_cnpj_cpf_snapshot = db.Column(db.String(20), nullable=False, index=True)
    cliente_email_financeiro_snapshot = db.Column(db.String(150), nullable=True)
    cliente_telefone_snapshot = db.Column(db.String(20), nullable=True)
    data_emissao = db.Column(db.Date, nullable=False, index=True)
    competencia = db.Column(db.String(7), nullable=True, index=True)
    descricao = db.Column(db.Text, nullable=True)
    valor_bruto = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_desconto = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_impostos_retidos = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_liquido = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False)
    data_vencimento_padrao = db.Column(db.Date, nullable=True)
    numero_parcelas = db.Column(db.Integer, nullable=False, default=1)
    condicao_recebimento = db.Column(db.String(120), nullable=True)
    status_fiscal = db.Column(db.String(30), nullable=False, default="Emitida", index=True)
    status_financeiro = db.Column(db.String(40), nullable=False, default="N�o integrado", index=True)
    arquivo_pdf_nome_original = db.Column(db.String(255), nullable=True)
    arquivo_pdf_nome_armazenado = db.Column(db.String(255), nullable=True)
    arquivo_pdf_path = db.Column(db.String(500), nullable=True)
    arquivo_pdf_drive_file_id = db.Column(db.String(255), nullable=True)
    arquivo_pdf_drive_link = db.Column(db.String(500), nullable=True)
    arquivo_xml_nome_original = db.Column(db.String(255), nullable=True)
    arquivo_xml_nome_armazenado = db.Column(db.String(255), nullable=True)
    arquivo_xml_path = db.Column(db.String(500), nullable=True)
    arquivo_xml_drive_file_id = db.Column(db.String(255), nullable=True)
    arquivo_xml_drive_link = db.Column(db.String(500), nullable=True)
    observacoes_fiscais = db.Column(db.Text, nullable=True)
    observacoes_financeiras = db.Column(db.Text, nullable=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    atualizado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    cancelado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    titulos = db.relationship("FinanceiroContaReceberTitulo", back_populates="nota_emitida", order_by="FinanceiroContaReceberTitulo.parcela_numero.asc(), FinanceiroContaReceberTitulo.id.asc()")
    cliente = db.relationship("FinanceiroCliente", foreign_keys=[cliente_id])
    contrato = db.relationship("FinanceiroContratoCliente", back_populates="notas_emitidas")
    medicao = db.relationship("FinanceiroContratoMedicao", back_populates="notas_emitidas", foreign_keys=[medicao_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_usuario_id])

    __table_args__ = (
        db.CheckConstraint("valor_bruto >= 0", name="ck_fin_notas_emitidas_valor_bruto"),
        db.CheckConstraint("valor_desconto >= 0", name="ck_fin_notas_emitidas_valor_desconto"),
        db.CheckConstraint("valor_impostos_retidos >= 0", name="ck_fin_notas_emitidas_valor_impostos"),
        db.CheckConstraint("valor_liquido >= 0", name="ck_fin_notas_emitidas_valor_liquido"),
        db.CheckConstraint("valor_total > 0", name="ck_fin_notas_emitidas_valor_total"),
        db.CheckConstraint("numero_parcelas >= 1", name="ck_fin_notas_emitidas_parcelas"),
        db.CheckConstraint("tipo_nota in ('NFS-e', 'NF-e', 'Recibo', 'Fatura', 'Outro')", name="ck_fin_notas_emitidas_tipo"),
        db.CheckConstraint("status_fiscal in ('Rascunho', 'Emitida', 'Enviada ao cliente', 'Cancelada', 'Substitu�da')", name="ck_fin_notas_emitidas_status_fiscal"),
        db.CheckConstraint("status_financeiro in ('N�o integrado', 'Pendente de gera��o', 'T�tulo gerado', 'Parcialmente vinculado', 'Vinculado a t�tulo existente', 'Cancelado')", name="ck_fin_notas_emitidas_status_financeiro"),
    )

    @property
    def titulos_ativos(self):
        return [titulo for titulo in self.titulos if titulo.status not in ["Cancelado", "Estornado"]]

    @property
    def quantidade_titulos_ativos(self):
        return len(self.titulos_ativos)

    @property
    def valor_vinculado_contas_receber(self):
        total = sum((titulo.valor_liquido for titulo in self.titulos_ativos), Decimal("0.00"))
        return total.quantize(Decimal("0.01"))

    @property
    def saldo_sem_titulo_financeiro(self):
        saldo = self.valor_total - self.valor_vinculado_contas_receber
        return saldo.quantize(Decimal("0.01")) if saldo > 0 else Decimal("0.00")

    @property
    def arquivo_pdf_disponivel(self):
        return bool(self.arquivo_pdf_path or self.arquivo_pdf_drive_file_id)

    @property
    def arquivo_xml_disponivel(self):
        return bool(self.arquivo_xml_path or self.arquivo_xml_drive_file_id)

    def __repr__(self):
        return f"<FinanceiroNotaFiscalEmitida {self.id} {self.numero_nota}>"


class FinanceiroContratoCliente(db.Model):
    __tablename__ = "financeiro_contratos_clientes"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("financeiro_clientes.id"), nullable=True, index=True)
    numero_contrato = db.Column(db.String(80), nullable=False, index=True)
    cliente_nome_snapshot = db.Column(db.String(180), nullable=False, index=True)
    cliente_cnpj_cpf_snapshot = db.Column(db.String(20), nullable=False, index=True)
    cliente_email_financeiro_snapshot = db.Column(db.String(150), nullable=True)
    cliente_telefone_snapshot = db.Column(db.String(20), nullable=True)
    descricao_objeto = db.Column(db.Text, nullable=True)
    data_inicio = db.Column(db.Date, nullable=False, index=True)
    data_fim = db.Column(db.Date, nullable=True, index=True)
    valor_contratual = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    tipo_cobranca = db.Column(db.String(40), nullable=False, default="Medi��o vari�vel")
    periodicidade_medicao = db.Column(db.String(30), nullable=False, default="Mensal")
    dia_padrao_vencimento = db.Column(db.Integer, nullable=True)
    condicao_recebimento = db.Column(db.String(120), nullable=True)
    centro_custo_id = db.Column(db.Integer, db.ForeignKey("centros_custo.id"), nullable=True, index=True)
    sub_centro_custo_equipe_id = db.Column(db.Integer, db.ForeignKey("equipes.id"), nullable=True, index=True)
    responsavel_interno_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="Ativo", index=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    atualizado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    cancelado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    cliente = db.relationship("FinanceiroCliente", foreign_keys=[cliente_id])

    centro_custo = db.relationship("CentroCusto")
    sub_centro_custo_equipe = db.relationship("Equipe")
    responsavel_interno = db.relationship("Usuario", foreign_keys=[responsavel_interno_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_usuario_id])
    medicoes = db.relationship("FinanceiroContratoMedicao", back_populates="contrato", order_by="FinanceiroContratoMedicao.data_medicao.desc(), FinanceiroContratoMedicao.id.desc()")
    titulos = db.relationship("FinanceiroContaReceberTitulo", back_populates="contrato", order_by="FinanceiroContaReceberTitulo.data_vencimento.desc(), FinanceiroContaReceberTitulo.id.desc()")
    notas_emitidas = db.relationship("FinanceiroNotaFiscalEmitida", back_populates="contrato", order_by="FinanceiroNotaFiscalEmitida.data_emissao.desc(), FinanceiroNotaFiscalEmitida.id.desc()")

    __table_args__ = (
        db.UniqueConstraint("numero_contrato", "cliente_cnpj_cpf_snapshot", name="uq_fin_contratos_numero_cliente"),
        db.CheckConstraint("valor_contratual >= 0", name="ck_fin_contratos_valor"),
        db.CheckConstraint("status in ('Rascunho', 'Ativo', 'Suspenso', 'Encerrado', 'Cancelado')", name="ck_fin_contratos_status"),
        db.CheckConstraint("tipo_cobranca in ('Medi��o vari�vel', 'Valor fixo mensal', 'Por evento', 'Por ordem de servi�o', 'Reembolso', 'Outro')", name="ck_fin_contratos_tipo_cobranca"),
        db.CheckConstraint("periodicidade_medicao in ('Mensal', 'Quinzenal', 'Semanal', 'Por demanda', '�nica', 'Outra')", name="ck_fin_contratos_periodicidade"),
    )

    @property
    def medicoes_ativas(self):
        return [medicao for medicao in self.medicoes if medicao.status_medicao != "Cancelada"]

    @property
    def titulos_ativos(self):
        return [titulo for titulo in self.titulos if titulo.status not in ["Cancelado", "Estornado"]]

    @property
    def notas_ativas(self):
        return [nota for nota in self.notas_emitidas if nota.status_fiscal != "Cancelada"]

    @property
    def quantidade_medicoes(self):
        return len(self.medicoes_ativas)

    @property
    def valor_medido_acumulado(self):
        total = sum((medicao.valor_liquido_medido for medicao in self.medicoes_ativas), Decimal("0.00"))
        return total.quantize(Decimal("0.01"))

    @property
    def valor_faturado(self):
        total = sum((titulo.valor_liquido for titulo in self.titulos_ativos), Decimal("0.00"))
        return total.quantize(Decimal("0.01"))

    @property
    def saldo_contratual_estimado(self):
        saldo = self.valor_contratual - self.valor_medido_acumulado
        return saldo.quantize(Decimal("0.01")) if saldo > 0 else Decimal("0.00")

    def __repr__(self):
        return f"<FinanceiroContratoCliente {self.id} {self.numero_contrato}>"


class FinanceiroContratoMedicao(db.Model):
    __tablename__ = "financeiro_contratos_medicoes"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("financeiro_contratos_clientes.id"), nullable=False, index=True)
    equipe_id = db.Column(db.Integer, db.ForeignKey("equipes.id"), nullable=True, index=True)
    nota_emitida_id = db.Column(db.Integer, db.ForeignKey("financeiro_notas_fiscais_emitidas.id"), nullable=True, index=True)
    numero_medicao = db.Column(db.String(80), nullable=False, index=True)
    competencia = db.Column(db.String(7), nullable=False, index=True)
    data_medicao = db.Column(db.Date, nullable=False, index=True)
    periodo_inicio = db.Column(db.Date, nullable=False, index=True)
    periodo_fim = db.Column(db.Date, nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=True)
    valor_bruto_medido = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_desconto = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_acrescimo = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_retencoes = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    valor_liquido_medido = db.Column(db.Numeric(12, 2), nullable=False)
    data_prevista_faturamento = db.Column(db.Date, nullable=True)
    data_prevista_vencimento = db.Column(db.Date, nullable=True)
    status_medicao = db.Column(db.String(40), nullable=False, default="Medida", index=True)
    status_financeiro = db.Column(db.String(40), nullable=False, default="N�o integrado", index=True)
    anexo_nome_original = db.Column(db.String(255), nullable=True)
    anexo_nome_armazenado = db.Column(db.String(255), nullable=True)
    anexo_path = db.Column(db.String(500), nullable=True)
    anexo_drive_file_id = db.Column(db.String(255), nullable=True)
    anexo_drive_link = db.Column(db.String(500), nullable=True)
    observacoes_tecnicas = db.Column(db.Text, nullable=True)
    observacoes_financeiras = db.Column(db.Text, nullable=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    atualizado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    cancelado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    contrato = db.relationship("FinanceiroContratoCliente", back_populates="medicoes")
    equipe = db.relationship("Equipe", foreign_keys=[equipe_id])
    nota_emitida = db.relationship("FinanceiroNotaFiscalEmitida", foreign_keys=[nota_emitida_id])
    titulos = db.relationship("FinanceiroContaReceberTitulo", back_populates="medicao", order_by="FinanceiroContaReceberTitulo.parcela_numero.asc(), FinanceiroContaReceberTitulo.id.asc()")
    notas_emitidas = db.relationship("FinanceiroNotaFiscalEmitida", back_populates="medicao", foreign_keys="FinanceiroNotaFiscalEmitida.medicao_id", order_by="FinanceiroNotaFiscalEmitida.data_emissao.desc(), FinanceiroNotaFiscalEmitida.id.desc()")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_usuario_id])

    __table_args__ = (
        db.UniqueConstraint("contrato_id", "numero_medicao", name="uq_fin_medicoes_contrato_numero"),
        db.CheckConstraint("valor_bruto_medido >= 0", name="ck_fin_medicoes_valor_bruto"),
        db.CheckConstraint("valor_desconto >= 0", name="ck_fin_medicoes_desconto"),
        db.CheckConstraint("valor_acrescimo >= 0", name="ck_fin_medicoes_acrescimo"),
        db.CheckConstraint("valor_retencoes >= 0", name="ck_fin_medicoes_retencoes"),
        db.CheckConstraint("valor_liquido_medido > 0", name="ck_fin_medicoes_valor_liquido"),
        db.CheckConstraint("periodo_fim >= periodo_inicio", name="ck_fin_medicoes_periodo"),
        db.CheckConstraint("status_medicao in ('Rascunho', 'Medida', 'Aguardando aprova��o', 'Aprovada', 'Faturada', 'Gerada no Contas a Receber', 'Cancelada')", name="ck_fin_medicoes_status"),
        db.CheckConstraint("status_financeiro in ('N�o integrado', 'Pendente de gera��o', 'T�tulo gerado', 'Vinculado a t�tulo existente', 'Vinculado � nota emitida', 'Cancelado')", name="ck_fin_medicoes_status_financeiro"),
    )

    @property
    def titulos_ativos(self):
        return [titulo for titulo in self.titulos if titulo.status not in ["Cancelado", "Estornado"]]

    @property
    def quantidade_titulos_ativos(self):
        return len(self.titulos_ativos)

    @property
    def valor_faturado(self):
        total = sum((titulo.valor_liquido for titulo in self.titulos_ativos), Decimal("0.00"))
        return total.quantize(Decimal("0.01"))

    @property
    def saldo_sem_titulo_financeiro(self):
        saldo = self.valor_liquido_medido - self.valor_faturado
        return saldo.quantize(Decimal("0.01")) if saldo > 0 else Decimal("0.00")

    @property
    def anexo_disponivel(self):
        return bool(self.anexo_path or self.anexo_drive_file_id)

    def __repr__(self):
        return f"<FinanceiroContratoMedicao {self.id} {self.numero_medicao}>"




class FinanceiroContaReceberCobranca(db.Model):
    __tablename__ = "financeiro_contas_receber_cobrancas"

    id = db.Column(db.Integer, primary_key=True)
    titulo_id = db.Column(db.Integer, db.ForeignKey("financeiro_contas_receber_titulos.id"), nullable=False, index=True)
    data_contato = db.Column(db.Date, nullable=False, index=True)
    tipo_contato = db.Column(db.String(30), nullable=False, index=True)
    responsavel_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    status_cobranca = db.Column(db.String(40), nullable=False, default="A cobrar", index=True)
    previsao_pagamento = db.Column(db.Date, nullable=True, index=True)
    observacao = db.Column(db.Text, nullable=True)
    proxima_acao = db.Column(db.String(180), nullable=True)
    data_proxima_acao = db.Column(db.Date, nullable=True, index=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    atualizado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    cancelado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    cancelado_em = db.…15622 tokens truncated…= db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
        nullable=True,
        index=True,
    )
    tipo_custo = db.Column(db.String(20), nullable=True)
    tipo_leitura_abastecimento = db.Column(db.String(20), nullable=True)
    leitura_abastecimento = db.Column(db.Numeric(8, 2), nullable=True)
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
        db.CheckConstraint(
            "tipo_custo IS NULL OR tipo_custo IN ('Abastecimento', 'Diversos', 'Manuten��o')",
            name="ck_suprimentos_requisicoes_compra_tipo_custo",
        ),
        db.CheckConstraint(
            "tipo_leitura_abastecimento IS NULL OR tipo_leitura_abastecimento IN ('odometro', 'horimetro')",
            name="ck_suprimentos_requisicoes_compra_tipo_leitura_abastecimento",
        ),
        db.CheckConstraint(
            "leitura_abastecimento IS NULL OR leitura_abastecimento >= 0",
            name="ck_suprimentos_requisicoes_compra_leitura_abastecimento",
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
    frete_fornecedor_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_fornecedores.id"),
        nullable=True,
        index=True,
    )
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
    frete_fornecedor = db.relationship("SuprimentosFornecedor", foreign_keys=[frete_fornecedor_id])
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
    valor_frete = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    prazo_entrega_dias = db.Column(db.Integer, nullable=True)
    condicao_pagamento = db.Column(db.String(160), nullable=True)
    forma_pagamento = db.Column(db.String(30), nullable=True, index=True)
    cartao_credito_id = db.Column(
        db.Integer,
        db.ForeignKey("financeiro_cartoes_credito.id"),
        nullable=True,
        index=True,
    )
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
    cartao_credito = db.relationship("FinanceiroCartaoCredito")
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
            "valor_frete >= 0",
            name="ck_suprimentos_cotacao_propostas_valor_frete",
        ),
        db.CheckConstraint(
            "prazo_entrega_dias is null or prazo_entrega_dias >= 0",
            name="ck_suprimentos_cotacao_propostas_prazo",
        ),
    )

    @property
    def valor_subtotal(self):
        return self.quantidade_snapshot * self.preco_unitario

    @property
    def valor_total(self):
        return self.valor_subtotal + (self.valor_frete or 0)

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
    tipo_custo = db.Column(db.String(20), nullable=True)
    tipo_leitura_abastecimento = db.Column(db.String(20), nullable=True)
    leitura_abastecimento = db.Column(db.Numeric(8, 2), nullable=True)
    status = db.Column(db.String(30), default="Gerada", nullable=False, index=True)
    status_financeiro = db.Column(db.String(30), default="Pendente de Financeiro", nullable=False, index=True)
    previsao_vencimento = db.Column(db.Date, nullable=True, index=True)
    quantidade_parcelas = db.Column(db.Integer, default=1, nullable=False)
    tipo_pagamento_financeiro = db.Column(db.String(30), nullable=True, index=True)
    forma_pagamento_financeiro = db.Column(db.String(30), nullable=True, index=True)
    condicao_pagamento_financeiro = db.Column(db.String(60), nullable=True)
    numero_parcelas_financeiro = db.Column(db.Integer, default=1, nullable=False)
    data_primeiro_vencimento_financeiro = db.Column(db.Date, nullable=True, index=True)
    cartao_credito_id = db.Column(
        db.Integer,
        db.ForeignKey("financeiro_cartoes_credito.id"),
        nullable=True,
        index=True,
    )
    observacoes_financeiras = db.Column(db.Text, nullable=True)
    preparado_financeiro_em = db.Column(db.DateTime, nullable=True)
    provisionado_financeiro_em = db.Column(db.DateTime, nullable=True)
    financeiro_integrado = db.Column(db.Boolean, default=False, nullable=False, index=True)
    financeiro_integrado_em = db.Column(db.DateTime, nullable=True)
    financeiro_integrado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
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
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    cartao_credito = db.relationship("FinanceiroCartaoCredito")
    financeiro_integrado_por = db.relationship("Usuario", foreign_keys=[financeiro_integrado_por_usuario_id])
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
    titulos_financeiros = db.relationship(
        "FinanceiroContaPagarTitulo",
        back_populates="ordem_compra",
        order_by="FinanceiroContaPagarTitulo.parcela_numero",
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
            "status_financeiro in ('Pendente de Financeiro', 'Preparado para Financeiro', 'Provisionado', 'Pendente de conferencia', 'Integrado ao Financeiro', 'Cancelado', 'Divergente')",
            name="ck_suprimentos_ordens_compra_status_financeiro",
        ),
        db.CheckConstraint(
            "quantidade_parcelas >= 1 and numero_parcelas_financeiro >= 1",
            name="ck_suprimentos_ordens_compra_qtd_parcelas",
        ),
        db.CheckConstraint(
            "tipo_custo IS NULL OR tipo_custo IN ('Abastecimento', 'Diversos', 'Manuten��o')",
            name="ck_suprimentos_ordens_compra_tipo_custo",
        ),
        db.CheckConstraint(
            "tipo_leitura_abastecimento IS NULL OR tipo_leitura_abastecimento IN ('odometro', 'horimetro')",
            name="ck_suprimentos_ordens_compra_tipo_leitura_abastecimento",
        ),
        db.CheckConstraint(
            "leitura_abastecimento IS NULL OR leitura_abastecimento >= 0",
            name="ck_suprimentos_ordens_compra_leitura_abastecimento",
        ),
    )

    @property
    def valor_subtotal_itens(self):
        return sum((item.valor_subtotal for item in self.itens), start=0)

    @property
    def valor_frete_total(self):
        return sum((item.valor_frete or 0 for item in self.itens), start=0)

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
    proxima_consulta_em = db.Column(db.DateTime, nullable=True)
    ultimo_cstat = db.Column(db.String(10), nullable=True)
    ultimo_motivo = db.Column(db.Text, nullable=True)
    documentos_ultima_consulta = db.Column(db.Integer, default=0, nullable=False)
    ultimo_download_xml_em = db.Column(db.DateTime, nullable=True)
    download_xml_bloqueado_ate = db.Column(db.DateTime, nullable=True)
    download_xml_status = db.Column(db.String(30), nullable=True)
    download_xml_mensagem = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=agora_brasil,
        onupdate=agora_brasil,
        nullable=False
    )

    def __repr__(self):
        return f"<FiscalControleNSU {self.cnpj_empresa} nsu={self.ultimo_nsu}>"


class FiscalConsultaNSUHistorico(db.Model):
    __tablename__ = "fiscal_consultas_nsu_historico"

    id = db.Column(db.Integer, primary_key=True)
    cnpj_empresa = db.Column(db.String(14), nullable=False, index=True)
    origem = db.Column(db.String(20), nullable=False, index=True)
    consultado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False, index=True)
    nsu_enviado = db.Column(db.String(20), nullable=False)
    cstat = db.Column(db.String(10), nullable=True, index=True)
    motivo = db.Column(db.Text, nullable=True)
    ultimo_nsu_recebido = db.Column(db.String(20), nullable=True)
    max_nsu_recebido = db.Column(db.String(20), nullable=True)
    documentos_quantidade = db.Column(db.Integer, default=0, nullable=False)
    menor_nsu_documento = db.Column(db.String(20), nullable=True)
    maior_nsu_documento = db.Column(db.String(20), nullable=True)
    nsu_gravado = db.Column(db.String(20), nullable=True)
    gravacao_status = db.Column(db.String(30), nullable=False)
    proxima_consulta_em = db.Column(db.DateTime, nullable=True)
    erro_tecnico = db.Column(db.Text, nullable=True)
    resposta_xml = db.Column(db.Text, nullable=True)


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
    xml_consultado_em = db.Column(db.DateTime, nullable=True)
    financeiro_status = db.Column(db.String(40), default="Pendente de geracao", nullable=False, index=True)
    financeiro_integrado = db.Column(db.Boolean, default=False, nullable=False, index=True)
    financeiro_integrado_em = db.Column(db.DateTime, nullable=True)
    financeiro_integrado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    financeiro_ignorado = db.Column(db.Boolean, default=False, nullable=False, index=True)
    financeiro_ignorado_em = db.Column(db.DateTime, nullable=True)
    financeiro_ignorado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    financeiro_observacoes = db.Column(db.Text, nullable=True)
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
    titulos_financeiros = db.relationship("FinanceiroContaPagarTitulo", back_populates="fiscal_documento")
    vinculado_por = db.relationship("Usuario", foreign_keys=[vinculado_por_usuario_id])
    manifestado_por = db.relationship("Usuario", foreign_keys=[manifestado_por_usuario_id])
    financeiro_integrado_por = db.relationship("Usuario", foreign_keys=[financeiro_integrado_por_usuario_id])
    financeiro_ignorado_por = db.relationship("Usuario", foreign_keys=[financeiro_ignorado_por_usuario_id])
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
    valor_frete = db.Column(db.Numeric(12, 2), default=0, nullable=False)
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
            "valor_frete >= 0",
            name="ck_suprimentos_oc_itens_valor_frete",
        ),
        db.CheckConstraint(
            "prazo_entrega_dias is null or prazo_entrega_dias >= 0",
            name="ck_suprimentos_oc_itens_prazo",
        ),
    )

    @property
    def valor_subtotal(self):
        return self.quantidade * self.preco_unitario

    @property
    def valor_total(self):
        return self.valor_subtotal + (self.valor_frete or 0)

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
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centros_custo.id"),
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
    centro_custo = db.relationship("CentroCusto")

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
    status = db.Column(db.String(20), default="Ativa", nullable=False, index=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    cancelado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )
    motivo_cancelamento = db.Column(db.Text, nullable=True)

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
    entregue_por = db.relationship("Usuario", foreign_keys=[entregue_por_usuario_id])
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_usuario_id])

    __table_args__ = (
        db.CheckConstraint(
            "tipo_material in ('EPI', 'Uniforme')",
            name="ck_seguranca_entregas_epi_tipo_material",
        ),
        db.CheckConstraint(
            "quantidade > 0",
            name="ck_seguranca_entregas_epi_quantidade",
        ),
        db.CheckConstraint(
            "status in ('Ativa', 'Cancelada')",
            name="ck_seguranca_entregas_epi_status",
        ),
    )

    def __repr__(self):
        return f"<SegurancaTrabalhoEntregaEpi colaborador={self.colaborador_id} item={self.item_id}>"


def _gerar_codigo_os_rental():
    ano = agora_brasil().year
    prefixo = f"RR-OS-{ano}-"
    codigos = (
        db.session.query(OperacaoOrdemServico.codigo_os_rental)
        .filter(OperacaoOrdemServico.codigo_os_rental.like(f"{prefixo}%"))
        .all()
    )
    sequencias = [
        int(codigo[len(prefixo):])
        for (codigo,) in codigos
        if codigo and codigo[len(prefixo):].isdigit()
    ]
    return f"{prefixo}{max(sequencias, default=0) + 1:06d}"


class OperacaoOrdemServico(db.Model):
    __tablename__ = "operacao_ordens_servico"

    id_os_interno = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codigo_os_rental = db.Column(db.String(60), unique=True, nullable=False, index=True, default=_gerar_codigo_os_rental)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    chave_idempotencia = db.Column(db.String(36), unique=True, nullable=False, index=True)
    numero_os_cliente = db.Column(db.String(80), nullable=True, index=True)
    local = db.Column(db.String(255), nullable=False)
    equipe = db.Column(db.String(120), nullable=False)
    data_programada_inicial = db.Column(db.Date, nullable=False, index=True)
    data_programada_final = db.Column(db.Date, nullable=False, index=True)
    data_inicial = db.Column(db.Date, nullable=True)
    data_final = db.Column(db.Date, nullable=True)
    trabalho_previsto = db.Column(db.Text, nullable=True)
    supervisor = db.Column(db.String(150), nullable=True)
    encarregado = db.Column(db.String(150), nullable=True)
    status_identificacao = db.Column(db.String(20), default="Pendente", nullable=False, index=True)
    status_operacional = db.Column(db.String(40), default="Programada", nullable=False, index=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    atualizado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    apontamentos_diarios = db.relationship("OperacaoApontamentoDiario", back_populates="ordem_servico")

    __table_args__ = (
        db.UniqueConstraint(
            "numero_os_cliente",
            name="uq_operacao_ordens_servico_numero_os_cliente",
        ),
        db.CheckConstraint(
            "status_identificacao in ('Pendente', 'Informado')",
            name="ck_operacao_os_status_identificacao",
        ),
        db.CheckConstraint(
            "data_programada_final >= data_programada_inicial",
            name="ck_operacao_os_periodo_programado",
        ),
    )

    def __repr__(self):
        return f"<OperacaoOrdemServico {self.codigo_os_rental}>"


class OperacaoApontamentoDiario(db.Model):
    __tablename__ = "operacao_apontamentos_diarios"

    id_apontamento_diario = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_os_interno = db.Column(db.String(36), db.ForeignKey("operacao_ordens_servico.id_os_interno"), nullable=False, index=True)
    chave_idempotencia = db.Column(db.String(36), unique=True, nullable=False, index=True)
    data_evento = db.Column(db.Date, nullable=False, index=True)
    equipe = db.Column(db.String(120), nullable=False)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    atualizado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    versao = db.Column(db.Integer, default=1, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    ordem_servico = db.relationship("OperacaoOrdemServico", back_populates="apontamentos_diarios")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_usuario_id])
    diario_localizacao = db.relationship("OperacaoDiarioLocalizacao", back_populates="apontamento", uselist=False)
    diario_servico = db.relationship("OperacaoDiarioServico", back_populates="apontamento", uselist=False)
    diario_material = db.relationship("OperacaoDiarioMaterial", back_populates="apontamento", uselist=False)
    circulacao_trem = db.relationship("OperacaoCirculacaoTrem", back_populates="apontamento", uselist=False)
    intervencao_adversa = db.relationship("OperacaoIntervencaoAdversa", back_populates="apontamento", uselist=False)

    def __repr__(self):
        return f"<OperacaoApontamentoDiario {self.id_apontamento_diario}>"


class OperacaoDiarioLocalizacao(db.Model):
    __tablename__ = "operacao_diarios_localizacao"

    id_apontamento_diario = db.Column(db.String(36), db.ForeignKey("operacao_apontamentos_diarios.id_apontamento_diario"), primary_key=True)
    encarregado = db.Column(db.String(150), nullable=False)
    chefe_boletim = db.Column(db.String(180), nullable=False)
    local = db.Column(db.String(255), nullable=False)
    numero_amv = db.Column(db.String(80), nullable=True)
    sub = db.Column(db.String(80), nullable=True)
    km_inicio = db.Column(db.String(40), nullable=True)
    km_fim = db.Column(db.String(40), nullable=True)
    hora_inicial = db.Column(db.Time, nullable=True)
    intervalo_jornada = db.Column(db.Time, nullable=True)
    hora_final = db.Column(db.Time, nullable=True)
    intervalo_inicio = db.Column(db.Time, nullable=True)
    intervalo_fim = db.Column(db.Time, nullable=True)
    pedido_liberacao_ccp = db.Column(db.Time, nullable=True)
    liberacao_embandeiramento = db.Column(db.Time, nullable=True)
    termino_embandeiramento = db.Column(db.Time, nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    apontamento = db.relationship("OperacaoApontamentoDiario", back_populates="diario_localizacao")

    @property
    def total_jornada(self):
        if not (self.hora_inicial and self.hora_final):
            return "Em aberto"
        inicio = self.hora_inicial.hour * 3600 + self.hora_inicial.minute * 60 + self.hora_inicial.second
        fim = self.hora_final.hour * 3600 + self.hora_final.minute * 60 + self.hora_final.second
        if fim < inicio:
            fim += 86400
        intervalo = self.intervalo_jornada.hour * 3600 + self.intervalo_jornada.minute * 60 + self.intervalo_jornada.second if self.intervalo_jornada else 3600
        total = max(fim - inicio - intervalo, 0)
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


class OperacaoDiarioServico(db.Model):
    __tablename__ = "operacao_diarios_servico"

    id_apontamento_diario = db.Column(db.String(36), db.ForeignKey("operacao_apontamentos_diarios.id_apontamento_diario"), primary_key=True)
    servico = db.Column(db.Text, nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)

    apontamento = db.relationship("OperacaoApontamentoDiario", back_populates="diario_servico")

    __table_args__ = (
        db.CheckConstraint("quantidade > 0", name="ck_operacao_diario_servico_quantidade"),
    )


class OperacaoDiarioMaterial(db.Model):
    __tablename__ = "operacao_diarios_material"

    id_apontamento_diario = db.Column(db.String(36), db.ForeignKey("operacao_apontamentos_diarios.id_apontamento_diario"), primary_key=True)
    tipo_material = db.Column(db.String(20), nullable=False)
    material_aplicado = db.Column(db.String(255), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)

    apontamento = db.relationship("OperacaoApontamentoDiario", back_populates="diario_material")

    __table_args__ = (
        db.CheckConstraint("tipo_material in ('NOVO', 'RECUPERADO')", name="ck_operacao_diario_material_tipo"),
        db.CheckConstraint("quantidade > 0", name="ck_operacao_diario_material_quantidade"),
    )


class OperacaoCirculacaoTrem(db.Model):
    __tablename__ = "operacao_circulacao_trens"

    id_apontamento_diario = db.Column(db.String(36), db.ForeignKey("operacao_apontamentos_diarios.id_apontamento_diario"), primary_key=True)
    prefixo = db.Column(db.String(80), nullable=True)
    motivo_paralisacao = db.Column(db.String(40), nullable=True)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fim = db.Column(db.Time, nullable=True)
    via_linha = db.Column(db.String(160), nullable=True)
    operador_ccp_maquinista = db.Column(db.String(160), nullable=True)
    tempo_interrompido = db.Column(db.String(40), nullable=True)
    pedido_corte_composicao = db.Column(db.String(30), nullable=False)
    corte_composicao = db.Column(db.String(30), nullable=False)

    apontamento = db.relationship("OperacaoApontamentoDiario", back_populates="circulacao_trem")

    @property
    def duracao(self):
        if not (self.hora_inicio and self.hora_fim):
            return "-"
        segundos = (self.hora_fim.hour * 3600 + self.hora_fim.minute * 60 + self.hora_fim.second) - (self.hora_inicio.hour * 3600 + self.hora_inicio.minute * 60 + self.hora_inicio.second)
        if segundos < 0:
            return "-"
        return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}:{segundos % 60:02d}"


class OperacaoIntervencaoAdversa(db.Model):
    __tablename__ = "operacao_intervencoes_adversas"

    id_apontamento_diario = db.Column(db.String(36), db.ForeignKey("operacao_apontamentos_diarios.id_apontamento_diario"), primary_key=True)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fim = db.Column(db.Time, nullable=True)
    tempo_total = db.Column(db.String(40), nullable=True)
    intervencao = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(160), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    apontamento = db.relationship("OperacaoApontamentoDiario", back_populates="intervencao_adversa")

    @property
    def duracao(self):
        if not (self.hora_inicio and self.hora_fim):
            return "-"
        segundos = (self.hora_fim.hour * 3600 + self.hora_fim.minute * 60 + self.hora_fim.second) - (self.hora_inicio.hour * 3600 + self.hora_inicio.minute * 60 + self.hora_inicio.second)
        if segundos < 0:
            return "-"
        return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}:{segundos % 60:02d}"

