"""compose 与镜像内 healthcheck 探测端点一致性守卫（P2-13）。

docker-compose.prod.yml 四个应用服务的 python3 urllib 探测与
docker/standalone/healthcheck.sh 的探测端点是两处独立定义（2026-09-16 曾同批
手改对齐），此前没有任何测试钉住——「一处改一处漏」只靠人肉。此处用源码断言
（仿 backend/test_jiangxi_gpu_contract.py 先例）把两侧端点钉在同一张契约表上。
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.prod.yml"
HEALTHCHECK_PATH = ROOT / "docker" / "standalone" / "healthcheck.sh"

# compose 服务 -> (容器内端口, healthcheck.sh 端口变量, compose 探测路径,
#                  healthcheck.sh 探测路径)
# backend 根路径无路由（404 语义），两处都必须钉在会话端点 /api/auth/session；
# miner-api 在 healthcheck.sh 中刻意用更深的 /api/health/jiangxi（含 manifest
# 哈希/设备校验），compose 用轻量会话端点——改任何一处必须同步更新本表
EXPECTED_PROBES = {
    "backend": ("5008", "BACKEND_PORT", "/api/auth/session", "/api/auth/session"),
    "frontend": ("3000", "FRONTEND_PORT", "/", "/"),
    "miner-api": ("8000", "MINER_BACKEND_PORT", "/api/auth/session", "/api/health/jiangxi"),
    "miner-web": ("4000", "MINER_FRONTEND_PORT", "/", "/"),
}

PROBE_URL_PATTERN = re.compile(r'urlopen\(\\"([^"\\]+)\\"')


def compose_probe_urls(compose_text):
    """按服务段提取 compose 内 python3 urllib 探测 URL。

    服务名 = services: 下两空格缩进的键；mysql 等非 urllib 探测自然不入表。
    """
    probes = {}
    service = None
    for line in compose_text.splitlines():
        header = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if header:
            service = header.group(1)
            continue
        match = PROBE_URL_PATTERN.search(line)
        if match and service:
            if service in probes:
                raise AssertionError(
                    f"{service} 有多条 urlopen 探测，无法唯一锁定契约"
                )
            probes[service] = match.group(1)
    return probes


class HealthcheckProbeContractTests(unittest.TestCase):
    def setUp(self):
        self.compose_text = COMPOSE_PATH.read_text(encoding="utf-8")
        self.healthcheck_text = HEALTHCHECK_PATH.read_text(encoding="utf-8")

    def test_compose_and_image_healthcheck_probe_endpoints_stay_consistent(self):
        probes = compose_probe_urls(self.compose_text)
        self.assertEqual(
            set(probes),
            set(EXPECTED_PROBES),
            "compose 四个应用服务应各有一条 python3 urllib 探测（mysql 走 mysqladmin 不算）",
        )
        for service, (port, port_variable, compose_path, healthcheck_path) in (
            EXPECTED_PROBES.items()
        ):
            self.assertEqual(
                probes[service],
                f"http://127.0.0.1:{port}{compose_path}",
                f"compose 中 {service} 的 healthcheck 探测端点漂移",
            )
            self.assertIn(
                f"http://127.0.0.1:${{{port_variable}}}{healthcheck_path}",
                self.healthcheck_text,
                f"healthcheck.sh 中 ${{{port_variable}}} 的探测端点漂移",
            )

    def test_backend_probe_uses_session_endpoint_not_root(self):
        # backend 根路径无路由（404 语义修复后不再被吞成 200）：任何一侧改回
        # 探测 "/" 都会把真实存活误判为 unhealthy
        probes = compose_probe_urls(self.compose_text)
        self.assertEqual(probes["backend"], "http://127.0.0.1:5008/api/auth/session")
        self.assertIn(
            "http://127.0.0.1:${BACKEND_PORT}/api/auth/session",
            self.healthcheck_text,
        )

    def test_healthcheck_probes_use_python3_urllib_without_curl(self):
        # standalone 运行镜像内无 curl，两侧统一 python3 urllib（HTTP>=400 抛异常）
        test_lines = [
            line for line in self.compose_text.splitlines() if "CMD-SHELL" in line
        ]
        self.assertTrue(test_lines, "compose 应定义 CMD-SHELL 探测")
        for line in test_lines:
            self.assertNotIn("curl", line, f"compose 探测不得用 curl: {line!r}")
        self.assertNotIn("curl", self.healthcheck_text, "healthcheck.sh 不得用 curl")
        self.assertIn("urllib.request", self.healthcheck_text)


if __name__ == "__main__":
    unittest.main()
