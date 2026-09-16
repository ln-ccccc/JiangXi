import os
import unittest

from applications import create_app


class AppFactoryIsolationTestCase(unittest.TestCase):
    def test_testing_config_does_not_use_runtime_sqlite_path(self):
        old_backend = os.environ.get("DB_BACKEND")
        old_path = os.environ.get("SQLITE_PATH")
        try:
            os.environ["DB_BACKEND"] = "sqlite"
            os.environ["SQLITE_PATH"] = "/app/runtime_data/jiangxi.sqlite3"
            app = create_app("testing")
            self.assertEqual(app.config["SQLALCHEMY_DATABASE_URI"], "sqlite:///:memory:")
        finally:
            if old_backend is None:
                os.environ.pop("DB_BACKEND", None)
            else:
                os.environ["DB_BACKEND"] = old_backend
            if old_path is None:
                os.environ.pop("SQLITE_PATH", None)
            else:
                os.environ["SQLITE_PATH"] = old_path


    def test_standalone_mode_without_secret_key_raises(self):
        old_standalone = os.environ.get("STANDALONE_MODE")
        old_secret = os.environ.get("SECRET_KEY")
        try:
            os.environ["STANDALONE_MODE"] = "1"
            os.environ.pop("SECRET_KEY", None)
            with self.assertRaises(RuntimeError) as ctx:
                create_app("testing")
            self.assertIn("SECRET_KEY", str(ctx.exception))
        finally:
            if old_standalone is None:
                os.environ.pop("STANDALONE_MODE", None)
            else:
                os.environ["STANDALONE_MODE"] = old_standalone
            if old_secret is not None:
                os.environ["SECRET_KEY"] = old_secret

    def test_standalone_mode_with_secret_key_bootstraps(self):
        old_standalone = os.environ.get("STANDALONE_MODE")
        old_secret = os.environ.get("SECRET_KEY")
        try:
            os.environ["STANDALONE_MODE"] = "1"
            os.environ["SECRET_KEY"] = "unit-test-only-not-a-real-secret"
            app = create_app("testing")
            self.assertIsNotNone(app)
        finally:
            if old_standalone is None:
                os.environ.pop("STANDALONE_MODE", None)
            else:
                os.environ["STANDALONE_MODE"] = old_standalone
            if old_secret is None:
                os.environ.pop("SECRET_KEY", None)
            else:
                os.environ["SECRET_KEY"] = old_secret

    def test_non_standalone_without_secret_key_still_bootstraps(self):
        old_standalone = os.environ.get("STANDALONE_MODE")
        old_secret = os.environ.get("SECRET_KEY")
        try:
            os.environ.pop("STANDALONE_MODE", None)
            os.environ.pop("SECRET_KEY", None)
            app = create_app("testing")
            self.assertIsNotNone(app)
        finally:
            if old_standalone is not None:
                os.environ["STANDALONE_MODE"] = old_standalone
            if old_secret is not None:
                os.environ["SECRET_KEY"] = old_secret


class GlobalErrorHandlingTests(unittest.TestCase):
    """create_app 工厂级错误处理契约（2026-09-14 独立复审修复项）。"""

    def test_unknown_route_returns_real_404(self):
        # Flask 2.2 MRO 下 Exception handler 若不放行 HTTPException，404 会被
        # 吞成 200 + JSON 错误体（运行容器实测坐实过）
        app = create_app("testing")
        client = app.test_client()
        resp = client.get("/api/no-such-route")
        self.assertEqual(resp.status_code, 404)

    def test_static_uploads_require_login(self):
        # 上传目录位于 Flask 默认 static 下，蓝图级鉴权不覆盖 /static/<path>，
        # 会形成 /_uploads 登录门的免登录旁路（实测免登录可完整下载 tif）
        app = create_app("testing")
        client = app.test_client()
        resp = client.get("/static/upload/whatever.tif")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
