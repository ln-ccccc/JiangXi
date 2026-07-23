import os

from flask import Flask
from flask_cors import CORS

from applications import models  # noqa: F401
from applications.api import system_api
from applications.common.scripts import init_script
from applications.configs import config
from applications.configs.config import _build_database_uri
from applications.extensions import db, init_plugs


def _build_allowed_origins(app):
    configured = app.config.get('CORS_ALLOWED_ORIGINS')
    return [item.strip() for item in str(configured or '').split(',') if item.strip()]


def create_app(config_name=None):
    app = Flask(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

    if not config_name:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app.config.from_object(config[config_name])
    if config_name == 'production' or os.getenv('DB_BACKEND') or os.getenv('SQLITE_PATH'):
        app.config['DB_BACKEND'] = (os.getenv('DB_BACKEND') or app.config.get('DB_BACKEND') or 'mysql').strip().lower()
        app.config['SQLITE_PATH'] = os.getenv('SQLITE_PATH') or app.config.get('SQLITE_PATH') or '/app/runtime_data/jiangxi.sqlite3'
        app.config['SQLALCHEMY_DATABASE_URI'] = _build_database_uri()
    if config_name == 'production' and not os.getenv('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY is required in production')
    init_plugs(app)

    with app.app_context():
        db.create_all()

    if config_name != 'testing':
        init_script(app)

    system_api(app)

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['JSON_AS_ASCII'] = False
    CORS(
        app,
        resources={r"/api/*": {"origins": _build_allowed_origins(app)}},
        supports_credentials=True,
    )

    return app
