# backend/app/config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class DevelopmentConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    # Store database in the backend folder (not migrations which was deleted)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '../instance/heimdall.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(DevelopmentConfig):
    # Use environment variable for production database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '../instance/heimdall.db')