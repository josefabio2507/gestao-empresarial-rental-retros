from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicialização das extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return Usuario.query.get(int(user_id))
        except (TypeError, ValueError):
            return None

    # Importação dos Blueprints
    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.usuarios.routes import usuarios_bp
    from app.permissoes.routes import permissoes_bp
    from app.departamentos.routes import departamentos_bp
    from app.departamento_pessoal.routes import departamento_pessoal_bp
    from app.departamento_pessoal.colaboradores.routes import colaboradores_bp
    from app.departamento_pessoal.pedido_refeicoes.routes import pedido_refeicoes_bp
    from app.departamento_pessoal.documentos.routes import documentos_bp
    from app.departamento_pessoal.vale_transporte.routes import vale_transporte_bp
    from app.financeiro.routes import financeiro_bp
    from app.operacao.routes import operacao_bp
    from app.seguranca_trabalho.routes import seguranca_trabalho_bp
    from app.admin import admin_bp
    from app.admin.cargos import cargos_bp
    from app.admin.equipes import equipes_bp

    # Registro dos Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
    app.register_blueprint(permissoes_bp, url_prefix="/permissoes")
    app.register_blueprint(departamentos_bp, url_prefix="/departamentos")
    app.register_blueprint(departamento_pessoal_bp, url_prefix="/departamento-pessoal")
    app.register_blueprint(colaboradores_bp, url_prefix="/departamento-pessoal/colaboradores")
    app.register_blueprint(pedido_refeicoes_bp, url_prefix="/departamento-pessoal/pedido-refeicoes")
    app.register_blueprint(documentos_bp, url_prefix="/departamento-pessoal/documentos")
    app.register_blueprint(vale_transporte_bp, url_prefix="/departamento-pessoal/vale-transporte")
    app.register_blueprint(financeiro_bp, url_prefix="/financeiro")
    app.register_blueprint(operacao_bp, url_prefix="/operacao")
    app.register_blueprint(seguranca_trabalho_bp, url_prefix="/seguranca-trabalho")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(cargos_bp, url_prefix="/admin/cargos")
    app.register_blueprint(equipes_bp, url_prefix="/admin/equipes")

    return app
