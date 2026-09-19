"""P1-3 回归（2026-09-19）：上传必须有请求体硬上限，非 TIFF 文件同样受限。

此前 8GB 上限只对扩展名 .tif 生效：9GB 随机数据改名 .png 可整包 spool
并落盘（2× 文件大小的磁盘开销，几次即可写满卷——磁盘耗尽型 DoS）。
现在：
1. BaseConfig.MAX_CONTENT_LENGTH = 8.5GiB——Werkzeug 超限 413 提前掐断，
   multipart 不再全量 spool；
2. /api/file/upload 对所有文件 seek/tell 比大小，非 TIFF 一视同仁。
"""

import unittest
from unittest.mock import patch

from applications import create_app
from applications.configs.config import BaseConfig


def _multipart(fields=None, files=None):
    """手工构造 multipart/form-data 体：文件内容驻内存，直接控大小。

    表单字段不带 filename（Werkzeug 以 filename 判定 file part，
    带 filename 的字段不会出现在 request.form 里）。
    """
    boundary = "----jxuploadboundary"
    body = b""
    for name, value in (fields or {}).items():
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        ).encode("utf-8")
        body += value.encode("utf-8") if isinstance(value, str) else value
        body += b"\r\n"
    for field, filename, payload in files or []:
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        body += payload + b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


class UploadHardLimitTests(unittest.TestCase):
    def setUp(self):
        # 设备钉 cpu：与 T1 一致，测试不依赖宿主 GPU
        self._device_env_patcher = patch.dict(
            "os.environ", {"JIANGXI_INFERENCE_DEVICE": "cpu"}
        )
        self._device_env_patcher.start()
        self.app = create_app("testing")
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.client = self.app.test_client()
        ctx = self.app.app_context()
        ctx.push()
        self.addCleanup(ctx.pop)
        self.addCleanup(self._device_env_patcher.stop)

    def _login(self):
        self.app.config["ADMIN_USERNAME"] = "admin"
        self.app.config["ADMIN_PASSWORD"] = "Secret123!"
        import os

        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD"] = "Secret123!"
        from applications.auth.service import sync_admin_from_env

        sync_admin_from_env()
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Secret123!"},
        )
        self.assertEqual(response.status_code, 200)

    def test_base_config_caps_request_body_at_8_5_gib(self):
        # 业务上限 8GB（MAX_UPLOAD_TIFF_SIZE_MB=8192），Werkzeug 层留 0.5GiB 裕量
        self.assertEqual(BaseConfig.MAX_CONTENT_LENGTH, int(8.5 * 1024 ** 3))

    def test_oversized_request_body_is_rejected_with_413(self):
        # P1-3：超限请求必须在 Werkzeug 层 413 掐断，先于任何业务代码落盘
        self._login()
        self.app.config["MAX_CONTENT_LENGTH"] = 1024
        body, content_type = _multipart(
            files=[("files", "big.tif", b"\x00" * 4096)], fields={"type": "satellite"}
        )
        response = self.client.post(
            "/api/file/upload", data=body, content_type=content_type
        )
        self.assertEqual(response.status_code, 413)

    def test_non_tiff_upload_is_size_capped_too(self):
        # P1-3 主场景：9GB png 之前畅通无阻——扩展名白名单不等于免检。
        # 路由内 seek/tell 检查对非 TIFF 一视同仁（这里把业务上限调小便于单测）
        self._login()
        self.app.config["MAX_CONTENT_LENGTH"] = None
        with patch("applications.api.file.MAX_UPLOAD_TIFF_SIZE_MB", 1):
            body, content_type = _multipart(
                fields={"type": "satellite"},
                files=[("files", "huge.png", b"\x00" * (2 * 1024 * 1024))],
            )
            response = self.client.post(
                "/api/file/upload", data=body, content_type=content_type
            )

        payload = response.get_json()
        self.assertIsNotNone(payload)
        self.assertFalse(payload.get("success"), payload)
        self.assertIn("超过硬上限", payload.get("msg", ""))


if __name__ == "__main__":
    unittest.main()
