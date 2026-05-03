from app import create_app
from app.extensions import db
from app.models import Usuario, NivelAcesso

app = create_app()

with app.app_context():
    nivel_admin = NivelAcesso.query.filter_by(slug="administrador").first()

    if not nivel_admin:
        nivel_admin = NivelAcesso(
            nome="Administrador",
            slug="administrador",
            descricao="Acesso administrativo completo",
            ativo=True
        )
        db.session.add(nivel_admin)
        db.session.flush()

    admin = Usuario.query.filter_by(email="admin@rentalretros.com.br").first()

    if not admin:
        admin = Usuario(
            nome="Administrador",
            email="admin@rentalretros.com.br",
            nivel_acesso_id=nivel_admin.id,
            ativo=True,
            precisa_trocar_senha=True
        )

        admin.definir_senha("Admin@123456")

        db.session.add(admin)
        db.session.commit()

        print("Usuário administrador criado com sucesso.")
    else:
        print("Usuário administrador já existe.")