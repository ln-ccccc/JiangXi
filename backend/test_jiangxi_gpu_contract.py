import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class JiangxiGpuContractTests(unittest.TestCase):
    def test_standalone_dockerfile_exposes_selectable_inference_device(self):
        source = (ROOT / "docker" / "standalone" / "Dockerfile.jiangxi").read_text(
            encoding="utf-8"
        )
        self.assertIn("ARG JIANGXI_INFERENCE_DEVICE=cpu", source)
        self.assertIn("JIANGXI_INFERENCE_DEVICE=${JIANGXI_INFERENCE_DEVICE}", source)
        self.assertIn("torch.version.cuda", source)

    def test_entrypoint_validates_configured_device_in_the_real_python_runtime(self):
        source = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("resolve_inference_device", source)
        self.assertIn("JIANGXI_INFERENCE_DEVICE", source)

    def test_healthcheck_compares_against_configured_device(self):
        source = (ROOT / "docker" / "standalone" / "healthcheck.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("JIANGXI_INFERENCE_DEVICE", source)
        self.assertIn("urllib.request", source)
        self.assertNotIn("curl -fsS", source)
        self.assertNotIn('health.get("model_device") != "cpu"', source)

    def test_standalone_forces_sqlite_and_persistent_inference_outputs(self):
        source = (ROOT / "docker" / "standalone" / "start-jiangxi-standalone.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('export DB_BACKEND="sqlite"', source)
        self.assertIn('export MINER_CHANGE_OUTPUT_ROOT="${RUNTIME_DATA_DIR}/change_matrix_outputs"', source)

    def test_standalone_healthcheck_allows_model_and_service_startup_time(self):
        source = (ROOT / "docker" / "standalone" / "Dockerfile.jiangxi").read_text(
            encoding="utf-8"
        )
        self.assertIn("HEALTHCHECK --interval=30s --timeout=15s", source)

    def test_gpu_build_reuses_the_torch_compatible_mmcv_extension(self):
        source = (ROOT / "docker" / "standalone" / "Dockerfile.jiangxi").read_text(
            encoding="utf-8"
        )
        self.assertIn("ARG JIANGXI_RUNTIME_COMPAT_IMAGE=jiangxi-runtime:current", source)
        self.assertIn("FROM ${JIANGXI_RUNTIME_COMPAT_IMAGE} AS jiangxi-runtime-compat", source)
        self.assertIn("COPY --from=jiangxi-runtime-compat /opt/conda /opt/conda", source)
        self.assertIn("COPY --from=jiangxi-runtime-compat /opt/node20 /opt/node20", source)
        self.assertIn("PATH=/opt/node20/bin:${PATH}", source)
        self.assertIn("@rollup/rollup-linux-x64-gnu", source)
        self.assertIn("@esbuild/linux-x64", source)
        self.assertIn("--include=dev", source)
        self.assertIn("--prefix /app/frontend", source)
        self.assertIn("vue-cli-service", source)
        self.assertIn("jiangxi-analysis-worker:gpu", source)
        self.assertIn("COPY --from=jiangxi-gpu-compat", source)
        self.assertIn("mmcv-2.1.0.dist-info", source)
        self.assertIn("rm -rf /opt/conda/envs/MMSeg310/lib/python3.10/site-packages/mmcv", source)
        self.assertIn("if grep -Fq", source)
        self.assertIn("Unsupported MMDetection", source)

    def test_gpu_standalone_starts_a_persistent_worker_before_flask(self):
        standalone = (
            ROOT / "docker" / "standalone" / "start-jiangxi-standalone.sh"
        ).read_text(encoding="utf-8")
        entrypoint = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")

        self.assertIn("JIANGXI_MMSEG_WORKER_ENABLED", standalone)
        self.assertIn("JIANGXI_MMSEG_WORKER_SOCKET", standalone)
        self.assertIn("mmseg_worker.py", entrypoint)
        self.assertIn("MMSEG_WORKER_PID", entrypoint)
        self.assertLess(
            entrypoint.index("start_mmseg_worker"),
            entrypoint.index("python app.py &"),
        )

    def test_gpu_healthcheck_pings_worker_without_rehashing_assets(self):
        source = (ROOT / "docker" / "standalone" / "healthcheck.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("is_gpu_inference_device", source)
        self.assertIn("JIANGXI_INFERENCE_DEVICE", source)
        self.assertIn("mmseg_worker.py", source)
        self.assertIn("--ping", source)
        self.assertIn("get_model_paths", source)
        self.assertNotIn(
            '[ "${JIANGXI_MMSEG_WORKER_ENABLED:-0}" = "1" ]',
            source,
        )


if __name__ == "__main__":
    unittest.main()
