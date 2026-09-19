"""S4（2026-09-19 审查）：登录失败限速——内网可达者此前可在线爆破唯一 admin。

内存态失败计数（键 = 客户端 IP|用户名）：MAX_FAILURES 次失败锁
LOCK_SECONDS 秒；失败路径另有固定延迟，使响应时序不泄露账号是否存在。
单进程部署（docker exec python app.py / gunicorn 单 worker）下内存态即可靠；
常量保持模块级以便测试注入。
"""

import threading
import time

MAX_FAILURES = 5
LOCK_SECONDS = 5 * 60
FIXED_DELAY_SECONDS = 0.5

_lock = threading.Lock()
# key -> {"count": int, "locked_until": float(monotonic)}
_failures = {}


def check_locked(key):
    """返回剩余锁定秒数；0 表示未锁。"""
    with _lock:
        entry = _failures.get(key)
        if not entry:
            return 0
        remaining = entry["locked_until"] - time.monotonic()
        if remaining > 0:
            return int(remaining) + 1
        return 0


def record_failure(key):
    with _lock:
        entry = _failures.setdefault(key, {"count": 0, "locked_until": 0.0})
        entry["count"] += 1
        if entry["count"] >= MAX_FAILURES:
            entry["locked_until"] = time.monotonic() + LOCK_SECONDS


def reset(key):
    with _lock:
        _failures.pop(key, None)


def fixed_delay():
    time.sleep(FIXED_DELAY_SECONDS)
