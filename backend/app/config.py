# backend/app/config.py
import os

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    DEBUG = True

class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    DEBUG = False
