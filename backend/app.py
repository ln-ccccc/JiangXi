from flask import session
from flask_migrate import Migrate

from applications import create_app
from applications.extensions import db
from runtime_frontend_env import load_runtime_config, write_legacy_frontend_env

app = create_app()

# /static 上传目录鉴权与全局错误处理（HTTPException 直通、debug 打印堆栈、
# 生产只回通用文案不回显异常原文）注册在 create_app 工厂
# （applications/__init__.py），对所有配置环境与测试环境一致生效。


@app.before_request
def before():
    session.permanent = True
    app.permanent_session_lifetime = app.config['PERMANENT_SESSION_LIFETIME']
    if session.get("admin_user_id"):
        # 确保活动请求刷新永久会话的过期时间，覆盖直接加载图片的请求。
        session.modified = True


migrate = Migrate(app, db)

if __name__ == '__main__':
    config = load_runtime_config()
    write_legacy_frontend_env(config)
    app.run(
        host=config["host"]["backend"],
        port=config["port"]["backend"],
        debug=bool(config.get("debug", False)),
        use_reloader=bool(config.get("debug", False)),
    )
