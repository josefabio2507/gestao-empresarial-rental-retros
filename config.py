import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-local-desenvolvimento")

    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///app.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_MIGRATE_ON_START = os.getenv(
        "AUTO_MIGRATE_ON_START",
        "true" if SQLALCHEMY_DATABASE_URI.startswith("postgresql://") else "false",
    ).lower() == "true"
    AUTO_SEED_MODULES_ON_START = os.getenv(
        "AUTO_SEED_MODULES_ON_START",
        "true" if SQLALCHEMY_DATABASE_URI.startswith("postgresql://") else "false",
    ).lower() == "true"

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    RECUPERACAO_SENHA_EXPIRACAO_MINUTOS = int(
        os.getenv("RECUPERACAO_SENHA_EXPIRACAO_MINUTOS", "60")
    )

    GOOGLE_DRIVE_HOLERITES_FOLDER_ID = os.getenv(
        "GOOGLE_DRIVE_HOLERITES_FOLDER_ID",
        "",
    ).strip()
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
