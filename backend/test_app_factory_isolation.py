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


if __name__ == "__main__":
    unittest.main()
