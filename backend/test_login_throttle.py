"""S4 回归（2026-09-19）：登录失败限速——内网可达者此前可无限次在线爆破唯一 admin。

策略：内存态失败计数（键 = 客户端 IP|用户名），5 次失败锁 5 分钟；
锁定期间请求在密码校验前即 429；失败路径加固定延迟，避免响应时序泄露
账号存在性。单进程部署（docker exec python app.py）内存态即可靠。
"""

import unittest
from unittest.mock import patch

from applications import create_app
from applications.auth import throttle as login_throttle
from applications.extensions import db


class LoginThrottleUnitTests(unittest.TestCase):
    def setUp(self):
        login_throttle._failures.clear()

    def tearDown(self):
        login_throttle._failures.clear()

    def test_locks_after_max_failures_and_reports_remaining_seconds(self):
        for _ in range(login_throttle.MAX_FAILURES):
            login_throttle.record_failure("ip|admin")
        self.assertGreater(login_throttle.check_locked("ip|admin"), 0)
        self.assertEqual(login_throttle.check_locked("ip|other"), 0)

    def test_success_resets_failure_count(self):
        for _ in range(login_throttle.MAX_FAILURES - 1):
            login_throttle.record_failure("ip|admin")
        login_throttle.reset("ip|admin")
        login_throttle.record_failure("ip|admin")
        self.assertEqual(login_throttle.check_locked("ip|admin"), 0)

    def test_lock_expires_after_window(self):
        login_throttle.record_failure("ip|admin")
        with patch.object(login_throttle, "LOCK_SECONDS", 0.0), patch.object(
            login_throttle, "MAX_FAILURES", 1
        ):
            login_throttle.record_failure("ip|expired")
            # LOCK_SECONDS=0 → locked_until=now → 立即过期
            self.assertEqual(login_throttle.check_locked("ip|expired"), 0)


class LoginThrottleApiTests(unittest.TestCase):
    def setUp(self):
        self._device_env_patcher = patch.dict(
            "os.environ", {"JIANGXI_INFERENCE_DEVICE": "cpu"}
        )
        self._device_env_patcher.start()
        self.app = create_app("testing")
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self._device_env_patcher.stop()
        login_throttle._failures.clear()

    def _login(self, password="wrong-password"):
        return self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": password},
        )

    def test_sixth_consecutive_failure_is_rejected_before_password_check(self):
        calls = []

        def fake_authenticate(username, password):
            calls.append((username, password))
            return None

        self.app.config["ADMIN_USERNAME"] = "admin"
        self.app.config["ADMIN_PASSWORD"] = "Secret123!"
        import os

        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD"] = "Secret123!"
        from applications.auth.service import sync_admin_from_env

        sync_admin_from_env()

        with patch("applications.api.auth.authenticate_admin", side_effect=fake_authenticate):
            for i in range(login_throttle.MAX_FAILURES):
                response = self._login()
                self.assertEqual(response.status_code, 401, f"第 {i + 1} 次应仍是 401")

            response = self._login()
            self.assertEqual(response.status_code, 429)
            # 锁定期间不再触发密码校验（爆破成本最大化）
            self.assertEqual(len(calls), login_throttle.MAX_FAILURES)

        # 正确密码也被锁挡下（同一键），锁定过期后恢复
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Secret123!"},
        )
        self.assertEqual(response.status_code, 429)

    def test_failure_path_has_fixed_delay(self):
        sleeps = []
        with patch(
            "applications.api.auth.login_throttle.fixed_delay",
            side_effect=lambda: sleeps.append(1),
        ):
            self._login()
        self.assertEqual(len(sleeps), 1, "失败路径必须经过固定延迟")


if __name__ == "__main__":
    unittest.main()
