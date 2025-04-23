# backend/app/config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class DevelopmentConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '../migrations/heimdall.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProductionConfig(DevelopmentConfig):
    pass