import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-dev-temporaria")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///desenvolvimento.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
