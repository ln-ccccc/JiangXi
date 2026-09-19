from flask import Blueprint, jsonify, request, session

from applications.auth import throttle as login_throttle
from applications.auth.service import authenticate_admin
from applications.common.utils.http import success_api

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@auth_api.post("/login")
def login_api():
    payload = request.json or {}
    # S4（2026-09-19 审查）：按 IP|用户名 失败限速，锁定在密码校验前拦下
    throttle_key = f"{request.remote_addr or 'unknown'}|{payload.get('username') or ''}"
    locked_for = login_throttle.check_locked(throttle_key)
    if locked_for:
        return (
            jsonify(success=False, code=429, msg=f"失败次数过多，请 {locked_for} 秒后重试"),
            429,
        )

    user = authenticate_admin(payload.get("username"), payload.get("password"))
    if user is None:
        # 固定延迟：失败响应时序不因账号是否存在而异
        login_throttle.fixed_delay()
        login_throttle.record_failure(throttle_key)
        return jsonify(success=False, code=401, msg="账号或密码错误"), 401

    login_throttle.reset(throttle_key)
    session.clear()
    session.permanent = True
    session["admin_user_id"] = user.id
    session["admin_username"] = user.username
    return success_api(data={"authenticated": True, "username": user.username})


@auth_api.get("/session")
def session_api():
    return success_api(
        data={
            "authenticated": bool(session.get("admin_user_id")),
            "username": session.get("admin_username"),
        }
    )


@auth_api.post("/logout")
def logout_api():
    session.clear()
    return success_api(msg="已退出登录", data={"authenticated": False, "username": None})
