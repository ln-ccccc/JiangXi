import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
import socket

from applications.interface.mmseg_worker import (
    MmsegWorker,
    WorkerUnavailableError,
    _remove_stale_socket,
    request_worker,
    serve_worker,
)


class MmsegWorkerTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.model = object()

        def infer(**kwargs):
            self.calls.append(kwargs)
            return {
                "status": "completed",
                "total": len(kwargs["file_names"]),
                "success": len(kwargs["file_names"]),
                "results": [
                    {
                        "name": f"pred_{Path(name).stem}.png",
                        "status": "success",
                    }
                    for name in kwargs["file_names"]
                ],
                "runtime": {"effective_device": "cuda:0"},
            }

        self.worker = MmsegWorker(
            model=self.model,
            runtime={
                "requested_device": "cuda:0",
                "effective_device": "cuda:0",
                "device_name": "test-gpu",
            },
            inference_fn=infer,
        )

    def test_ping_reports_loaded_gpu_model(self):
        response = self.worker.handle_request({"action": "ping"})

        self.assertEqual(response["status"], "ok")
        self.assertTrue(response["model_ready"])
        self.assertTrue(response["asset_validation_passed"])
        self.assertEqual(response["runtime"]["effective_device"], "cuda:0")

    def test_continuous_requests_reuse_the_same_loaded_model(self):
        request = {
            "action": "infer",
            "input_dir": "/input",
            "output_dir": "/output",
            "file_names": ["first.tif"],
            "submitted_at": time.time() - 0.01,
        }

        first = self.worker.handle_request(request)
        second = self.worker.handle_request({**request, "file_names": ["second.tif"]})

        self.assertEqual([call["model"] for call in self.calls], [self.model, self.model])
        self.assertEqual(first["runtime"]["model_load_once"], True)
        self.assertEqual(second["runtime"]["model_load_once"], True)
        self.assertGreaterEqual(first["runtime"]["queue_wait_seconds"], 0)
        self.assertEqual(second["results"][0]["name"], "pred_second.png")

    def test_invalid_request_returns_structured_error(self):
        response = self.worker.handle_request({"action": "unsupported"})

        self.assertEqual(response["status"], "error")
        self.assertIn("未知", response["error"])

    def test_socket_client_reports_missing_worker_without_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_socket = Path(temp_dir) / "missing.sock"
            with self.assertRaisesRegex(WorkerUnavailableError, "GPU 推理 Worker 不可用"):
                request_worker(str(missing_socket), {"action": "ping"}, timeout=0.1)

    def test_refuses_to_replace_an_active_socket(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            socket_path = Path(temp_dir) / "worker.sock"
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                server.bind(str(socket_path))
                server.listen(1)
                with self.assertRaisesRegex(RuntimeError, "已在运行"):
                    _remove_stale_socket(str(socket_path))
            finally:
                server.close()

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "AF_UNIX 仅在 Linux/容器环境可用")
    def test_survives_client_disconnect_before_response(self):
        """客户端不读响应就断开（如健康检查超时留下的陈旧连接）不得终止 serve 循环。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            socket_path = Path(temp_dir) / "worker.sock"
            serve_failures = []

            def run_server():
                try:
                    serve_worker(str(socket_path), self.worker)
                except Exception as exc:
                    serve_failures.append(exc)

            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()
            deadline = time.time() + 5
            while not socket_path.exists() and time.time() < deadline:
                time.sleep(0.05)
            self.assertTrue(socket_path.exists(), "serve_worker 未在期限内创建 socket")

            abusive = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                abusive.connect(str(socket_path))
                request = {
                    "action": "infer",
                    "input_dir": "/input",
                    "output_dir": "/output",
                    "file_names": ["a.tif"],
                }
                abusive.sendall((json.dumps(request) + "\n").encode("utf-8"))
            finally:
                abusive.close()

            pong = request_worker(str(socket_path), {"action": "ping"}, timeout=5.0)
            self.assertEqual(pong.get("status"), "ok")
            third = request_worker(
                str(socket_path),
                {
                    "action": "infer",
                    "input_dir": "/input",
                    "output_dir": "/output",
                    "file_names": ["b.tif"],
                },
                timeout=5.0,
            )
            self.assertEqual(third.get("status"), "completed")
            self.assertEqual(third["results"][0]["name"], "pred_b.png")
            self.assertTrue(thread.is_alive(), "serve_worker 因单客户端断开而退出")
            self.assertEqual(serve_failures, [])


if __name__ == "__main__":
    unittest.main()
