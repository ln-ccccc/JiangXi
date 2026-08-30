# GPU 常驻推理 Worker 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 仅在江西 standalone GPU 模式下，启动一个常驻的 MMSeg 推理 Worker，使 DINOv3+Swin 模型仅加载一次；后续 KML/影像推理复用已加载模型，同时保持现有 API、页面、TBBH/map_fid 和输出协议不变。

**架构：** `kml_roi_infer.py` 仍负责裁剪、TBBH/map_fid 对齐和结果清单；`mmseg_inference_caller` 在配置了 GPU Worker Socket 时通过本地 Unix Socket 发送 JSON 请求；`mmseg_worker.py` 在启动时完成完整模型资产校验和 `init_model`，按单线程队列执行推理。CPU 与非 standalone 继续使用现有一次性子进程路径。

**技术栈：** Python 3.10、Flask、MMSegmentation、PyTorch/CUDA、Unix domain socket、Docker Bash。

**授权边界：** 不提交、不清理任何镜像或运行数据；构建和运行日志/缓存仅使用 `F:\images\jiangxi`。

---

### 任务 1：定义并锁定 Worker 协议的失败行为

**文件：**
- 新增：`backend/test_mmseg_worker.py`
- 修改：`backend/test_mmseg_caller_errors.py`

- [ ] 先添加测试，覆盖 Worker `ping`、连续推理复用同一已加载模型、请求异常返回结构，以及客户端在 Socket 缺失时抛出“GPU 推理 Worker 不可用”。
- [ ] 运行新测试，确认在尚未实现 Worker 前以缺少模块/接口的方式失败（RED）。
- [ ] 测试不导入 MMSeg、Torch 或真实模型；通过注入的假模型加载器与推理函数验证协议和串行处理。

**验证：**

```powershell
python backend/test_mmseg_worker.py -v
python backend/test_mmseg_caller_errors.py -v
```

### 任务 2：实现常驻 Worker，并抽取“已加载模型”推理路径

**文件：**
- 新增：`backend/applications/interface/mmseg_worker.py`
- 修改：`backend/applications/interface/mmseg_segmentation.py`

- [ ] 新增仅容器内可用的 Unix Socket JSON Worker：安全处理陈旧 Socket、拒绝非 Socket 路径、提供 `ping` 和 `infer` 两种动作。
- [ ] Worker 启动时调用现有 `get_model_paths()` 完整校验配置、权重、依赖权重及源码哈希，然后只执行一次 `init_model(..., device='cuda:0')` 与类别合同校验。
- [ ] 从 `run_inference()` 抽取可传入已加载模型的推理函数，保留现有 CLI `run_inference()` 行为和输出格式。
- [ ] 每个 Worker 响应保留既有 `results`/`runtime`，并增加 `queue_wait_seconds`、`model_load_once=true`；错误返回 `{status: "error", error: ...}`。
- [ ] Worker 为单线程服务，不创建并发模型实例；CLI 支持 `--socket` 启动与 `--ping` 探测。

**验证：**

```powershell
python backend/test_mmseg_worker.py -v
python -m py_compile backend/applications/interface/mmseg_worker.py backend/applications/interface/mmseg_segmentation.py
```

### 任务 3：让调用方在 GPU Worker 模式下走 Socket，且禁止静默回退

**文件：**
- 修改：`backend/applications/interface/mmseg_inference_caller.py`
- 修改：`backend/test_mmseg_caller_errors.py`

- [ ] 当 `JIANGXI_MMSEG_WORKER_ENABLED=1` 且配置了 Socket 时，在执行 `get_model_paths()`、解释器探测和子进程启动前走 Worker 客户端。
- [ ] 校验 Worker 返回结构；Socket 缺失、超时或错误状态必须报清晰的“GPU 推理 Worker 不可用/失败”错误，禁止回退 CPU 或一次性 GPU 子进程。
- [ ] 无 Worker 配置时保持现有 CPU/非 standalone 子进程路径完全不变。

**验证：**

```powershell
python backend/test_mmseg_caller_errors.py -v
python backend/test_inference_runner_batch.py -v
```

### 任务 4：接入 standalone 启动、退出和健康检查

**文件：**
- 修改：`docker/standalone/start-jiangxi-standalone.sh`
- 修改：`docker/entrypoint.sh`
- 修改：`docker/standalone/healthcheck.sh`
- 修改：`backend/test_jiangxi_gpu_contract.py`
- 修改：`docker/tests/test_source_isolation.py`

- [ ] GPU 模式导出 Worker 开关与固定容器内 Socket 路径；CPU 模式明确不启用 Worker。
- [ ] GPU 模式把原有启动前的模型资产校验交给 Worker，以避免双重校验；CPU 保持原逻辑。
- [ ] entrypoint 在 Flask 前启动 Worker、等待 `ping` 就绪，失败立即退出；将 Worker PID 纳入现有终止信号清理。
- [ ] Worker 已启用时健康检查改为 `ping` 并核验设备为 `cuda:0`；CPU 健康检查继续执行模型资产校验。

**验证：**

```powershell
python backend/test_jiangxi_gpu_contract.py -v
python docker/tests/test_source_isolation.py -v
bash -n docker/entrypoint.sh docker/standalone/start-jiangxi-standalone.sh docker/standalone/healthcheck.sh
```

### 任务 5：构建 GPU 候选镜像并执行真实连续推理验收

**文件：**
- 修改：`AGENTS.md`
- 修改：`docker/standalone/README.md`
- 修改：`docs/offline_deployment_guide.md`

- [ ] 记录 Worker 的启用条件、Socket、启动/健康语义和排障方式；不记录账号密码或其他密钥。
- [ ] 使用新的候选标签在 `F:\images\jiangxi` 构建；保留当前稳定 GPU 容器和 CPU 镜像作为回滚资源。
- [ ] 容器启动后验证 Worker `ping`、服务健康、348 条 GeoJSON/TBBH 完整性、两次连续同影像 GPU 推理，以及连续第二次没有重新加载模型的日志证据。
- [ ] 验证输出的 TBBH、map_fid、模型哈希和持久化结果与现有协议一致；发生异常时停止在候选状态并保留回滚容器。

**验证：**

```powershell
python backend/test_mmseg_worker.py -v
python backend/test_mmseg_caller_errors.py -v
python backend/test_inference_runner_batch.py -v
python backend/test_jiangxi_gpu_contract.py -v
python docker/tests/test_source_isolation.py -v
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:jiangxi-gpu-20260829-worker .
```

---

## 最终验收条件

- GPU Worker 仅在 standalone GPU 模式运行，且在 Flask 启动前就绪。
- 一次容器生命周期内只加载一次江西 MMSeg 模型；后续推理不重复完整权重 SHA-256 校验或 `init_model`。
- GPU Worker 失败会阻断 GPU 推理并给出明确错误，不会静默回退。
- CPU 与非 standalone 原路径不变。
- 健康检查在 GPU Worker 模式不再每 30 秒重新哈希模型资产。
- 连续相同输入输出仍具有稳定结果，TBBH/map_fid/模型哈希/持久化产物合同不变。
