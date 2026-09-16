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
    if config_name == 'production' or (
        config_name != 'testing' and (os.getenv('DB_BACKEND') or os.getenv('SQLITE_PATH'))
    ):
        app.config['DB_BACKEND'] = (os.getenv('DB_BACKEND') or app.config.get('DB_BACKEND') or 'mysql').strip().lower()
        app.config['SQLITE_PATH'] = os.getenv('SQLITE_PATH') or app.config.get('SQLITE_PATH') or '/app/runtime_data/jiangxi.sqlite3'
        app.config['SQLALCHEMY_DATABASE_URI'] = _build_database_uri()
    if (config_name == 'production' or os.getenv('STANDALONE_MODE') == '1') and not os.getenv('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY 未配置：生产环境或 STANDALONE_MODE=1 时必须显式设置 SECRET_KEY 环境变量')
    init_plugs(app)

    with app.app_context():
        db.create_all()

    if config_name != 'testing':
        init_script(app)

    system_api(app)

    from flask import request
    from werkzeug.exceptions import HTTPException

    from applications.auth.guard import ensure_logged_in

    @app.before_request
    def protect_static_uploads():
        # 上传/生成目录位于 Flask 默认 static 目录下（static/upload 与 static/upload/res），
        # 蓝图级鉴权不覆盖 /static/<path>，会形成 /_uploads 登录门的免登录旁路（实测坐实）。
        if request.path.startswith('/static/'):
            unauthorized = ensure_logged_in()
            if unauthorized is not None:
                return unauthorized

    @app.errorhandler(Exception)
    def error_handler(e):
        # Flask 2.2 MRO 下 Exception handler 会吞掉 HTTPException（404/401 全变 200），
        # 必须先放行；非 HTTP 异常只回通用文案——str(e) 常含服务器绝对路径与子进程
        # stderr，回显属信息泄露，细节进服务端日志（debug 模式追加打印堆栈）。
        if isinstance(e, HTTPException):
            return e
        if app.debug:
            import traceback
            traceback.print_exc()
        app.logger.error("unhandled exception: %s", e, exc_info=True)
        from applications.common.utils.http import fail_api
        return fail_api("后端出现异常，请稍后重试")

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['JSON_AS_ASCII'] = False
    CORS(
        app,
        resources={
            r"/api/*": {"origins": _build_allowed_origins(app)},
            r"/_uploads/*": {"origins": _build_allowed_origins(app)},
        },
        supports_credentials=True,
    )

    return app
