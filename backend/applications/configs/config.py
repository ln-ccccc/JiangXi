import logging
import os
from pathlib import Path
from urllib.parse import quote_plus


def _bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_database_uri():
    backend = (os.getenv("DB_BACKEND") or "mysql").strip().lower()
    if backend == "sqlite":
        sqlite_path = Path(os.getenv("SQLITE_PATH") or "/app/runtime_data/jiangxi.sqlite3")
        return f"sqlite:///{sqlite_path.as_posix()}"

    mysql_username = os.getenv("MYSQL_USERNAME") or "root"
    mysql_password = os.getenv("MYSQL_PASSWORD") or "123456"
    mysql_host = os.getenv("MYSQL_HOST") or "127.0.0.1"
    mysql_port = int(os.getenv("MYSQL_PORT") or 3306)
    mysql_database = os.getenv("MYSQL_DATABASE") or "AdminFlask"
    return (
        "mysql+pymysql://"
        f"{mysql_username}:{quote_plus(mysql_password)}@{mysql_host}:{mysql_port}/{mysql_database}"
        "?charset=utf8mb4"
    )


class BaseConfig:
    SYSTEM_NAME = os.getenv('SYSTEM_NAME', 'Admin')
    # 主题面板的链接列表配置
    SYSTEM_PANEL_LINKS = []

    UPLOADED_PHOTOS_DEST = 'static/upload'
    UPLOADED_FILES_ALLOW = ['gif', 'jpg', 'png']

    # JSON配置
    JSON_AS_ASCII = False

    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev key'
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')
    FRONTEND_PORT = int(os.getenv('FRONTEND_PORT') or 3000)
    MINER_FRONTEND_PORT = int(os.getenv('MINER_FRONTEND_PORT') or 4000)
    SESSION_COOKIE_NAME = os.getenv('SESSION_COOKIE_NAME') or 'jiangxi_session'
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _bool_env('SESSION_COOKIE_SECURE', False)
    CORS_ALLOWED_ORIGINS = os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://127.0.0.1:4173,http://127.0.0.1:4174',
    )

    # redis配置
    REDIS_HOST = os.getenv('REDIS_HOST') or "127.0.0.1"
    REDIS_PORT = int(os.getenv('REDIS_PORT') or 6379)

    DB_BACKEND = (os.getenv("DB_BACKEND") or "mysql").strip().lower()
    SQLITE_PATH = os.getenv("SQLITE_PATH") or "/app/runtime_data/jiangxi.sqlite3"
    PROJECT_OUTPUT_ROOT = os.getenv("PROJECT_OUTPUT_ROOT") or str(
        Path(__file__).resolve().parents[2] / "static" / "project_outputs"
    )
    KML_ROI_INPUT_ROOT = os.getenv("KML_ROI_INPUT_ROOT") or str(
        Path(__file__).resolve().parents[2] / "bianhua_2years"
    )
    KML_ROI_KML_ROOT = os.getenv("KML_ROI_KML_ROOT") or "/app/runtime_data"

    # mysql 配置
    MYSQL_USERNAME = os.getenv('MYSQL_USERNAME') or "root"
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD') or "123456"
    MYSQL_HOST = os.getenv('MYSQL_HOST') or "127.0.0.1"
    MYSQL_PORT = int(os.getenv('MYSQL_PORT') or 3306)
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE') or "AdminFlask"

    # 数据库连接
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    # 默认日志等级
    LOG_LEVEL = logging.WARN
    #
    MAIL_SERVER = os.getenv('MAIL_SERVER') or 'smtp.qq.com'
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_PORT = 465
    MAIL_USERNAME = os.getenv('MAIL_USERNAME') or '123@qq.com'
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD') or 'XXXXX'  # 生成的授权码
    # 默认发件人的邮箱,这里填写和MAIL_USERNAME一致即可
    MAIL_DEFAULT_SENDER = ('admin', os.getenv('MAIL_USERNAME') or '123@qq.com')


class TestingConfig(BaseConfig):
    """ 测试配置 """
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # 内存数据库
    TESTING = True


class DevelopmentConfig(BaseConfig):
    """ 开发配置 """
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(BaseConfig):
    """生成环境配置"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_POOL_RECYCLE = 8

    LOG_LEVEL = logging.ERROR


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
