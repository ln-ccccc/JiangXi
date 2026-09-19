import importlib
import os
import tempfile
import unittest
from unittest import mock

from applications import create_app


class ApiRobustnessTestCase(unittest.TestCase):
    """复审批次 A6：查询参数与空 body 的容错不应进全局异常处理器。"""

    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()

    def test_kml_roi_history_non_numeric_page_falls_back_to_default(self):
        # 修复前 int('abc') 抛 ValueError，整页 200+「后端出现异常」错误体
        with self.client.session_transaction() as sess:
            sess["admin_user_id"] = 1
        resp = self.client.get("/api/analysis/kml_roi_history?page=abc&limit=xyz")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body.get("code"), 0)

    def test_history_batch_remove_json_null_body_returns_param_error(self):
        # body 为合法 JSON null 时 request.json 为 None，缺省容错后应返回参数异常
        with self.client.session_transaction() as sess:
            sess["admin_user_id"] = 1
        resp = self.client.delete(
            "/api/history/batchRemove",
            data="null",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body.get("code"), 1)
        self.assertEqual(body.get("msg"), "参数异常")

    def test_history_batch_remove_without_body_returns_client_error(self):
        # 无 JSON content-type 时 get_json 抛 HTTPException，必须原样直通
        # （不被全局处理器吞成 200 JSON）。具体码随 Werkzeug 版本：
        # 2.2 抛 400 BadRequest，2.3+ 抛 415 UnsupportedMediaType（语义更准），
        # 断言锁定「4xx 客户端错误直通」这一契约而非版本细节。
        with self.client.session_transaction() as sess:
            sess["admin_user_id"] = 1
        resp = self.client.delete("/api/history/batchRemove")
        self.assertIn(resp.status_code, (400, 415))


class InitDbFailureTests(unittest.TestCase):
    """复审批次 A5：init_db 建表语句失败必须显式失败，不得静默吞掉。"""

    @staticmethod
    def _run_execute_fromfile(sql, execute_side_effect):
        # 包 __init__ 重导出了 init_db 符号，importlib 拿真正的模块对象
        init_db_module = importlib.import_module(
            "applications.common.scripts.init_db"
        )

        fd, path = tempfile.mkstemp(suffix=".sql")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(sql)
            conn = mock.MagicMock()
            cursor = mock.MagicMock()
            cursor.execute.side_effect = execute_side_effect
            conn.cursor.return_value = cursor
            with mock.patch.object(init_db_module.pymysql, "connect", return_value=conn):
                init_db_module.execute_fromfile(path)
            return conn, cursor
        finally:
            os.unlink(path)

    def test_failed_statement_raises_and_closes_connection(self):
        with self.assertRaises(RuntimeError):
            self._run_execute_fromfile(
                "CREATE TABLE a(x INT);\n\nCREATE TABLE b(y INT);",
                [None, RuntimeError("boom")],
            )

    def test_all_statements_pass_without_error(self):
        conn, cursor = self._run_execute_fromfile(
            "CREATE TABLE a(x INT);\n\nCREATE TABLE b(y INT);", None
        )
        # 尾部空语句（split(';') 的空串）应被跳过，不进入 execute
        self.assertEqual(cursor.execute.call_count, 2)
        conn.close.assert_called()


if __name__ == "__main__":
    unittest.main()
