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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    itens_suprimentos = db.relationship(
        "SuprimentosItem",
        back_populates="centro_custo_padrao",
    )

    def __repr__(self):
        return f"<CentroCusto {self.codigo or ''} {self.nome}>"


class SuprimentosItem(db.Model):
    __tablename__ = "suprimentos_itens"

    id = db.Column(db.Integer, primary_key=True)
    codigo_interno = db.Column(db.String(60), unique=True, nullable=True, index=True)
    descricao = db.Column(db.String(220), nullable=False)
    categoria_id = db.Column(
        db.Integer,
        db.ForeignKey("suprimentos_categorias_itens.id"),
        nullable=False,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    solicitante = db.relationship("Usuario")
    centro_custo = db.relationship("CentroCusto")
    equipe = db.relationship("Equipe")
    itens = db.relationship(
        "SuprimentosRequisicaoCompraItem",
        back_populates="requisicao",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "status in ('Rascunho', 'Enviada para Analise', 'Cancelada')",
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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
    aberta_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    encerrada_em = db.Column(db.DateTime, nullable=True)
    enviada_aprovacao_em = db.Column(db.DateTime, nullable=True)
    aprovada_em = db.Column(db.DateTime, nullable=True)
    aprovada_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    requisicao = db.relationship("SuprimentosRequisicaoCompra")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    aprovada_por = db.relationship("Usuario", foreign_keys=[aprovada_por_usuario_id])
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

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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
