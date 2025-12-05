# app/models/__init__.py
from .inmate import Inmate
from .alert import Alert
# Add any other models here...
from .facial_embedding import FacialEmbedding 
from app.routes.admin_api import admin_api_bp
app.register_blueprint(admin_api_bp)