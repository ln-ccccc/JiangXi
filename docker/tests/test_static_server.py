"""Static file server malformed-URL regression tests.

static-server.mjs 是 4173/4174 的主进程（start-frontend.sh / start-miner-web.sh
均 exec 它）：畸形百分号编码（如 /%E0%A4%A）会让 decodeURIComponent 抛 URIError，
历史上直接杀死进程。此处用真实子进程回归：坏 URL 必须 400，且进程必须存活。
"""

import shutil
import socket
import subprocess
import tempfile
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


if __name__ == "__main__":
    unittest.main()
