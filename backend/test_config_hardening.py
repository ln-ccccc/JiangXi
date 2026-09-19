"""S5 回归（2026-09-19）：MySQL 弱口令静默回退清除 + 空/缺口令 fail-fast。

此前 config.py 两处 `or "123456"` 回退是检查现成把柄；现置空并由
create_app 门拦截——选了 MySQL 后端但没有 MYSQL_PASSWORD 时启动即报错
（compose 已强制注入；本地开发显式设环境变量或改 DB_BACKEND=sqlite）。
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from applications import create_app


class MysqlPasswordHardeningTests(unittest.TestCase):
    def test_no_weak_password_fallback_in_config_source(self):
        source = (
            Path(__file__).parent / "applications" / "configs" / "config.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("123456", source, "config.py 不得再出现弱口令回退字面量")

    def test_mysql_backend_without_password_fails_fast(self):
        env = {k: v for k, v in os.environ.items() if k not in ("MYSQL_PASSWORD", "STANDALONE_MODE")}
        env["DB_BACKEND"] = "mysql"
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "MYSQL_PASSWORD"):
                create_app("development")


if __name__ == "__main__":
    unittest.main()
