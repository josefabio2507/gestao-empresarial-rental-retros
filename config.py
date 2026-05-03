import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-local-desenvolvimento")

    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///app.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False