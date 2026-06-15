from flask import Blueprint


cargos_bp = Blueprint("cargos", __name__)

from app.admin.cargos import routes
