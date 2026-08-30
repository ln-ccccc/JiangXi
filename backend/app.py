import traceback

from flask import session
from flask_migrate import Migrate

from applications import create_app
from applications.common.utils.http import fail_api
from applications.extensions import db
from runtime_frontend_env import load_runtime_config, write_legacy_frontend_env

debug_mode = False
app = create_app()


@app.before_request
def before():
    session.permanent = True
    app.permanent_session_lifetime = app.config['PERMANENT_SESSION_LIFETIME']
    if session.get("admin_user_id"):
        # 确保活动请求刷新永久会话的过期时间，覆盖直接加载图片的请求。
        session.modified = True


@app.errorhandler(Exception)
def error_handler(e):
    if debug_mode:
        traceback.print_exc()
    return fail_api("后端出现异常：{}".format(str(e)))


migrate = Migrate(app, db)

if __name__ == '__main__':
    config = load_runtime_config()
    debug_mode = bool(config.get("debug", False))
    write_legacy_frontend_env(config)
    app.run(
        host=config["host"]["backend"],
        port=config["port"]["backend"],
        debug=debug_mode,
        use_reloader=debug_mode,
    )
