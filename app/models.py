from datetime import datetime

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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_solicitacao = db.Column(db.String(80), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    usuario = db.relationship("Usuario", back_populates="tokens_recuperacao_senha")

    @property
    def foi_usado(self):
        return self.usado_em is not None

    @property
    def expirou(self):
        return datetime.utcnow() > self.expira_em

    def __repr__(self):
        return f"<TokenRecuperacaoSenha usuario={self.usuario_id}>"

class Equipe(db.Model):
    __tablename__ = "equipes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    pedido = db.relationship("PedidoRefeicao", backref="consumos")
    colaborador = db.relationship("Colaborador")
    item_cardapio = db.relationship("ItemCardapio")

    def __repr__(self):
        return f"<ConsumoRefeicao pedido={self.pedido_id} colaborador={self.colaborador_id}>" 
