from flask import Blueprint


equipes_bp = Blueprint("equipes", __name__)

from app.admin.equipes import routes
