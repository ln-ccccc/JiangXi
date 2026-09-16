"""Static file server malformed-URL regression tests.

static-server.mjs 是 4173/4174 的主进程（start-frontend.sh / start-miner-web.sh
均 exec 它）：畸形百分号编码（如 /%E0%A4%A）会让 decodeURIComponent 抛 URIError，
历史上直接杀死进程。此处用真实子进程回归：坏 URL 必须 400，且进程必须存活。
"""

import http.client
import http.server
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


SERVER_PATH = Path(__file__).resolve().parents[1] / "static-server.mjs"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class StaticServerMalformedUrlTests(unittest.TestCase):
    def setUp(self):
        if shutil.which("node") is None:
            self.skipTest("node is not available on PATH")
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "index.html").write_text("<html>ok</html>", encoding="utf-8")
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen(
            ["node", str(SERVER_PATH), str(root), str(self.port), "/index.html"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            if self.proc.poll() is not None:
                self.fail(f"static-server exited during startup (code={self.proc.returncode})")
            try:
                with urllib.request.urlopen(f"{self.base_url}/index.html", timeout=2) as response:
                    if response.status == 200:
                        return
            except Exception:
                time.sleep(0.1)
        self.fail("static-server did not become ready in time")

    def tearDown(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self._tmp.cleanup()

    def _request(self, path):
        try:
            with urllib.request.urlopen(f"{self.base_url}{path}", timeout=5) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            try:
                return error.code, error.read()
            finally:
                error.close()

    def test_malformed_percent_encoding_returns_400_and_keeps_process_alive(self):
        status, body = self._request("/%E0%A4%A")
        self.assertEqual(status, 400)
        self.assertEqual(body, b"Bad Request")
        self.assertIsNone(self.proc.poll(), "server process must survive the malformed URL")
        # 坏请求之后进程仍能正常服务，证明没有崩溃
        status, _ = self._request("/index.html")
        self.assertEqual(status, 200)

    def test_truncated_percent_sequence_returns_400_without_killing_process(self):
        status, _ = self._request("/assets/%")
        self.assertEqual(status, 400)
        self.assertIsNone(self.proc.poll())
        status, _ = self._request("/index.html")
        self.assertEqual(status, 200)


class _StubUpstreamHandler(http.server.BaseHTTPRequestHandler):
    """记录最近一次请求路径并返回固定标记，用于验证代理转发的真实去向。"""

    def do_GET(self):
        self.server.last_path = self.path
        body = b"upstream-ok"
        self.send_response(200)
        self.send_header("content-type", "text/plain; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class StaticServerProxyOriginGuardTests(unittest.TestCase):
    """P1-4 SSRF 回归：代理分支的重组目标必须与配置上游同源。

    new URL(request.url, proxy.target) 在 request.url 携带绝对 URL
    （http://169.254.169.254/...）或协议相对 URL（//evil.example/...）时 base 被
    整体覆盖，method/headers/body 全转发，等于任意主机中继。此处起真实上游 stub
    + 真实 static-server 子进程（PROXY_API_TARGET 指向上游）验证三种形态。
    """

    def setUp(self):
        if shutil.which("node") is None:
            self.skipTest("node is not available on PATH")
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "index.html").write_text("<html>ok</html>", encoding="utf-8")

        self.upstream = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), _StubUpstreamHandler
        )
        self.upstream.last_path = None
        self.upstream_port = self.upstream.server_address[1]
        self.upstream_thread = threading.Thread(
            target=self.upstream.serve_forever, daemon=True
        )
        self.upstream_thread.start()

        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen(
            ["node", str(SERVER_PATH), str(root), str(self.port), "/index.html"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                **os.environ,
                "PROXY_API_TARGET": f"http://127.0.0.1:{self.upstream_port}",
            },
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            if self.proc.poll() is not None:
                self._stop_upstream()
                self.fail(f"static-server exited during startup (code={self.proc.returncode})")
            try:
                with urllib.request.urlopen(f"{self.base_url}/index.html", timeout=2) as response:
                    if response.status == 200:
                        return
            except Exception:
                time.sleep(0.1)
        self._stop_upstream()
        self.fail("static-server did not become ready in time")

    def tearDown(self):
        proc = getattr(self, "proc", None)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        self._stop_upstream()
        self._tmp.cleanup()

    def _stop_upstream(self):
        self.upstream.shutdown()
        self.upstream.server_close()
        self.upstream_thread.join(timeout=5)

    def _request(self, path):
        try:
            with urllib.request.urlopen(f"{self.base_url}{path}", timeout=5) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            try:
                return error.code, error.read()
            finally:
                error.close()

    def test_absolute_url_hijack_returns_400_and_never_reaches_other_host(self):
        # 绝对 URL 劫持：请求目标是本服务，但 request.url 自带 authority
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", "http://169.254.169.254/latest/meta-data/")
            response = connection.getresponse()
            status = response.status
            body = response.read()
        finally:
            connection.close()
        self.assertEqual(status, 400)
        self.assertEqual(body, b"Bad Request")
        self.assertIsNone(
            self.upstream.last_path, "hijacked request must not reach any upstream"
        )
        self.assertIsNone(self.proc.poll(), "server process must survive the hijack attempt")
        status, _ = self._request("/index.html")
        self.assertEqual(status, 200)

    def test_protocol_relative_url_hijack_returns_400(self):
        status, body = self._request("//evil.example/api/session")
        self.assertEqual(status, 400)
        self.assertEqual(body, b"Bad Request")
        self.assertIsNone(self.upstream.last_path)
        self.assertIsNone(self.proc.poll())
        status, _ = self._request("/index.html")
        self.assertEqual(status, 200)

    def test_normal_api_path_is_forwarded_to_configured_upstream(self):
        status, body = self._request("/api/ping?z=1")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"upstream-ok")
        self.assertEqual(self.upstream.last_path, "/api/ping?z=1")
        self.assertIsNone(self.proc.poll())


if __name__ == "__main__":
    unittest.main()
